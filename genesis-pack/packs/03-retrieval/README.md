# Pack 03 · retrieval

Hybrid recall fabric with a single `retrieve()` entry point that fuses:

- BM25 / DuckDB FTS
- Dense vector search / LanceDB
- Cross-encoder reranking
- Optional graph expansion / Kuzu

## API

`api.py` exports:

- `Hit` dataclass
- `retrieve(query, **filters) -> list[Hit]`

The implementation uses graceful capability detection:

- If optional dependencies are missing, modules degrade without hard-fail.
- If local embedding/rerank endpoints are unavailable, baseline retrieval still works.

## Files

- `api.py` — core retrieval API
- `contextual_chunking.py` — chunk contextualization helper
- `graphiti_builder.py` — temporal graph upsert scaffolding
