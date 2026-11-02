"""
List holdings that break the holding rules, without changing anything.

Run against a copy of a backup, or inside the container:

    python -m app.tools.check_holdings /path/to/cointainr.db

Without a path, the SQLite file from COINTAINR_DATABASE_URL is used. The file
is opened read-only. Exit code 0 means no violations, 1 means violations were
listed, 2 means the file could not be read.
"""

import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.holding_rules import holding_violations

DEFAULT_URL = "sqlite+aiosqlite:///./cointainr.db"


@dataclass(frozen=True)
class Violation:
    id: int
    name: str
    type: str
    field: str
    rule: str


def find_violations(db_path: Path | str) -> list[Violation]:
    """
    Read every holding from a SQLite file and check it against the rules.

    Args:
        db_path: path to the SQLite database file

    Returns:
        One entry per broken rule, ordered by holding id

    Raises:
        FileNotFoundError: if the file does not exist (it is never created)
    """
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    uri = f"{path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT id, name, type, quantity, purchase_price FROM assets ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    return [
        Violation(id=row_id, name=name, type=asset_type, field=field, rule=rule)
        for row_id, name, asset_type, quantity, purchase_price in rows
        for field, rule in holding_violations(asset_type, quantity, purchase_price)
    ]


def _path_from_database_url(url: str) -> Optional[str]:
    prefix = "sqlite+aiosqlite:///"
    return url[len(prefix) :] if url.startswith(prefix) else None


def main(argv: Optional[list[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args:
        db_path = args[0]
    else:
        url = os.getenv("COINTAINR_DATABASE_URL", DEFAULT_URL)
        db_path = _path_from_database_url(url)
        if db_path is None:
            print(f"Not a SQLite database URL: {url}", file=sys.stderr)
            return 2

    try:
        violations = find_violations(db_path)
    except (FileNotFoundError, sqlite3.Error) as error:
        print(f"Cannot read {db_path}: {error}", file=sys.stderr)
        return 2

    if not violations:
        print(f"No holding rule violations in {db_path}")
        return 0

    print(f"{len(violations)} holding rule violation(s) in {db_path}:")
    for v in violations:
        print(f"  id {v.id} ({v.type}, {v.name!r}): {v.field}: {v.rule}")
    print("Fix them by editing the holdings in the app.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
