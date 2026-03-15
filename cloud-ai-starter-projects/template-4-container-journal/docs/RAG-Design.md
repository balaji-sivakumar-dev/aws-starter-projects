# RAG Pipeline Design

> **Status: Design phase**
> Last updated: 2026-03-14

---

## 1. What is RAG and why do we need it?

**Retrieval-Augmented Generation (RAG)** lets an LLM answer questions using your own data — not just its training data. Instead of fine-tuning a model (expensive, slow), you retrieve relevant documents at query time and pass them as context to the LLM.

**Why every target app needs it**:

| App | RAG query example | Data source |
|-----|-------------------|-------------|
| Budget Tracker | "How much did I spend on dining out last quarter?" | Transaction history |
| Tax Processor | "Based on my uploaded T4, what is my total employment income?" | Extracted tax document fields |
| Curriculum | "Explain polymorphism using examples from Module 3" | Uploaded course materials |
| Family Tree | "Tell me about my grandfather's siblings" | Family member profiles + relationships |
| Journal (Template 3) | "What themes have been recurring in my entries this month?" | Journal entries |

---

## 2. RAG pipeline overview

```
  ┌────────────────────────────────────────────────────────┐
  │                    INGESTION FLOW                       │
  │                                                        │
  │  Source Data ──► Chunk ──► Embed ──► Store              │
  │  (text/docs)    (split)   (vectors)  (vector store)    │
  └────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────┐
  │                    QUERY FLOW                           │
  │                                                        │
  │  User Query ──► Embed ──► Search ──► Retrieve ──► LLM  │
  │  ("How much     (vector)  (k-NN)    (top-k      (answer│
  │   on dining?")                       chunks)     with  │
  │                                                 context)│
  └────────────────────────────────────────────────────────┘
```

---

## 3. Component design

### 3.1 Chunking

Raw text must be split into chunks before embedding. Chunks should be:
- Small enough to be semantically focused (~200-500 tokens)
- Large enough to carry meaningful context
- Overlapping slightly (50-100 tokens) to avoid losing context at boundaries

**Strategy per data type**:

