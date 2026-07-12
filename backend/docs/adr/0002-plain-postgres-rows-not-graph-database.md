# Plain Postgres rows, not a graph database

Concept relationships (the edges in a Concept Map) are stored as plain rows in Postgres, not in a dedicated graph database. V1's relationship volume and query pattern (render one Topic's graph at a time) don't need graph-native traversal, and a graph database would be new infrastructure to operate for no proven benefit yet.

**Status**: accepted
