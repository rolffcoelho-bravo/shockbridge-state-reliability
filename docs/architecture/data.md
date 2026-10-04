# Data architecture — foundation

Persistent analytical data will use Parquet and DuckDB after Milestone 1. Milestone 0 intentionally stores no external data in version control.

```text
data/raw -> data/interim -> data/processed -> data/feature_store
```

Each artifact requires a sidecar manifest containing the source URL, retrieval timestamp, content hash, provider vintage, schema version, license identifier, redistribution decision, and row-level timing fields. Transformations must be deterministic and preserve lineage to immutable raw content.

