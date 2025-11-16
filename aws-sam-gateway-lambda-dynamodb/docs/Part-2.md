---
title: "🏗️ Part 2 — Running a Serverless API Locally with AWS SAM (API Gateway + Lambda + DynamoDB)"
published: false
tags: aws, serverless, sam, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "Deep dive into the architecture, Lambda internals, and local-first workflow for the Todo API backend."
---

# 📘 Serverless TODO App — Article Series

| Part | Title | 
|------|--------|
| **1** | [Architecture Overview](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m) |
| **2** | [Local Backend with AWS SAM *(You are here)*](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m) |
| **3** | Deploying Backend to AWS (SAM + CDK) - *(Coming soon…)* |

---

# 🏗️ Part 2 — Running a Serverless API Locally with AWS SAM  
### (API Gateway + Lambda + DynamoDB Local)

This article expands on **Part 1**, diving into how the backend works and how to run it **fully locally** using:

- AWS SAM  
- Local Lambda (Docker)  
- DynamoDB Local  
- Seed scripts  
- curl-based testing  

This ensures rapid, cost-free development before deploying to AWS (in Part 3).

🔗 **GitHub Repo:**  
👉 [aws-sam-gateway-lambda-dynamodb](https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb)

> Scope: Part 2 is **local-only**. Cloud deploy, auth, and hardening land in Part 3.

---

