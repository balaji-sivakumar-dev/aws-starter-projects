# AWS SAM Todo App – Local‑first + CDK‑ready

## Services in This Starter
- **AWS SAM (Serverless Application Model)** – an open-source framework + CLI that lets you define serverless infrastructure as concise YAML/JSON and run the stack locally with the same Lambda runtime Docker uses in AWS.
- **AWS SAM CLI** – the developer toolchain that compiles the SAM template into CloudFormation, runs `sam local start-api`, and drives guided deployments so you can ship the stack without manually crafting AWS CLI commands.
- **AWS Lambda** – the compute service that executes `src/app.py` on-demand. You only pay for milliseconds of execution time and never manage servers or scaling.
- **Amazon DynamoDB** – the fully managed NoSQL database backing the Todo items. In this project you can swap between DynamoDB Local (Docker) for dev and the managed service for prod.
- **Amazon API Gateway (HTTP API)** – the managed front door that exposes `/todos` endpoints, handles CORS, and forwards requests to the Lambda function with minimal configuration.

A complete, **local‑first** serverless Todo API using **API Gateway + Lambda + DynamoDB** with **AWS SAM**. Includes optional **DynamoDB Local** via Docker, sample seed data, and a **CDK adapter** you can use when you’re ready to deploy on AWS using AWS CDK.

---

## ✅ Features
- CRUD endpoints: `POST /todos`, `GET /todos`, `GET /todos/{id}`, `PUT /todos/{id}`, `DELETE /todos/{id}`
- Single Lambda with lightweight in‑function router
- DynamoDB table with a GSI on `status`
- Local dev with `sam local start-api` and **DynamoDB Local** (Docker)
- Seed script to create the table locally and insert sample items
- CORS enabled
- **CDK adapter (TypeScript)** mirroring the same stack so you can deploy later

---

## 🧱 Project Structure
```
aws-sam-todo/
├─ template.yaml                      # SAM template (API, Lambda, DynamoDB)
├─ README.md                          # Project overview (this file)
├─ Setup.md                           # Step-by-step setup & deployment
├─ docker-compose.yml                 # DynamoDB Local
├─ requirements.txt                   # Python Lambda deps
├─ src/
│  ├─ app.py                          # Lambda handler with router
│  ├─ ddb.py                          # DynamoDB helper
│  └─ models.py                       # Pydantic models
├─ scripts/
│  ├─ seed_local_ddb.py               # Creates local table & seeds test data
│  └─ sample_events/
│     ├─ post_todo.json
│     ├─ put_todo.json
│     └─ api_gateway_proxy_get.json
├─ tests/
│  └─ test_todos.py                   # (optional) pytest tests
└─ cdk/                               # Optional CDK adapter (TypeScript)
   ├─ bin/todo.ts
   ├─ lib/todo-stack.ts
   ├─ package.json
   ├─ tsconfig.json
   └─ cdk.json
```

---

## ⚙️ API Endpoints
| Method | Path            | Purpose                 |
|-------:|-----------------|-------------------------|
| POST   | `/todos`        | Create a todo           |
| GET    | `/todos`        | List todos              |
| GET    | `/todos/{id}`   | Get one todo by id      |
| PUT    | `/todos/{id}`   | Update fields/status    |
| DELETE | `/todos/{id}`   | Delete a todo           |

---

## 🧠 How It Works
1. **SAM** provisions Lambda + API Gateway + DynamoDB (or runs them locally via Docker).
2. `src/app.py` performs light routing and uses `src/ddb.py` to interact with DynamoDB.
3. For **local development**, `DDB_ENDPOINT` points to **DynamoDB Local** (Docker).  
   For **cloud deployment**, `DDB_ENDPOINT` is empty so the app uses **AWS DynamoDB**.

---

## 📦 Tech Stack
- **Python 3.11** (Lambda runtime)
- **AWS SAM** (local-first IaC + CLI)
- **DynamoDB** / **DynamoDB Local**
- **AWS CDK (TypeScript)** adapter
- **boto3**, **pydantic**

---

## 💰 Cost Note
- Local work (SAM + DynamoDB Local) is free.
- SAM/CDK cloud deploys upload artifacts to an S3 bucket; the first 5 GB is free for 12 months, then standard S3 storage/request pricing applies until you delete the bucket.

---

## 🚀 Roadmap Ideas
- Auth with Amazon Cognito (JWT authorizer)
- Pagination with `LastEvaluatedKey`
- Replace table `scan` with GSI query for `status`
- Observability with AWS Lambda Powertools (logs/metrics/traces)
- CI/CD via GitHub Actions (SAM and/or CDK pipelines)
- WAF, throttling, request validation at API Gateway

---

## 📚 References
- AWS SAM – https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html
- AWS CDK – https://docs.aws.amazon.com/cdk/latest/guide/home.html
- DynamoDB Local – https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html
