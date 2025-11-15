---
title: "🏗️ Part 2 — Running a Serverless API Locally with AWS SAM (API Gateway + Lambda + DynamoDB)"
published: false
tags: aws, serverless, sam, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "Deep dive into the architecture, local-first workflow, and developer experience for the Todo API backend."
---

# 🏗️ Part 2 — Running a Serverless API Locally with AWS SAM  
### (API Gateway + Lambda + DynamoDB)

This article continues from **Part 1**, where I introduced the end-to-end architecture for building my serverless TODO application.  
In this Part 2, we focus entirely on the **backend**, located in this public GitHub folder:

🔗 **GitHub Repo (Source Code for Part 2)**  
https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# 🎯 What This Part Covers

- The architecture, purpose, and motivation behind this backend  
- How the Lambda function is structured and how each critical component works  
- How to run this entire serverless stack **locally** using AWS SAM  
- How DynamoDB Local and Lambda containers integrate seamlessly  
- How this local-first workflow prepares you for cloud deployment (covered in Part 3)  

👉 **Note:** Deploying this stack to real AWS (with SAM or CDK) and configuring AWS credentials will be covered in **Part 3**.

---

# 🧭 Motivation — Why Build This?

Most AWS tutorials show you how to write and deploy a Lambda function, but they rarely address the real challenges:

- How do you run AWS Lambda locally?  
- How do you emulate API Gateway locally?  
- How do you test DynamoDB without AWS charges?  
- How do you seed test data?  

This project solves all of these.

The goal is to create a **production-shaped**, cloud-ready backend that:

- Runs 100% locally  
- Uses local DynamoDB for fast development  
- Uses SAM to emulate API Gateway + Lambda in containers  

This becomes the backend foundation for the full Todo App.

---

# 🏗️ Architecture Overview

Here is the structure of the backend:

```
┌──────────────────────────┐
│ API Gateway (Local / AWS)│
└──────────────┬───────────┘
               │
        /todos routes
               │
┌──────────────▼───────────┐
│  AWS Lambda (Python 3.13)│  <-- src/app.py
│  Router + Handlers       │
└──────────────┬───────────┘
               │ boto3
┌──────────────▼───────────┐
│ DynamoDB (Local / AWS)   │
└───────────────────────────┘
```

### Components

| Component | Purpose |
|----------|---------|
| **API Gateway (emulated by SAM)** | Exposes REST endpoints locally |
| **Lambda** | Contains router + CRUD handlers |
| **DynamoDB** | Storage for TODO items |
| **DynamoDB Local** | Local database for fast testing |
| **AWS SAM** | Local Lambda + API Gateway emulator |

---

# 🧩 What This Backend Does

The backend implements a complete CRUD API for TODO items.

### Endpoints

| Method | Route | Description |
|-------|--------|-------------|
| POST | `/todos` | Create a new TODO |
| GET  | `/todos` | List all TODOs |
| GET  | `/todos/{id}` | Fetch a specific TODO |
| PUT  | `/todos/{id}` | Update a TODO |
| DELETE | `/todos/{id}` | Delete a TODO |

### DynamoDB Schema

Each TODO item includes:

- `id`  
- `title`  
- `description`  
- `status`  
- `created_at`  
- `updated_at`  

💡 *Future enhancement:* A **GSI on `status`** can be added later to support filtered queries such as `/todos?status=done`. It is not required for the current implementation.

---

# 🧠 Deep Dive — How the Lambda Works

## 1️⃣ SAM Template (`template.yaml`)

The SAM template defines:

- Lambda runtime (currently `python3.13`)  
- Source code directory (`src/`)  
- API routes mapping  
- DynamoDB table  
- Environment variables:
  - `TABLE_NAME`
  - `DDB_ENDPOINT` (used only for local runs)

If you prefer a different Python version (e.g. `python3.11`), you can update the `Runtime` field in `template.yaml` without changing the app code.

