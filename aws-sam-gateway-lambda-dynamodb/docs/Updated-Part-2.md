---
title: "🏗️ Part 2 — Running a Serverless API Locally with AWS SAM (API Gateway + Lambda + DynamoDB)"
published: false
tags: aws, serverless, sam, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "Deep dive into the architecture, Lambda internals, and local-first workflow for the Todo API backend."
---

# 📘 Serverless TODO App — Article Series

| Part | Title | Link |
|------|--------|-------|
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
https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

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

# 🏗️ Architecture Overview

```
[SAM Local API Gateway]
         |
         |  (HTTP /todos)
         |
[Lambda Runtime (Docker)]
         |
         | boto3
         |
[DynamoDB Local (Docker)]
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
def lambda_handler(event, context):
    http_method = event["httpMethod"]
    resource = event["resource"]

    if resource == "/todos" and http_method == "GET":
        return list_todos()

    if resource == "/todos" and http_method == "POST":
        body = json.loads(event["body"])
        return create_todo(body)

    if resource == "/todos/{id}":
        todo_id = event["pathParameters"]["id"]

        if http_method == "GET":
            return get_todo(todo_id)

        if http_method == "PUT":
            body = json.loads(event["body"])
            return update_todo(todo_id, body)

        if http_method == "DELETE":
            return delete_todo(todo_id)

    return {"statusCode": 404, "body": "Not Found"}
```

✔ Simple but effective routing  
✔ One Lambda for all endpoints  
✔ Fast & cost-efficient  

---

## **2️⃣ Pydantic Models (src/models.py)**

```python
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TodoUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    status: Optional[str]

class TodoItem:
    @staticmethod
    def now():
        return datetime.utcnow().isoformat()
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
    payload = TodoCreate(**data)

    item = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "status": "pending",
        "created_at": TodoItem.now(),
        "updated_at": TodoItem.now(),
    }

    table.put_item(Item=item)

    return {"statusCode": 200, "body": json.dumps(item)}
```

✔ Validated input  
✔ UUID generation  
✔ Auto timestamps  

---

## **5️⃣ SAM Template (excerpt)**

```yaml
Resources:
  TodoFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.13
      Handler: app.lambda_handler
      CodeUri: src/
      Environment:
        Variables:
          TABLE_NAME: local-todos
          DDB_ENDPOINT: http://host.docker.internal:8000
      Events:
        TodosApi:
          Type: Api
          Properties:
            Path: /todos
            Method: ANY
```

✔ Shows how API routes map to Lambda  
✔ Shows environment variables for local DB  

---

# 🏃‍♂️ Running the Backend Locally

## **1️⃣ Start DynamoDB Local**

```bash
docker compose up -d
```

---

## **2️⃣ Seed Data**

```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000
python3 scripts/seed_local_ddb.py
```

---

## **3️⃣ Build the Project**

```bash
sam build
```

---

## **4️⃣ Create env_local.json**

```json
{
  "TodoFunction": {
    "TABLE_NAME": "local-todos",
    "DDB_ENDPOINT": "http://host.docker.internal:8000"
  }
}
```

---

## **5️⃣ Start Local API Gateway**

```bash
sam local start-api --env-vars env_local.json
```

Endpoint:

```
http://127.0.0.1:3000
```

---

# **6️⃣ Test Endpoints with curl**

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
👉 https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

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
