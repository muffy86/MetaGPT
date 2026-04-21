#!/usr/bin/env bash
set -e
mkdir -p data/{exocortex/events,exocortex/embeddings.lance,exocortex/graph.kuzu} memory/{daily,weekly} runs tmp vault assets
# Iceberg catalog init (DuckDB Iceberg extension)
duckdb data/ledger.duckdb <<'SQL'
INSTALL iceberg; LOAD iceberg;
INSTALL fts;     LOAD fts;
INSTALL vss;     LOAD vss;
CREATE SCHEMA IF NOT EXISTS exocortex;
CREATE TABLE IF NOT EXISTS exocortex.events (
  id UUID, ts TIMESTAMPTZ, ingested_at TIMESTAMPTZ DEFAULT now(),
  source VARCHAR, kind VARCHAR, actor VARCHAR, subjects VARCHAR[],
  title VARCHAR, body TEXT, body_hash VARCHAR,
  tags VARCHAR[], thread_id VARCHAR, parent_id UUID,
  embed_ref VARCHAR, kg_node_id VARCHAR,
  meta JSON, sensitivity VARCHAR DEFAULT 'internal', redaction_map VARCHAR
);
CREATE INDEX IF NOT EXISTS idx_ts     ON exocortex.events(ts);
CREATE INDEX IF NOT EXISTS idx_source ON exocortex.events(source);
PRAGMA create_fts_index('exocortex.events', 'id', 'title', 'body', stemmer='porter', overwrite=1);

CREATE TABLE IF NOT EXISTS hitl.queue (
  id UUID PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  type VARCHAR, payload JSON, status VARCHAR DEFAULT 'pending',
  confidence DOUBLE, citations JSON, disposed_at TIMESTAMP,
  disposition VARCHAR, edit JSON
);
SQL

# KuzuDB schema
python - <<'PY'
import kuzu
db = kuzu.Database("data/exocortex/graph.kuzu")
c  = kuzu.Connection(db)
for q in [
 "CREATE NODE TABLE IF NOT EXISTS Person(id STRING PRIMARY KEY, name STRING, emails STRING[], handles STRING[])",
 "CREATE NODE TABLE IF NOT EXISTS Org(id STRING PRIMARY KEY, name STRING)",
 "CREATE NODE TABLE IF NOT EXISTS Project(id STRING PRIMARY KEY, name STRING)",
 "CREATE NODE TABLE IF NOT EXISTS Topic(id STRING PRIMARY KEY, name STRING)",
 "CREATE NODE TABLE IF NOT EXISTS Event(id STRING PRIMARY KEY, ts TIMESTAMP, source STRING)",
 "CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Event TO Person, ts TIMESTAMP)",
 "CREATE REL TABLE IF NOT EXISTS MENTIONS_ORG(FROM Event TO Org, ts TIMESTAMP)",
 "CREATE REL TABLE IF NOT EXISTS DISCUSSES(FROM Event TO Topic, weight DOUBLE)",
 "CREATE REL TABLE IF NOT EXISTS REPORTS_TO(FROM Person TO Person, from_ts TIMESTAMP, to_ts TIMESTAMP)",
 "CREATE REL TABLE IF NOT EXISTS WORKS_ON(FROM Person TO Project, from_ts TIMESTAMP, to_ts TIMESTAMP)",
]:
    try: c.execute(q)
    except Exception as e: print("skip:", e)
PY

# LanceDB init
python - <<'PY'
import lancedb, pyarrow as pa
db = lancedb.connect("data/exocortex/embeddings.lance")
schema = pa.schema([
    ("id", pa.string()),
    ("vec", pa.list_(pa.float32(), 1024)),
    ("source", pa.string()),
    ("ts", pa.timestamp("us", tz="UTC")),
    ("title", pa.string()),
    ("body", pa.string()),
    ("actor", pa.string()),
])
try: db.create_table("events_embed", schema=schema, mode="create")
except: pass
PY

# identity.md seed
[[ -f memory/identity.md ]] || cat > memory/identity.md <<'MD'
# Identity
north_star: ""
non_negotiables: []
pinned_context:
  - "Ship, don't theorize."
  - "The exocortex is the spine; don't shard state elsewhere."
MD
echo "data initialized"