SAM uses CloudFormation under the hood, but in this part we only use it for **local emulation**, not real AWS deployment.

---

## 2️⃣ Router + Handlers (`src/app.py`)

The Lambda acts as a small router:

```python
http_method = event["httpMethod"]
resource = event["resource"]
```

It dispatches each request to:

- `create_todo`
- `list_todos`
- `get_todo`
- `update_todo`
- `delete_todo`

This design allows **one Lambda to manage all routes**, keeping the architecture simple and cost-efficient for a small app.

---

## 3️⃣ Input Validation (`models.py`)

Using **Pydantic** for:

- `TodoCreate`
- `TodoUpdate`

Benefits:

- Strong typing  
- Automatic validation  
- Clean error messages  
- Uniform ISO8601 timestamps  

---

## 4️⃣ DynamoDB Layer (`ddb.py`)

```python
ddb = boto3.resource("dynamodb", endpoint_url=os.getenv("DDB_ENDPOINT"))
```

This makes the backend environment-agnostic:

### Local  
`DDB_ENDPOINT=http://localhost:8000` → points to **DynamoDB Local**.

### Later in AWS  
When `DDB_ENDPOINT` is not set, `boto3` will connect to **managed DynamoDB** (we’ll use this in Part 3).

No code changes needed — only environment changes.

---

# 🏃‍♂️ Running the Backend Locally (AWS SAM)

This is the main highlight of this project — **running real Lambda + API Gateway locally**.

---

## 1️⃣ Start DynamoDB Local (Docker)

```bash
docker compose up -d
```

This will start **DynamoDB Local** on `localhost:8000` based on the `docker-compose.yml` in the project.

---

## 2️⃣ Seed the Local DB

```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000
python3 scripts/seed_local_ddb.py
```

This script will:

- Create the table (if it doesn’t exist)  
- Insert some sample TODO items  

---

## 3️⃣ Build the Lambda Using SAM

```bash
sam build
```

SAM will package the Lambda code using the runtime defined in `template.yaml`.

---

## 4️⃣ Create env file for the local Lambda container

Create `env_local.json` in the project root:

```bash
cat > env_local.json <<'JSON'
{
  "TodoFunction": {
    "TABLE_NAME": "local-todos",
    "DDB_ENDPOINT": "http://host.docker.internal:8000"
  }
}
JSON
```

`host.docker.internal` lets the Lambda container talk to DynamoDB Local running on your host machine.

---

## 5️⃣ Start the Local API Gateway + Lambda Emulator

```bash
sam local start-api --env-vars env_local.json
```

Test it:

```bash
curl http://127.0.0.1:3000/todos | jq
```

You should see the seeded TODO items from DynamoDB Local.

🎉 *You now have a fully local, serverless API running on your laptop!*  

This tight feedback loop is what makes SAM + DynamoDB Local such a powerful combo for backend development.

---

## 📚 Additional Resources

### 🔗 GitHub Repository (Full Source Code)
All code for this backend (SAM templates, Lambda, DynamoDB Local scripts) is available here:

👉 **https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb**

Feel free to explore the repo, open issues, or adapt it for your own serverless projects.

---

# 👀 Coming Up in Part 3 — Deploying to AWS (SAM + CDK + Cost Watchouts)

In **Part 3**, we’ll move from local-only development to **real AWS deployment**:

- Configuring AWS credentials safely  
- How SAM packages and uploads to S3  
- Deploying the stack to AWS using **SAM**  
- Deploying the same code using **CDK**  
- Understanding AWS free tier vs “always free”  
- Setting up AWS Budgets to avoid surprises  

Later, in **Part 4**, we’ll wire this backend to:

- A React + Vite frontend  
- AWS Cognito Hosted UI for authentication  
- Vercel (or Amplify) for frontend hosting  

Stay tuned — we’ll take this local backend all the way to production-ready! 🚀
