# **Setup.md — Run Locally with AWS SAM & Deploy with CDK**

This guide walks you through:
1. 🧱 Running locally with **AWS SAM + DynamoDB Local**  
2. ☁️ Deploying to AWS using **SAM**  
3. 🧩 Optionally deploying with **AWS CDK (TypeScript)**  

> Tested on **macOS (Apple Silicon)**. Commands are nearly identical for Linux and Windows (use PowerShell equivalents).

---

## **0️⃣ Prerequisites**
Make sure these are installed:

| Tool | Required for | Install / Docs |
|------|---------------|----------------|
| **AWS SAM CLI (≥ 1.144)** | Local build & deploy | [Install SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) |
| **Docker Desktop** | DynamoDB Local & SAM containers | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| **Python 3.13 + pip** | Lambda runtime | `brew install python` |
| **AWS CLI v2** | Cloud deploys | [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) |
| **Node 18+ + npm** | Only for CDK adapter | [Node LTS](https://nodejs.org) |

Verify versions:
```bash
sam --version
docker --version
python3 --version
aws --version
node --version     # only if using CDK
npm --version      # only if using CDK
```

---

## **1️⃣ Clone & Prepare Environment**

```bash
git clone <your-repo-url>
cd aws-sam-gateway-lambda-dynamodb
```

### 🔹 Create a Virtual Environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate      # (venv) prompt appears
pip install aws-sam-cli boto3
```

Deactivate any time with:
```bash
deactivate
```

---

## **2️⃣ Install Dependencies & Build**

> Simply place `requirements.txt` in `src/` and let `sam build` handle it.

```bash
cd aws-sam-gateway-lambda-dynamodb
sam build
```

If you want to confirm the Python runtime, open `template.yaml` — it should read:
```yaml
Globals:
  Function:
    Runtime: python3.13
```

---

## **3️⃣ Start DynamoDB Local (Docker)**

```bash
docker compose up -d
docker ps | grep dynamodb-local
```

✅ You should see `0.0.0.0:8000->8000/tcp` in the PORTS column.

Check it’s responding:
```bash
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

# List table content 
```
aws dynamodb scan --endpoint-url http://localhost:8000 --table-name local-todos
```
---

## **4️⃣ Seed Local Table**

This creates and seeds a test table inside DynamoDB Local.

```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000
python3 scripts/seed_local_ddb.py
```

Expected output:
```
Creating table...
Table ready: local-todos
Seeded 3 items.
```

---

## **5️⃣ Run the API Locally**

### 5.1 Build (if needed)
```bash
sam build
```

### 5.2 Create `env_local.json` for local run
> On macOS/Windows, use `host.docker.internal`.  
> On Linux, use `localhost`.

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

### 5.3 Start the local API
```bash
sam local start-api --env-vars env_local.json
```

Output shows a local endpoint like:
```
Mounting TodoFunction at http://127.0.0.1:3000/todos [GET,POST,...]
```

---

## **6️⃣ Test Endpoints**
```bash
# Create
curl -sS -X POST http://127.0.0.1:3000/todos \
  -H 'Content-Type: application/json' \
  -d '{"title":"First Todo","description":"hello"}' | jq

# List
curl -sS http://127.0.0.1:3000/todos | jq

# Get one
ID="ac4c77bc-d368-4657-b2b8-107d059518fc"
curl -sS http://127.0.0.1:3000/todos/$ID | jq

# Update
curl -sS -X PUT http://127.0.0.1:3000/todos/$ID \
  -H 'Content-Type: application/json' \
  -d '{"status":"done"}' | jq

# Delete
curl -i -sS -X DELETE http://127.0.0.1:3000/todos/$ID
```

Stop the API with `Ctrl +C`.  
Stop DynamoDB Local with:
```bash
docker compose down
```

---

## **7️⃣ Deploy to AWS with SAM**

Ensure AWS CLI credentials are configured:

Verify if credentials are configured:
```bash
aws configure list
```

You should see something like:
```bash
      Name                    Value             Type    Location
      ----                    -----             ----    --------
   profile                <not set>             None
access_key     ****************ABCD      config-file    ~/.aws/credentials
secret_key     ****************1234      config-file    ~/.aws/credentials
    region                ca-central-1      config-file    ~/.aws/config

```
```bash
aws configure
```

Deploy:
```bash
sam build
sam deploy --guided
```

Follow the prompts:
- Stack Name (e.g., `sam-todo-stack`)
- Region (e.g., `ca-central-1`)
- Confirm IAM role creation
- Save to a config file (yes)

Test deployed API:
```bash
API_URL="https://xxxxxx.execute-api.<region>.amazonaws.com/v1"
curl -sS "$API_URL/todos" | jq
```

Redeploy:
```bash
sam build && sam deploy
```

Remove stack:
```bash
aws cloudformation delete-stack --stack-name sam-todo-stack
```

---

## **8️⃣ Deploy to AWS with CDK (Optional)**

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

---

## **9️⃣ Environment Variables**

| Mode | TABLE_NAME | DDB_ENDPOINT |
|------|-------------|---------------|
| **Local (host)** | `local-todos` | `http://localhost:8000` |
| **Local via SAM (Docker)** | `local-todos` | `http://host.docker.internal:8000` |
| **Cloud (AWS)** | *auto from stack* | *unset* |

---

## **🔟 Troubleshooting**

| Issue | Fix |
|-------|-----|
| **Connection refused to DDB Local** | Ensure container maps `8000:8000`; run `docker compose up -d` |
| **SAM can’t reach DDB Local on macOS/Windows** | Use `host.docker.internal` in `env.json` |
| **Missing modules** | Run `sam build` (after ensuring `src/requirements.txt`) |
| **Permission denied in cloud** | Re-deploy so IAM policy updates propagate |
| **CORS** | Demo uses `'*'`; restrict origins for production |

---

## **💰 Costs & Cleanup**

| Environment | Cost |
|--------------|------|
| **Local (Docker)** | Free |
| **AWS Cloud** | Pay-per-use (Lambda + API Gateway + DynamoDB) |
| **Cleanup** | `aws cloudformation delete-stack --stack-name <name>` or `npx cdk destroy` |

---

## 10) What’s Next
- Add Cognito JWT authorizer for protected routes.
- Add request validation and schema checks.
- Add pagination & GSI queries by `status`.
- Add CloudWatch dashboards and Powertools.
- Add a frontend (React/Next.js/Expo) that calls this API.

Happy building! 🚀
