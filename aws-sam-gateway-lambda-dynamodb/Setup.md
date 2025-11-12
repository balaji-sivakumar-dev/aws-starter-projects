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

List table contents:
```bash
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
> Run this any time you change Python code or the template so the local container picks up the latest bundle.
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
This spins up a local API Gateway emulator + Lambda container wired to DynamoDB Local using the env file above.
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

# Grab an id from the JSON above
ID="1a31c3fc-45b9-44f7-8152-47d258340d60"

# Get one
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
1. Inspect the current profile:
   ```bash
   aws configure list
   ```
   Example output:
   ```
         Name                    Value             Type    Location
         ----                    -----             ----    --------
      profile                <not set>             None
   access_key     ****************ABCD      config-file    ~/.aws/credentials
   secret_key     ****************1234      config-file    ~/.aws/credentials
       region                ca-central-1   config-file    ~/.aws/config
   ```
2. If anything is missing, run the guided setup:
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

> ⚠️ SAM Stores the deployables in S3 Bucket 

🧹 Cleanup tip

> Deleting your stack (aws cloudformation delete-stack) does not delete the S3 bucket.

```bash
aws s3 ls | grep sam
aws s3 rb s3://<<bucket_name>> --force
```

> if there are multiple versions in the bucket (most likely), try this
```bash
BUCKET=<your-sam-artifacts-bucket>
aws s3api list-object-versions --bucket "$BUCKET" --output json \
| jq -r '.Versions[]?, .DeleteMarkers[]? | [.Key, .VersionId] | @tsv' \
| while IFS=$'\t' read -r k v; do aws s3api delete-object --bucket "$BUCKET" --key "$k" --version-id "$v"; done
aws s3api delete-bucket --bucket "$BUCKET"

```

Alternate option: use the helper script to drop the stack and purge its artifact bucket in one go.

```bash
./scripts/cleanup_sam.sh --stack sam-todo-app2 --delete-stack --region ca-central-1
```

---

## **8️⃣ Deploy to AWS with CDK **

The CDK adapter mirrors the SAM template (REST API + Lambda + DynamoDB) and uses the `PythonFunction` construct to bundle the Python source + `requirements.txt`. Run the following from `aws-sam-gateway-lambda-dynamodb/cdk`:

```bash
cd cdk
npm install           # once per machine to pull CDK + Node typings
npm run build         # transpile TypeScript -> dist/
npx cdk synth         # uses the locally installed CDK CLI
npx cdk deploy        # creates/updates the stack
```

Useful extras:
- `npx cdk diff` – preview infrastructure changes before deploying.
- `npx cdk destroy` – removes the CDK stack (clean up any residual S3 buckets if prompted).

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
