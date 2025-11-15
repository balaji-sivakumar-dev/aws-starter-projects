---
title: "🏗️ Part 2 — Running a Serverless API Locally with AWS SAM (API Gateway + Lambda + DynamoDB)"
published: false
tags: aws, serverless, sam, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/q3p0fmx9d47j4vkgc46u.png
description: "Deep dive into the architecture, local-first workflow, and deployment paths (SAM + CDK) for the Todo API backend."
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
- Deployment using **AWS SAM** (CloudFormation)  
- Deployment using **AWS CDK** (no application code changes required)  
- A teaser for Part 3: UI + Cognito Authentication  

---

# 🧭 Motivation — Why Build This?

Most AWS tutorials show you how to write and deploy a Lambda function, but they rarely address the real challenges:

- How do you run AWS Lambda locally?  
- How do you emulate API Gateway locally?  
- How do you test DynamoDB without AWS charges?  
- How do you seed test data?  
- How can SAM and CDK deploy the same codebase?

This project solves all of these.

The goal is to create a **production-shaped**, cloud-ready backend that:

- Runs 100% locally  
- Uses local DynamoDB for fast development  
- Uses SAM to emulate API Gateway + Lambda in containers  
- Deploys unchanged to AWS using SAM **or** CDK  

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
│ DynamoDB (Local / AWS)    │
└───────────────────────────┘
```

### Components

| Component | Purpose |
|----------|---------|
| **API Gateway** | Exposes REST endpoints |
| **Lambda** | Contains router + CRUD handlers |
| **DynamoDB** | Storage for TODO items |
| **DynamoDB Local** | Local database for fast testing |
| **AWS SAM** | Local Lambda + API Gateway emulator |
| **AWS CDK** | Alternate IaC deployment path |

---

# 🧩 What This Backend Does

The backend implements a complete CRUD API for TODO items.

### Endpoints

| Method | Route | Description |
|-------|--------|-------------|
| POST | `/todos` | Create a new TODO |
| GET | `/todos` | List all TODOs |
| GET | `/todos/{id}` | Fetch a specific TODO |
| PUT | `/todos/{id}` | Update a TODO |
| DELETE | `/todos/{id}` | Delete a TODO |

### DynamoDB Schema

Each TODO item includes:

- `id`  
- `title`  
- `description`  
- `status`  
- `created_at`  
- `updated_at`

A **GSI on `status`** is designed for future filtered queries.

---

# 🧠 Deep Dive — How the Lambda Works

## 1️⃣ SAM Template (`template.yaml`)

The SAM template defines:

- Lambda runtime (Python 3.13)
- Source code directory (`src/`)
- API routes mapping
- DynamoDB table and GSI
- Environment variables:
  - `TABLE_NAME`
  - `DDB_ENDPOINT` (used only for local runs)

SAM uses CloudFormation under the hood for deployment.

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

This design allows **one Lambda to manage all routes**, keeping the architecture simple and cost-efficient.

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
`DDB_ENDPOINT=http://localhost:8000`

### AWS  
Environment variable omitted → connect to real DynamoDB.

No code changes needed.

---

# 🏃‍♂️ Running the Backend Locally (AWS SAM)

This is the main highlight of this project — **running real Lambda + API Gateway locally**.

---

## 1️⃣ Start DynamoDB Local (Docker)

```bash
docker compose up -d
```

Runs on `localhost:8000`.

---

## 2️⃣ Seed the Local DB

```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000
python3 scripts/seed_local_ddb.py
```

---

## 3️⃣ Build the Lambda Using SAM

```bash
sam build
```

---

## 4️⃣ Create env file for the local Lambda container

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

---

## 5️⃣ Start the Local API Gateway + Lambda Emulator

```bash
sam local start-api --env-vars env_local.json
```

Test it:

```bash
curl http://127.0.0.1:3000/todos | jq
```

🎉 *You now have a fully local, serverless API running on your laptop!*

---

# ☁️ Deploying to AWS (Using SAM)

```bash
sam build
sam deploy --guided
```

SAM will:

- Package the Lambda
- Upload artifacts to S3
- Create DynamoDB table, IAM roles, API Gateway
- Output the public API URL

Future deploys:

```bash
sam deploy
```

Cleanup:

```bash
aws cloudformation delete-stack --stack-name <stack-name>
```

---

# 🧰 Deploying Using CDK (Same Codebase, Zero Changes)

Inside `cdk/lib/todo-stack.ts`, the entire infrastructure is defined using CDK.

Commands:

```bash
cd cdk
npm install
npm run build
npx cdk synth
npx cdk deploy
```

Destroy:

```bash
npx cdk destroy
```

The Lambda code (`src/`) stays untouched — proving that your backend logic is **IaC-agnostic**.

---

# ⚠️ **Important Watchouts — AWS Free Tier & Cost Notes**

Although this project is designed to stay *within free-tier limits*, there are some important cost considerations to be aware of:

### **1️⃣ S3 Upload Costs (SAM / CDK Deployments)**  
Both **SAM** and **CDK** upload your Lambda package to an S3 bucket.  
S3 is **not always free** unless you are in your first 12 months on AWS.

- S3 storage: may incur small charges after free tier (5GB for 12 months only)  
- S3 PUT requests: may incur costs depending on number of deployments  

⚠️ *If you deploy frequently, watch your S3 usage.*

---

### **2️⃣ API Gateway Free Tier Is NOT “Always Free”**  
Amazon API Gateway offers:

- **1M REST API calls/month — only for the first 12 months**

After that period, you will incur charges per million requests.

If your API is idle, cost will be near zero, but it is **not always free**.

---

### **3️⃣ DynamoDB Is Always Free (Up to Limits)**  
DynamoDB has an *always-free* tier:

- 25GB storage  
- Limited read/write request units  

This is safe for hobby projects as long as:

- You use **on-demand** mode (recommended)
- You stay within read/write limits

---

### **4️⃣ Lambda Has an Always-Free Tier**  
You get:

- 1M requests/month (always free)  
- 400,000 GB-seconds compute/month  

Most personal projects never exceed these.

---

### **5️⃣ CloudFormation / CDK / SAM Itself Is Free**  
But the resources they create may not be.

---

### **✔️ Recommended Action**  
Set up an AWS **Budget Alert** (free):

- Set threshold to **$1 or $2**
- Receive email if anything is created that may incur cost

---

## 📚 Additional Resources

### 🔗 GitHub Repository (Full Source Code)
All code for this backend (SAM, CDK, Lambda, DynamoDB) is available here:

👉 **https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb**

Feel free to explore the repo, open issues, or adapt it for your own serverless projects.

---

# 👀 Coming Up in Part 3 — UI + Cognito Authentication

Part 3 will focus on:

- React + Vite frontend  
- AWS Cognito Hosted UI  
- Persisting user sessions  
- Calling this backend with JWT authentication  
- Deploying UI to Vercel or Amplify  

Stay tuned — Part 3 completes the full-stack serverless TODO application! 🚀