| Data type | Chunking strategy |
|-----------|-------------------|
| Journal entries | One chunk per entry (entries are typically < 500 tokens) |
| Transactions | Batch by month + category (aggregate, don't embed individual $5 charges) |
| Tax documents | One chunk per extracted field group (employment income, deductions, etc.) |
| Course materials | Recursive text splitter — paragraphs → sentences → fixed-size |
| Family profiles | One chunk per person (name + relationships + bio) |

### 3.2 Embedding

Convert text chunks into fixed-length vectors (1024-1536 dimensions).

**Provider options** (following the existing LLM provider pattern):

| Provider | Model | Dimensions | Cost | Local? |
|----------|-------|-----------|------|--------|
| **Amazon Titan** | `amazon.titan-embed-text-v2:0` | 1024 | $0.0001/1K tokens | No |
| **Cohere** | `cohere.embed-english-v3` (via Bedrock) | 1024 | $0.0001/1K tokens | No |
| **OpenAI** | `text-embedding-3-small` | 1536 | $0.00002/1K tokens | No |
| **Ollama** | `nomic-embed-text` | 768 | Free | Yes |

**Recommendation**: Start with **Amazon Titan Embeddings v2** (via Bedrock) for AWS deployments — same Bedrock IAM setup we already have. Use **Ollama + nomic-embed-text** locally for free development.

**Provider abstraction** (extends existing `LLMProvider`):
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...
```

### 3.3 Vector store

**Options evaluated**:

| Store | Type | Cost (idle) | Cost (active) | Managed? | Local dev? |
|-------|------|-------------|---------------|----------|------------|
| **OpenSearch Serverless (AOSS)** | AWS managed | ~$21/mo (2 OCU min) | Scales | Yes | No (use Docker) |
| **Pinecone** | SaaS | Free tier (100K vectors) | $8+/mo | Yes | No (use starter) |
| **pgvector (RDS)** | Self-managed | ~$15/mo (t4g.micro) | Scales | Partially | Yes (Docker) |
| **DynamoDB + brute-force** | DIY | $0 | Per-request | No | Yes |
| **ChromaDB** | Open source | $0 | $0 | No | Yes |
| **FAISS in Lambda** | In-memory | $0 | Per-request | No | Yes (Python) |

**Recommendation by stage**:

| Stage | Store | Why |
|-------|-------|-----|
| **Local dev** | ChromaDB (Docker) | Free, simple API, good Python/JS SDKs |
| **MVP (< 10K vectors)** | DynamoDB + brute-force OR FAISS in Lambda | Zero additional cost, fits in free tier |
| **Growth (10K-1M vectors)** | Pinecone (free tier → starter) | Managed, no ops, generous free tier |
| **Scale (1M+ vectors)** | OpenSearch Serverless | AWS-native, integrates with IAM, scales |

**DynamoDB brute-force approach** (for MVP):
- Store embeddings as a binary attribute in DynamoDB
- On query: scan all user's embeddings, compute cosine similarity in Lambda
- Works for < 10K vectors per user (sub-second at 1K vectors)
- Zero additional infrastructure cost
- Graduate to a real vector store when query latency becomes an issue

### 3.4 Retrieval

```python
class Retriever:
    def __init__(self, vector_store, embedding_provider):
        self.store = vector_store
        self.embedder = embedding_provider

    def retrieve(self, query: str, tenant_id: str, top_k: int = 5,
                 filters: dict = None) -> list[Document]:
        """
        1. Embed the query
        2. Search vector store (scoped to tenant)
        3. Return top-k most similar documents
        """
        query_vector = self.embedder.embed(query)
        results = self.store.search(
            vector=query_vector,
            tenant_id=tenant_id,
            top_k=top_k,
            filters=filters  # e.g., {"entity_type": "transaction", "date_range": "2026-Q1"}
        )
        return results
```

**Key design decisions**:
- **Tenant isolation**: Every vector is tagged with `tenant_id`. Queries only search within the user's own data.
- **Metadata filters**: Pre-filter by entity type, date range, category before vector search. Reduces search space and improves relevance.
- **Hybrid search**: For structured data (transactions), combine vector similarity with metadata filtering. "Dining expenses in January" = vector search for "dining" + filter `date >= 2026-01-01`.

### 3.5 LLM integration (answer generation)

```python
def rag_query(query: str, tenant_id: str, llm: LLMProvider, retriever: Retriever) -> str:
    # 1. Retrieve relevant context
    documents = retriever.retrieve(query, tenant_id, top_k=5)

    # 2. Build prompt with context
    context = "\n\n".join([
        f"[{doc.metadata.get('source', 'unknown')}]\n{doc.text}"
        for doc in documents
    ])

    messages = [
        {"role": "system", "content": f"Answer the user's question using ONLY the following context. If the context doesn't contain the answer, say so.\n\nContext:\n{context}"},
        {"role": "user", "content": query}
    ]

    # 3. Generate answer
    return llm.complete(messages)
```

---

## 4. Ingestion triggers

When should embeddings be created or updated?

| Trigger | Action | Implementation |
|---------|--------|---------------|
| **New entity created** | Embed on write | Inline (if fast) or async via Step Functions |
| **Entity updated** | Re-embed | Delete old vector + embed new |
| **Entity deleted** | Remove embedding | Delete from vector store |
| **File uploaded** | Parse → chunk → embed | S3 event → Step Functions → Lambda |
| **Bulk import** | Batch embed | Step Functions Map state for parallel processing |

**Async vs inline**:
- For small text (journal entry, transaction description): **inline** — embed during the API write, add < 200ms latency
- For large content (PDF, course material): **async** — return immediately, process via Step Functions, poll for status (same pattern as current AI enrichment)

---

## 5. API design

New RAG endpoints added to the platform API:

```
POST /rag/query
  Body: { "query": "How much did I spend on dining in January?", "filters": { ... } }
  Response: { "answer": "...", "sources": [...], "requestId": "..." }

POST /rag/embed
  Body: { "entityType": "transaction", "entityId": "txn-123", "text": "..." }
  Response: { "status": "embedded", "vectorId": "..." }

DELETE /rag/embed/{vectorId}
  Response: { "deleted": true }

GET /rag/status
  Response: { "totalVectors": 1234, "lastEmbeddedAt": "..." }
```

The `/rag/query` endpoint is the main user-facing feature. The embed/delete endpoints are typically called by the system (on entity create/update/delete), not by end users directly.

---

## 6. Infrastructure (Terraform)

New module: `modules/rag/`

```hcl
# For MVP (DynamoDB brute-force)
resource "aws_dynamodb_table" "vectors" {
  name         = "${var.app_prefix}-${var.env}-vectors"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenantId"
  range_key    = "vectorId"

  attribute {
    name = "tenantId"
    type = "S"
  }
  attribute {
    name = "vectorId"
    type = "S"
  }
}

# For Bedrock embeddings
# Reuse existing ai_gateway IAM role — add bedrock:InvokeModel for embedding model
```

Later upgrade path: swap DynamoDB table for OpenSearch Serverless collection or Pinecone client — same Terraform module interface, different backend.

---

## 7. Local development

```yaml
# docker-compose.rag.yml (overlay)
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma

  api:
    environment:
      RAG_PROVIDER: chroma
      CHROMA_HOST: http://chromadb:8000
      EMBEDDING_PROVIDER: ollama
      EMBEDDING_MODEL: nomic-embed-text
```

Usage:
```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml -f docker-compose.rag.yml up
```

---

## 8. Cost estimate

| Component | MVP (DynamoDB) | Growth (Pinecone) | Scale (AOSS) |
|-----------|---------------|-------------------|--------------|
| Vector storage | $0 (free tier) | $0 (free tier, 100K vectors) | ~$21/mo |
| Embedding (Titan) | ~$0.10/1K docs | ~$1/10K docs | ~$10/100K docs |
| LLM queries | Same as current AI costs | Same | Same |
| **Additional monthly** | **~$0** | **~$0-8** | **~$21+** |

**Key insight**: The MVP approach (DynamoDB + brute-force cosine similarity) adds **zero additional infrastructure cost**. It works well up to ~10K vectors per user. This aligns with the "save cost in the initial phase" motivation.

---

## 9. Implementation sequence

1. **Add `embed()` to LLM provider interface** — extend existing abstraction
2. **Implement Ollama embedding provider** (local dev) + Titan embedding provider (AWS)
3. **Create vector store abstraction** — `VectorStore` ABC with `store()`, `search()`, `delete()`
4. **Implement DynamoDB vector store** (MVP) + ChromaDB store (local dev)
5. **Build Retriever** — query embedding + vector search + metadata filtering
6. **Add `/rag/query` endpoint** to API
7. **Wire ingestion triggers** — embed on entity create/update, async for files
8. **Test end-to-end** with journal entries (Template 3 as first RAG-enabled app)
9. **Graduate to Pinecone/AOSS** when vector count exceeds DynamoDB performance threshold
