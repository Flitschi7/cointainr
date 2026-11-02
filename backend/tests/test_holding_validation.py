"""
Holding rules on create and update, and the read-only violation check.

Rules (GLOSSARY.md "Holding" and "Purchase price"): quantity may be 0 and is
negative only for cash; purchase price may be 0 but not negative; NaN and
Infinity are always rejected. Existing rows that break a rule still load.
"""

import json
import sqlite3

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.session import engine
from app.models.asset import Asset, AssetType
from app.tools.check_holdings import find_violations, main

ASSETS = "/api/v1/assets/"

Session = async_sessionmaker(engine, expire_on_commit=False)


async def post_raw(client, body: str):
    """Send JSON text as-is, so NaN and Infinity reach the server."""
    return await client.post(
        ASSETS, content=body, headers={"Content-Type": "application/json"}
    )


async def create(client, **fields):
    response = await client.post(ASSETS, json=fields)
    assert response.status_code == 200, response.text
    return response.json()


async def insert_row(**fields):
    async with Session() as session:
        row = Asset(**fields)
        session.add(row)
        await session.commit()
        return row.id


# --- Create ---


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "stock", "name": "Broker", "quantity": -1},
        {"type": "crypto", "name": "Wallet", "quantity": -0.5},
        {"type": "derivative", "name": "Broker", "quantity": -10},
        {"type": "stock", "name": "Broker", "quantity": 1, "purchase_price": -5},
        {"type": "cash", "name": "Bank", "quantity": 1, "purchase_price": -1},
    ],
    ids=[
        "negative-stock",
        "negative-crypto",
        "negative-derivative",
        "negative-purchase-price",
        "negative-purchase-price-cash",
    ],
)
async def test_create_rejects_rule_violations(client, fields):
    response = await client.post(ASSETS, json=fields)

    assert response.status_code == 422
    assert (await client.get(ASSETS)).json() == []


@pytest.mark.parametrize(
    "body",
    [
        '{"type": "stock", "name": "B", "quantity": NaN}',
        '{"type": "stock", "name": "B", "quantity": Infinity}',
        '{"type": "cash", "name": "B", "quantity": -Infinity}',
        '{"type": "stock", "name": "B", "quantity": 1, "purchase_price": NaN}',
        '{"type": "stock", "name": "B", "quantity": 1, "purchase_price": Infinity}',
    ],
    ids=["nan-qty", "inf-qty", "neg-inf-cash", "nan-price", "inf-price"],
)
async def test_create_rejects_non_finite_numbers(client, body):
    response = await post_raw(client, body)

    assert response.status_code == 422
    assert (await client.get(ASSETS)).json() == []


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "stock", "name": "Broker", "quantity": 0},
        {"type": "cash", "name": "Bank", "quantity": -250.75},
        {"type": "crypto", "name": "Wallet", "quantity": 1, "purchase_price": 0},
        {"type": "crypto", "name": "Wallet", "quantity": 0.00000001},
        {"type": "stock", "name": "Broker", "quantity": 1, "purchase_price": None},
    ],
    ids=[
        "zero-quantity",
        "negative-cash",
        "free-acquisition",
        "one-satoshi",
        "no-purchase-price",
    ],
)
async def test_create_accepts_valid_edge_cases(client, fields):
    body = await create(client, **fields)

    assert body["quantity"] == fields["quantity"]
    assert body["purchase_price"] == fields.get("purchase_price")


# --- Update ---


