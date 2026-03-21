# AWS Cost Estimate — Reflect (Template 3)

Estimated monthly cost for **Lambda-only serverless mode** on AWS.
Figures are for **us-east-1**, 1–5 users, light testing workload.

> **Target deployment: `compute_mode = "serverless"` — Lambda + API Gateway only.**
> No ECS, no Fargate, no App Runner. Step Functions handles async AI enrichment.

---

## AWS Free Tier

Most services in this app are either always-free or covered by the 12-month free tier.

| Service | Free Tier Allowance |
|---|---|
| Lambda | 1M requests/month + 400,000 GB-seconds compute — **always free** |
| API Gateway (HTTP) | 1M calls/month for 12 months |
| DynamoDB | 25 GB storage + 25 WCU/RCU — **always free** |
| S3 | 5 GB storage + 20K GET + 2K PUT for 12 months |
| CloudFront | 1 TB transfer + 10M HTTP requests for 12 months |
| Cognito | 50,000 MAUs — **always free** |
| CloudWatch Logs | 5 GB ingestion + 5 GB storage for 12 months |
| Step Functions | 4,000 state transitions/month — **always free** |

**During the free tier period, running this app costs ~$0/month for core infrastructure.**

---

## Estimated Monthly Cost (After Free Tier)

| Service | Config | Monthly Est. |
|---|---|---|
| Lambda | 100K invocations × 512 MB × 500 ms avg | ~$0.20 |
| API Gateway (HTTP API) | 100K requests/month | ~$0.10 |
| DynamoDB | On-demand, ~10 MB data, light reads/writes | ~$0.25 |
| Step Functions | ~1K state transitions/month | ~$0.00 |
| Cognito | Up to 50,000 MAUs | $0 |
| CloudWatch Logs | 1 GB ingested/month | ~$0.50 |
| S3 (frontend) | < 1 GB, < 10K requests | ~$0.02 |
| CloudFront | 1 GB data transfer | ~$0.09 |
| SSM Parameters | Standard tier | $0 |
| **Total (no AI, no RAG)** | | **~$1.16/month** |

---

## AI Enrichment Add-On (Bedrock)

Per-entry AI enrichment (summary + tags) runs via Step Functions → AI Gateway Lambda → Bedrock.
**Bedrock has zero idle cost — you pay only per API call.**

### Recommended: Amazon Bedrock Nova Lite (default)

`amazon.nova-lite-v1:0` — cheapest model with good quality. Already set as default `bedrock_model_id` in Terraform.

| What | Config | Cost |
|---|---|---|
| Input tokens | ~1,000 tokens/entry × 100 enrichments/month | ~$0.006 |
| Output tokens | ~300 tokens/entry × 100 enrichments/month | ~$0.007 |
| **Subtotal** | | **~$0.013/month** |

Pricing: $0.00006/1K input tokens, $0.00024/1K output tokens.

### Alternative: Claude 3 Haiku (higher quality)

`anthropic.claude-3-haiku-20240307-v1:0` — better reasoning, slightly more expensive.

| What | Config | Cost |
|---|---|---|
| Input tokens | ~1,000 tokens × 100 enrichments | ~$0.025 |
| Output tokens | ~300 tokens × 100 enrichments | ~$0.038 |
| **Subtotal** | | **~$0.063/month** |

---

## RAG (Ask Your Journal) — Vector Storage

The local stack uses ChromaDB (requires a persistent server process). **ChromaDB cannot run inside Lambda.**
For Lambda-only AWS deployment, choose one of these alternatives:

### Option A — DynamoDB Vector Storage (Recommended for Testing)

Store embedding vectors as JSON in the DynamoDB table alongside journal entries.
Lambda retrieves vectors, computes cosine similarity in memory, returns top-k passages.

| What | Cost |
|---|---|
| DynamoDB storage: 200 entries × 1536-dim vectors (~2.5 MB) | ~$0 (within free tier) |
| Bedrock Titan Embed v2 — embed all 200 entries once | ~$0.0002 |
| Bedrock Nova Lite — 20 RAG "ask" queries/month | ~$0.002 |
| **Total** | **< $0.01/month** |

Works well for up to ~1,000 entries. No extra infrastructure — uses the existing DynamoDB table.

