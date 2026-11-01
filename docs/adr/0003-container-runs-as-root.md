# Container runs as root

The Cointainr image deliberately keeps running as root instead of a dedicated non-root user. Switching users would require a one-time ownership change of every existing data directory before the app could write its SQLite database, which is easy to get wrong during an update, while the app is a single-user, self-hosted service. Revisit together with a documented migration path if the image is ever offered for shared or multi-tenant hosting.
