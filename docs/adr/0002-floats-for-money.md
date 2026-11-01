# Floats for money, rounded only for display

Quantities, quotes, purchase prices, and values are stored in SQLite and calculated as floating-point numbers; they are rounded only when displayed, and rounded values are never written back. For a personal portfolio, float error stays far below one cent, while moving storage to exact decimals would require a migration of existing holdings with real risk and no visible benefit. Revisit if Cointainr ever produces figures that must reconcile exactly, such as tax reports.
