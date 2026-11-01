# Cointainr

Cointainr is a self-hosted tracker for one person's portfolio of cash, stocks,
crypto, and derivatives held at different locations, valued in one display
currency. Wallet syncing (Bitcoin and Ethereum native balances first) is planned.

## Language

### Portfolio structure

**Portfolio**:
Everything one person owns and tracks in a Cointainr instance; an instance has exactly one.
_Avoid_: Account, workspace

**Location**:
A place where holdings are kept, such as a bank, broker, exchange, or wallet.
_Avoid_: Broker, depot, account, name

**Asset**:
A tradable or holdable instrument, such as Apple stock, Bitcoin, or euro cash, independent of where or how much is held.
_Avoid_: Instrument, security

**Holding**:
A quantity of one asset at one location, with its purchase price; the same asset at two locations is two holdings. Holdings are edited directly; there is no buy/sell history. A quantity may be zero, and negative only for cash; short holdings do not exist.
_Avoid_: Asset (for the row), position

**Asset type**:
The kind of asset: cash, stock, crypto, or derivative. Derivatives are exchange-traded certificates and warrants, valued per unit like stocks.
_Avoid_: Category, class

**Symbol**:
The ticker that identifies a stock or crypto asset, such as AAPL or BTC.
_Avoid_: Code, asset name

**ISIN**:
The international securities number that identifies a derivative.
_Avoid_: Symbol (for derivatives)

**Wallet**:
A location backed by an on-chain address or Bitcoin xpub, whose holding quantities are read from the blockchain instead of entered by hand.
_Avoid_: Address, account

**Last sync**:
The most recent successful read of a wallet's balances; its quantities stay in use, with their age shown, until the next one.
_Avoid_: Refresh, update

### Currencies

**Display currency**:
The single currency the portfolio is currently valued and totalled in.
_Avoid_: Target currency, total currency

**Cash currency**:
The currency a cash holding consists of.
_Avoid_: Holding currency

**Purchase currency**:
The currency a holding's purchase price was paid in.
_Avoid_: Buy currency, holding currency

**Quote currency**:
The currency a quote is reported in.
_Avoid_: Price currency, holding currency

### Valuation

**Quote**:
The latest known market price per unit of an asset, in its quote currency.
_Avoid_: Price (alone), rate

**Stale quote**:
A quote older than its refresh interval; it still values holdings, with its age shown.
_Avoid_: Expired quote, invalid quote

**Unavailable**:
A value that cannot be determined because no quote or currency conversion exists; it is distinct from zero.
_Avoid_: Zero, missing, N/A

**Value**:
A holding's quantity times its quote, converted to the display currency; for cash, its quantity converted.
_Avoid_: Worth, market value

**Purchase price**:
The average cost per unit of a holding across all of its buys, in its purchase currency. Zero means a free acquisition, such as an airdrop or gift; cash has none.
_Avoid_: Buy price, entry price

**Gain/Loss**:
The money difference between a holding's current value and its total purchase cost. Cash has none, including currency movements.
_Avoid_: Yield, profit, P&L

**Return**:
Gain/Loss as a percentage of total purchase cost.
_Avoid_: Performance, yield