# 🧰 Prerequisites for Local-Only
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Docker (for Lambda + DynamoDB Local containers)](https://www.docker.com/products/docker-desktop/)
- [Python 3.13](https://www.python.org/downloads/)
- [Optional: AWS CLI (not required for local-only; dummy creds work)](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

---

# 🎯 What This Part Covers

- How Lambda routing, validation, and DB access work together  
- How SAM emulates API Gateway + Lambda  
- How DynamoDB Local integrates via environment variables  
- Full local run workflow  
- curl commands to test every endpoint  

---

# 🧭 Why Local-First Development?

Local-first gives:

- Instant iteration  
- No AWS costs  
- Offline development  
- Safe experimentation  
- Faster debugging  
- Confidence before cloud deployment  

SAM provides a **near-identical Lambda runtime** locally using Docker.

---

# 🏗️ Architecture Overview & What You’ll Build

Single Lambda handles all `/todos` routes, talking to DynamoDB Local via SAM’s local API Gateway:

```
┌──────────────────────────┐
│ API Gateway (Local)      │
└──────────────┬───────────┘
               │
        /todos routes
               │
┌──────────────▼───────────┐
│ AWS Lambda (Python 3.13) │  <-- src/app.py
│ Router + Handlers (Local)│
└──────────────┬───────────┘
               │ boto3
┌──────────────▼───────────┐
│ DynamoDB (Local)         │
└──────────────────────────┘
```

---

# 🧩 What the Backend Does

CRUD API for TODO items:

| Method | Route | Description |
|--------|--------|-------------|
| GET | /todos | List all items |
| GET | /todos/{id} | Get by ID |
| POST | /todos | Create |
| PUT | /todos/{id} | Update |
| DELETE | /todos/{id} | Delete |

---

# 🧠 Deep Dive — How the Lambda Works

Below are the **essential excerpts** needed to understand the backend logic.

---

## **1️⃣ Lambda Router (src/app.py)**

```python
def handler(event, context):
    path = event.get("resource") or event.get("path", "")
    http_method = event.get("httpMethod", "GET").upper()
    path_params = event.get("pathParameters") or {}

    if path == "/todos" and http_method == "POST":
        return create_todo(event)
    if path == "/todos" and http_method == "GET":
        return list_todos(event)
    if path == "/todos/{id}" and http_method == "GET":
        return get_todo(path_params.get("id"))
    if path == "/todos/{id}" and http_method == "PUT":
        return update_todo(path_params.get("id"), event)
    if path == "/todos/{id}" and http_method == "DELETE":
        return delete_todo(path_params.get("id"))

    return _response(404, {"message": "Not Found"})
```

✔ Simple but effective routing  
✔ One Lambda for all endpoints  
✔ Fast & cost-efficient  

---

## **2️⃣ Pydantic Models (src/models.py)**

```python
class TodoCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: str = Field(default="pending")  # pending|done

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
```

✔ Ensures clean validation  
✔ Protects API from malformed payloads  

---

## **3️⃣ DynamoDB Layer (src/ddb.py)**

```python
ddb = boto3.resource(
    "dynamodb",
    endpoint_url=os.getenv("DDB_ENDPOINT")  # Local or AWS
)

table = ddb.Table(os.getenv("TABLE_NAME"))
```

This makes the DB layer **environment-agnostic**.

---

## **4️⃣ Example Handler — Create Todo**

```python
def create_todo(data):
    payload = TodoCreate(**json.loads(data.get("body") or "{}"))

    item = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "status": payload.status,
        "created_at": TodoItem.now_iso(),
        "updated_at": TodoItem.now_iso(),
    }

    table.put_item(Item=item)

    return _response(201, item)
```

✔ Validated input  
✔ UUID generation  
✔ Auto timestamps  

---

## **5️⃣ SAM Template — What Each Part Does**

- **Globals**  
  Sets defaults for all functions: `Runtime: python3.13`, `Timeout: 20s`, and environment variables. `TABLE_NAME` and `DDB_ENDPOINT` are injected into the Lambda so the code can read `os.environ` without hardcoding names or endpoints.

- **TodoTable (DynamoDB)**  
  Pay-per-request table named `${StackName}-todos` with a primary key `id` and a `status-index` GSI. This is the backing store the Lambda writes to and reads from.

- **HttpApi (API Gateway)**  
  Defines the HTTP API (`StageName: v1`) with permissive CORS for local dev.

- **TodoFunction (Lambda)**  
  - `CodeUri: src/` and `Handler: app.handler` point to the Python entry point (`src/app.py::handler`).  
  - `Policies: DynamoDBCrudPolicy` grants read/write access to `TodoTable`.  
  - `Events` map HTTP routes to this single Lambda:
    - `POST /todos`
    - `GET /todos`
    - `GET /todos/{id}`
    - `PUT /todos/{id}`
    - `DELETE /todos/{id}`
  - In AWS, `DDB_ENDPOINT` is empty (real DynamoDB). For local runs, override it in `env_local.json` to point at DynamoDB Local.

- **Outputs**  
  Expose the API URL and table name after deploy for easy copy/paste/testing.

---

# 🏃‍♂️ Running the Backend Locally

## **1️⃣ Start DynamoDB Local**

```bash
docker compose up -d
```

If you don’t have AWS creds configured, export dummy values so CLI + seed script work:
```bash
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export AWS_REGION=ca-central-1
```

---

## **2️⃣ Create & Activate Python Virtual Environment using venv**

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r src/requirements.txt
```

Deactivate any time:
```bash
deactivate
```

---

## **3️⃣ Seed Data**

```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000
python3 scripts/seed_local_ddb.py
```

---

## **4️⃣ Build the Project**

```bash
sam build
```

---

## **5️⃣ Create env_local.json**

```json
{
  "TodoFunction": {
    "TABLE_NAME": "local-todos",
    "DDB_ENDPOINT": "http://host.docker.internal:8000"
  }
}
```

---

## **6️⃣ Start Local API Gateway**

```bash
sam local start-api --env-vars env_local.json
```

Endpoint:

```
http://127.0.0.1:3000
```

---

# **7️⃣ Test Endpoints with curl (smoke test)**

```bash
# Create
curl -sS -X POST http://127.0.0.1:3000/todos   -H 'Content-Type: application/json'   -d '{"title":"First Todo","description":"hello"}' | jq

# List
curl -sS http://127.0.0.1:3000/todos | jq

# Grab an id from the JSON above
ID="1a31c3fc-45b9-44f7-8152-47d258340d60"

# Get one
curl -sS http://127.0.0.1:3000/todos/$ID | jq

# Update
curl -sS -X PUT http://127.0.0.1:3000/todos/$ID   -H 'Content-Type: application/json'   -d '{"status":"done"}' | jq

# Delete
curl -i -sS -X DELETE http://127.0.0.1:3000/todos/$ID
```

---

# 📚 Additional Resources

GitHub Repository:  
👉 [aws-sam-gateway-lambda-dynamodb](https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb)

---

# ⏭️ Coming Up in Part 3

Part 3 covers:

- Deploying to AWS with SAM  
- Deploying to AWS with CDK  
- S3 packaging  
- API Gateway  
- DynamoDB  
- AWS Free Tier vs Always-Free Notes  
- Budget Alerts to avoid costs  

Stay tuned! 🚀