> **Important**: `amazon.titan-embed-text-v2:0` generates the embedding vector.
> It does NOT store it. The vector must be saved to DynamoDB separately.
> This is identical to how Ollama embeddings work locally — the embedding provider
> just converts text to numbers; the RAG store layer handles persistence.

### Option B — pgvector on RDS Postgres (Production Scale)

Proper vector index with approximate nearest neighbour search.
Required when entry count exceeds ~2,000 or query latency matters.

| Config | Monthly Est. |
|---|---|
| db.t3.micro, 20 GB gp2, single-AZ | ~$15/month |
| Free: db.t3.micro for first 12 months (750 hrs/month) | $0 |

### Option C — OpenSearch Serverless (Not Recommended)

| Config | Monthly Est. |
|---|---|
| Minimum 2 OCUs — billed even when idle | ~$350/month |

Too expensive for testing. Avoid.

---

## What to Keep Running vs Shut Down

### Keep Running — Zero Idle Cost

With Lambda-only mode, **everything scales to zero automatically**. There is nothing to shut down.

| Resource | Idle Cost |
|---|---|
| Lambda functions | $0 (never invoked = never charged) |
| API Gateway | $0 (no requests = no charge) |
| DynamoDB table | $0 on-demand with no reads/writes |
| Step Functions | $0 with no executions |
| Cognito User Pool | $0 |
| S3 bucket (frontend) | ~$0.02/month (storage) |
| CloudFront | $0 with no traffic |
| SSM, IAM, CloudWatch | $0 |

**Lambda-only is the ideal architecture for intermittent testing — you pay only when you use it.**

### If You Want to Eliminate All Charges (Extended Pause)

The only cost when completely idle is S3 storage (~$0.02/month). To eliminate even that:

```bash
# Empty the frontend S3 bucket (content can be re-deployed by step-4a script)
aws s3 rm s3://<BUCKET_NAME> --recursive
```

---

## Recommended Setup for Testing

| Layer | Service | Monthly Cost |
|---|---|---|
| Frontend | S3 + CloudFront | ~$0.11 |
| API | Lambda + API Gateway HTTP | ~$0.30 |
| Database + Rate Limiting | DynamoDB on-demand | ~$0.25 |
| Auth + Pre-Signup Lambda | Cognito (free) + Lambda | ~$0 |
| AI enrichment | Step Functions → Bedrock Nova Lite | ~$0.013 |
| RAG (DynamoDB vectors) | Bedrock Titan Embed + DynamoDB | ~$0.002 |
| Logs | CloudWatch (1 GB) | ~$0.50 |
| **Total (after free tier)** | | **~$1.17/month** |
| **During free tier (12 months)** | | **~$0/month** |

---

## App Runner and ECS — Not Used

`compute_mode = "serverless"` (the default and your chosen mode) creates **Lambda only**.
App Runner and ECS Fargate are never created.

- Step 3B (build/push container) → **skip entirely**
- No ECR repository needed
- No container image to maintain

App Runner (`compute_mode = "container"`) would cost ~$5–8/month and adds operational complexity. With Bedrock as the AI provider, there is no benefit to using containers.

---

## Budget Alert (Recommended)

```bash
aws budgets create-budget \
  --account-id <ACCOUNT_ID> \
  --budget '{
    "BudgetName": "reflect-monthly",
    "BudgetLimit": {"Amount": "5", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[{
    "Notification": {
      "NotificationType": "ACTUAL",
      "ComparisonOperator": "GREATER_THAN",
      "Threshold": 80
    },
    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "your@email.com"}]
  }]'
```

A $5/month budget alert is safe. If triggered, check AWS Cost Explorer to identify the source.

---

## Bedrock Model Quick Reference

| Model ID | Quality | Input $/1K | Output $/1K | Use for |
|---|---|---|---|---|
| `amazon.nova-lite-v1:0` | Good | $0.00006 | $0.00024 | Default — enrichment + insights |
| `amazon.nova-micro-v1:0` | Basic | $0.000035 | $0.00014 | Ultra-cheap simple summaries |
| `amazon.titan-embed-text-v2:0` | — | $0.00002 | — | RAG embeddings only |
| `anthropic.claude-3-haiku-20240307-v1:0` | Better | $0.00025 | $0.00125 | Higher quality RAG answers |

Start with **Nova Lite** (already default). Switch to Claude Haiku only if answer quality is insufficient.