@pytest.mark.parametrize(
    "start, change",
    [
        ({"type": "stock", "quantity": 1}, {"quantity": -1}),
        ({"type": "cash", "quantity": -5}, {"type": "stock"}),
        ({"type": "stock", "quantity": 1}, {"purchase_price": -0.01}),
        ({"type": "stock", "quantity": 1}, {"quantity": float("nan")}),
        ({"type": "stock", "quantity": 1}, {"purchase_price": float("inf")}),
    ],
    ids=[
        "negative-stock",
        "negative-cash-becomes-stock",
        "negative-price",
        "nan-qty",
        "inf-price",
    ],
)
async def test_update_rejects_result_that_breaks_a_rule(client, start, change):
    created = await create(client, name="Holding", **start)

    response = await client.put(
        f"{ASSETS}{created['id']}",
        content=json.dumps(change),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert (await client.get(ASSETS)).json() == [created]


@pytest.mark.parametrize(
    "start, change",
    [
        ({"type": "cash", "quantity": 10}, {"quantity": -10}),
        ({"type": "stock", "quantity": 3}, {"quantity": 0}),
        ({"type": "stock", "quantity": 3, "purchase_price": 9}, {"purchase_price": 0}),
        ({"type": "stock", "quantity": 3}, {"name": "Renamed"}),
    ],
    ids=["negative-cash", "zero-quantity", "free-acquisition", "rename"],
)
async def test_update_accepts_valid_result(client, start, change):
    created = await create(client, name="Holding", **start)

    response = await client.put(f"{ASSETS}{created['id']}", json=change)

    assert response.status_code == 200
    assert response.json() == {**created, **change}


async def test_update_that_fixes_an_invalid_row_is_accepted(client):
    row_id = await insert_row(type=AssetType.STOCK, name="Old", quantity=-5)

    response = await client.put(f"{ASSETS}{row_id}", json={"quantity": 5})

    assert response.status_code == 200
    assert response.json()["quantity"] == 5


async def test_update_that_leaves_an_invalid_row_invalid_is_rejected(client):
    row_id = await insert_row(type=AssetType.STOCK, name="Old", quantity=-5)

    response = await client.put(f"{ASSETS}{row_id}", json={"name": "Renamed"})

    assert response.status_code == 422


# --- Existing rows ---


async def test_existing_invalid_rows_still_load(client):
    await insert_row(
        type=AssetType.CRYPTO, name="Old", quantity=-2, purchase_price=-1.0
    )

    listed = (await client.get(ASSETS)).json()

    assert [(a["quantity"], a["purchase_price"]) for a in listed] == [(-2, -1.0)]


async def test_existing_infinite_quantity_still_loads(client):
    await insert_row(type=AssetType.STOCK, name="Old", quantity=float("inf"))

    response = await client.get(ASSETS)

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Old"


# --- Read-only violation check ---


def make_db(path, rows):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE assets (id INTEGER PRIMARY KEY, type VARCHAR, name VARCHAR,"
            " assetname VARCHAR, quantity FLOAT, symbol VARCHAR, currency VARCHAR,"
            " purchase_price FLOAT, buy_currency VARCHAR)"
        )
        conn.executemany(
            "INSERT INTO assets (id, type, name, quantity, purchase_price)"
            " VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    return path


def test_check_lists_each_violation(tmp_path):
    db = make_db(
        tmp_path / "backup.db",
        [
            (1, "CASH", "Bank", -100.0, None),
            (2, "STOCK", "Broker", 0.0, 0.0),
            (3, "STOCK", "Short", -3.0, 10.0),
            (4, "CRYPTO", "Odd", 1.0, -2.0),
            (5, "DERIVATIVE", "Huge", float("inf"), None),
            (6, "CASH", "Gift", 5.0, float("-inf")),
        ],
    )

    found = [(v.id, v.rule) for v in find_violations(db)]

    assert found == [
        (3, "negative quantity is only allowed for cash"),
        (4, "purchase price must not be negative"),
        (5, "quantity must be a finite number"),
        (6, "purchase price must be a finite number"),
    ]


def test_check_does_not_modify_the_database(tmp_path):
    db = make_db(tmp_path / "backup.db", [(1, "STOCK", "Short", -1.0, None)])
    before = db.read_bytes()

    find_violations(db)

    assert db.read_bytes() == before
    assert not (tmp_path / "backup.db-journal").exists()
    assert not (tmp_path / "backup.db-wal").exists()


def test_check_refuses_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_violations(tmp_path / "missing.db")
    assert not (tmp_path / "missing.db").exists()


def test_check_cli_exit_code_reports_violations(tmp_path, capsys):
    clean = make_db(tmp_path / "clean.db", [(1, "CASH", "Bank", -1.0, None)])
    dirty = make_db(tmp_path / "dirty.db", [(7, "STOCK", "Short", -1.0, None)])

    assert main([str(clean)]) == 0
    assert main([str(dirty)]) == 1
    out = capsys.readouterr().out
    assert "7" in out and "Short" in out and "only allowed for cash" in out
