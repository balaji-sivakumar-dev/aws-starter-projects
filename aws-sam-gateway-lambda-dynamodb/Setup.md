# Setup.md — Run Locally with SAM & Deploy with CDK

This guide walks you through:
1) **Running locally** with **AWS SAM** + **DynamoDB Local**  
2) **Deploying to AWS** using **SAM**  
3) **Deploying to AWS** using the optional **CDK adapter** (TypeScript)

> Tested on macOS. Commands are similar on Linux/Windows (PowerShell may need slight changes).

---

## 0) Prerequisites
- **AWS SAM CLI**: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
- **Docker Desktop** (for DynamoDB Local): https://www.docker.com/products/docker-desktop/
- **Python 3.11** + `pip`
- **Node.js 18+** (only if using the CDK adapter)
- **AWS CLI v2** (configured with credentials if you plan to deploy)

Verify:
```bash
sam --version
docker --version
python3 --version
aws --version
node --version   # only for CDK
npm --version    # only for CDK
```

---

## 1) Clone & Install Dependencies

### 🧹 Use Virtual Environments (recommended)

To keep dependencies isolated per project:
```
cd aws-sam-gateway-lambda-dynamodb

# Create venv folder
python3 -m venv venv

# Activate it
source venv/bin/activate

# (You’ll see your prompt change, e.g. (venv) MacBook$)

# Then install your project deps inside venv
pip install -r requirements.txt -t src/

# To Deactivate Virtual Environment

deactivate

```
### Install Python Dependencies

```bash
cd aws-sam-gateway-lambda-dynamodb

# Install Python deps into the Lambda src folder
pip install -r requirements.txt -t src/
```

> Why install into `src/`? So that `sam build` bundles the dependencies alongside the handler.

---

## 2) Start DynamoDB Local (Docker)
```bash
docker compose up -d
# confirm it is running
docker ps | grep dynamodb-local
```

By default this starts **DynamoDB Local** at `http://localhost:8000` (mapped to container port `8000`).

---

## 3) (Optional) Seed Local Table
Create and seed a **local** table (separate from the SAM stack’s cloud table):
```bash
export TABLE_NAME=local-todos
export DDB_ENDPOINT=http://localhost:8000

python scripts/seed_local_ddb.py
```

You should see:
- “Creating table…” (first run) and then “Table ready: local-todos”
- “Seeded 3 items.”

---

## 4) Run the API Locally (SAM)
Build and start the local API:
```bash
sam build

# Point Lambda at DynamoDB Local.
# macOS/Windows Docker often needs host.docker.internal. On Linux, use localhost.
cat > env.json << 'JSON'
{
  "TodoFunction": {
    "TABLE_NAME": "local-todos",
    "DDB_ENDPOINT": "http://host.docker.internal:8000"
  }
}
JSON

sam local start-api --env-vars env.json
```

You’ll see the local endpoint, typically: `http://127.0.0.1:3000`.

### Test the endpoints
```bash
# Create
curl -sS -X POST http://127.0.0.1:3000/todos   -H 'Content-Type: application/json'   -d '{"title":"First Todo","description":"hello"}' | jq

# List
curl -sS http://127.0.0.1:3000/todos | jq

# Get by ID
ID="<paste id from create/list>"
curl -sS http://127.0.0.1:3000/todos/$ID | jq

# Update
curl -sS -X PUT http://127.0.0.1:3000/todos/$ID   -H 'Content-Type: application/json'   -d '{"status":"done"}' | jq

# Delete
curl -i -sS -X DELETE http://127.0.0.1:3000/todos/$ID
```

Stop the local API with `Ctrl+C` when done. To stop DynamoDB Local:
```bash
docker compose down
```

---

## 5) Deploy to AWS with SAM (Cloud)
> Make sure your AWS CLI credentials are set (`aws configure`).

```bash
# Clean build
sam build

# First-time guided deploy (creates a parameters file for next time)
sam deploy --guided
```

During the guided deploy, you’ll choose:
- Stack Name (e.g., `sam-todo-stack`)
- AWS Region (e.g., `ca-central-1` or `us-east-1`)
- Confirm creation of IAM roles
- Save arguments to a config file (recommended)

After deploy, SAM prints stack **Outputs** including the `ApiUrl`. Test it:
```bash
API_URL="https://xxxxxx.execute-api.<region>.amazonaws.com/v1"

curl -sS -X POST "$API_URL/todos"   -H 'Content-Type: application/json'   -d '{"title":"Cloud Todo","description":"deployed via SAM"}' | jq
```

### Update & Redeploy
```bash
sam build && sam deploy
```

### Delete the Stack
```bash
aws cloudformation delete-stack --stack-name sam-todo-stack
```

---

## 6) Deploy to AWS with **CDK Adapter** (Optional)
This repo includes a **CDK** stack that mirrors the SAM stack. Useful if you prefer CDK or want to evolve the architecture.

### Install & Build
```bash
cd cdk
npm install
npm run build
```

### Synthesize & Deploy
```bash
npx cdk synth
npx cdk deploy
```

After a successful deploy, the CDK prints outputs including `ApiUrl`. Use it the same way as the SAM URL.

### Destroy
```bash
npx cdk destroy
```

---

## 7) Environment Variables & Config
- **Local mode**: set `TABLE_NAME=local-todos`, `DDB_ENDPOINT=http://localhost:8000` (or `http://host.docker.internal:8000` when invoked via SAM’s Docker runtime on macOS/Windows).
- **Cloud mode**: do **not** set `DDB_ENDPOINT`. The Lambda will use DynamoDB in the target AWS Region, and the table name is provided by the stack.

---

## 8) Troubleshooting
- **DynamoDB Local not reachable**: Ensure Docker is running; try `curl http://localhost:8000/shell/` (DDB Local UI) if enabled.
- **SAM can’t reach DDB Local on macOS/Windows**: Use `host.docker.internal` instead of `localhost` in `env.json`.
- **Missing dependencies**: Ensure you installed Python deps into `src/` **before** `sam build`.
- **AccessDenied on cloud**: The SAM template grants CRUD policy to the Lambda for the table; re‑deploy if you changed resource names.
- **CORS issues**: CORS is enabled for `'*'` (demo). Tighten in production.

---

## 9) Cost & Cleanup
- Local runs via Docker are free.
- In AWS, resources are in pay‑as‑you‑go tiers (DynamoDB PAY_PER_REQUEST, Lambda, API Gateway). Costs are typically low for test stacks.
- **Cleanup**: Run `aws cloudformation delete-stack --stack-name <name>` (SAM) or `npx cdk destroy` (CDK).

---

## 10) What’s Next
- Add Cognito JWT authorizer for protected routes.
- Add request validation and schema checks.
- Add pagination & GSI queries by `status`.
- Add CloudWatch dashboards and Powertools.
- Add a frontend (React/Next.js/Expo) that calls this API.

Happy building! 🚀
