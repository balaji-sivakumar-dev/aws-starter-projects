# Local Testing Guide — Reflect

Step-by-step guide to run and test the full Reflect stack locally, including the RAG pipeline.

---

## Prerequisites

- Docker Desktop running
- `services/api/.venv` exists (created during setup — see [Setup.md](./Setup.md))
- You are in the template-3 root directory:

```bash
cd cloud-ai-starter-projects/template-3-container-serverless-journal
```

---

## 1. Start the Stack

### Option A — Base only (no AI, no RAG)

```bash
docker compose -f docker-compose.yml up --build -d
```

Containers started:

| Container | Role | Port |
|---|---|---|
| `t3-dynamodb` | DynamoDB Local (in-memory) | 8000 |
| `t3-api` | FastAPI backend | 8080 |
| `t3-web` | React + Nginx frontend | 3000 |

### Option B — With Ollama LLM (AI enrichment + insights)

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ollama.yml \
  up --build -d
```

Additional containers:

| Container | Role | Notes |
|---|---|---|
| `t3-ollama` | Ollama LLM server | Port 11434 |
| `t3-ollama-pull` | One-shot model pull | Downloads `llama3.2` (~2 GB) |

**First startup downloads `llama3.2` — allow 5–10 min.**

### Option C — Full stack with RAG (recommended for full testing)

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ollama.yml \
  -f docker-compose.rag.yml \
  up --build -d
```

Additional containers:

| Container | Role | Notes |
|---|---|---|
| `t3-chromadb` | ChromaDB vector store | Internal port 8000, host port 8001 |
| `t3-ollama-pull-embed` | One-shot embedding model pull | Downloads `nomic-embed-text` (~275 MB) |

**Total first-startup download: ~2.5 GB.**

---

## 2. Verify All Containers Are Healthy

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Expected (Option C):

```
NAMES                    STATUS
t3-api                   Up X minutes (healthy)
t3-web                   Up X minutes
t3-dynamodb              Up X minutes (healthy)
t3-ollama                Up X minutes (healthy)
t3-chromadb              Up X minutes (healthy)
t3-ollama-pull           Exited (0)
t3-ollama-pull-embed     Exited (0)
```

> `ollama-pull` containers must exit with code **0**, not 1. If they show `Exited (1)`, model download failed — check logs: `docker logs t3-ollama-pull`

---

## 3. Seed Journal Entries

Loads ~195 realistic journal entries (2024–2026) for user `dev-user`:

```bash
services/api/.venv/bin/python3 scripts/seed_data/seed_data.py
```

Expected output (truncated):

```
✓ Created: Morning run and coffee ritual (2024-04-01)
✓ Created: Book club night with Dave (2024-04-07)
...
Done. 195 entries seeded for user dev-user
```

To re-seed (stack restart wipes in-memory DynamoDB), just run the script again.

---

## 4. Verify in the UI

Open **http://localhost:3000**

- **Home tab** — should show entry count stats
- **Journal tab** — 195 entries in the sidebar. Year filter buttons (`2024`, `2025`, `2026`) should appear. Click a year to expand month filters.

---

## 5. Test AI Enrichment (Option B/C only)

1. Click any journal entry in the sidebar
2. In the detail panel, click **"AI Enrich"**
3. The entry should update with a summary and tags (status changes to `DONE`)

Or via API:

```bash
# Get an entry ID first
curl -s http://localhost:8080/entries?limit=1 \
  -H "X-User-Id: dev-user" | python3 -m json.tool

# Trigger AI enrichment
curl -s -X POST http://localhost:8080/entries/<ENTRY_ID>/ai \
  -H "X-User-Id: dev-user" | python3 -m json.tool
```

---

## 6. Test RAG — Index All Entries (Option C only)

Before asking questions, all entries must be embedded into ChromaDB.

**Via Admin tab (UI):**
1. Go to **Admin** tab → click **"Index All Entries"**
2. Wait for the response — should report `195 embedded, 0 failed`

**Via API:**

```bash
curl -s -X POST http://localhost:8080/rag/embed-all \
  -H "X-User-Id: dev-user" | python3 -m json.tool
```

Expected response:

```json
{
  "status": "completed",
  "totalEntries": 195,
  "embedded": 195,
  "failed": 0
}
```

Check how many vectors are stored:

```bash
curl -s http://localhost:8080/rag/status \
  -H "X-User-Id: dev-user" | python3 -m json.tool
```

---

## 7. Test RAG — Ask Your Journal (Option C only)

**Via Ask tab (UI):**
- Go to **Ask** tab and type a question, e.g. *"When did I go hiking with Liam?"*

**Via API:**

```bash
curl -s -X POST http://localhost:8080/rag/ask \
  -H "X-User-Id: dev-user" \
  -H "Content-Type: application/json" \
  -d '{"query": "What hobbies do I enjoy most?", "top_k": 5}' \
  | python3 -m json.tool
```

Expected response shape:

```json
{
  "answer": "Based on your journal entries, you enjoy...",
  "sources": [
    { "entryId": "...", "title": "...", "score": 0.87 }
  ],
  "query": "What hobbies do I enjoy most?"
}
```

Sample questions to try:
- *"How has my fitness routine changed over time?"*
- *"What did Emma accomplish at school?"*
- *"When did I last travel and where did I go?"*
- *"What books have I read with Dave's book club?"*
- *"How is Liam doing with chess?"*

---

## 8. Run Unit Tests

```bash
cd services/api
.venv/bin/pytest tests/ -v
```

Current test coverage:

| Test File | What it covers |
|---|---|
| `test_entries.py` | CRUD operations on journal entries |
| `test_auth.py` | Auth / user isolation |
| `test_llm.py` | AI enrichment endpoint |
| `test_insights.py` | Insights generation |
| `test_rag_embedding.py` | Ollama embedding provider (FIX-004) |

## 8b. Run Integration Tests (requires running stack + seed data)

```bash
bash scripts/tests/test_local_integration.sh

# Verbose output (prints full response bodies on failure):
VERBOSE=1 bash scripts/tests/test_local_integration.sh
```

Covers: entries CRUD, RAG embed-all, semantic search, ask journal, and insights generation.

---

## 9. Tear Down

```bash
# Stop containers, keep volumes (retains Ollama models)
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ollama.yml \
  -f docker-compose.rag.yml \
  down

# Stop and wipe all volumes (forces model re-download on next start)
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ollama.yml \
  -f docker-compose.rag.yml \
  down -v
```

> Prefer `down` (without `-v`) day-to-day to avoid re-downloading models.

---

## Troubleshooting

| Symptom | Action |
|---|---|
| `t3-chromadb` stays unhealthy | `docker logs t3-chromadb` — check startup errors |
| `t3-ollama-pull-embed` exits with code 1 | Model pull failed — check network, retry: `docker compose ... up -d` |
| Embed-all returns `failed > 0` | `docker logs t3-api` — look for embedding errors |
| Ask returns "not enough entries to answer" | Indexing (Step 6) hasn't been run yet, or ChromaDB volume was wiped |
| UI shows blank / no entries | Seed step (Step 3) hasn't been run, or stack was restarted (DynamoDB is in-memory) |
| API returns HTML error instead of JSON | App hasn't finished starting — check `docker logs t3-api` |
