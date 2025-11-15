---
title: "🌐 Part 3 — Deploying the Serverless API to AWS with SAM & CDK (and Cost Watchouts)"
published: false
tags: aws, serverless, sam, cdk, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "From local SAM emulation to real AWS deployment with SAM and CDK, plus free tier and cost considerations."
---

# 🌐 Part 3 — Deploying the Serverless API to AWS with SAM & CDK  
### (Credentials, S3 Packaging, API Gateway, Costs)

In **Part 2**, we focused entirely on running the Todo API **locally** using:

- AWS SAM (`sam local start-api`)  
- Lambda emulation in Docker  
- DynamoDB Local + seed scripts  

In this **Part 3**, we’ll take the same backend and deploy it to **real AWS**, using both:

- **AWS SAM** (CloudFormation-based)  
- **AWS CDK** (TypeScript-based IaC)  

We’ll also talk about **free tier vs always-free**, and what to watch out for when deploying.

🔗 **GitHub Repo (Source Code for Backend)**  
https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# 🎯 What This Part Covers

- How SAM and CDK package Lambda code and upload to S3  
- How to deploy the backend to AWS using **SAM**  
- How to deploy the same code using **CDK**  
- Where AWS free tier applies (and where it doesn’t)  
- How to set up cost guardrails (AWS Budgets)  

> ⚠️ **Prerequisite:** You should have Part 2 running locally before attempting this. This ensures the code works before touching AWS resources.

---

# ☁️ Deploying to AWS (Using SAM)

Once you’ve verified the API locally, you can deploy the same stack to AWS.

```bash
sam build
sam deploy --guided
```

During the first `sam deploy --guided`, SAM will:

- Ask for a **stack name**  
- Ask which AWS **region** to deploy to  
- Create or reuse an **S3 bucket** for artifacts  
- Save your answers to `samconfig.toml`  

After deployment, SAM will print out:

- The **API Gateway URL** for your `/todos` endpoints  
- The **stack name** you can use for cleanup

### What SAM does behind the scenes

- Packages your Lambda code  
- Uploads it to **S3**  
- Generates/uses a CloudFormation template  
- Creates:
  - Lambda function  
  - DynamoDB table  
  - API Gateway  
  - IAM roles & permissions  

Future redeploys are as simple as:

```bash
sam build
sam deploy
```

### Cleaning up the stack

When you are done:

```bash
aws cloudformation delete-stack --stack-name <your-stack-name>
```

This avoids ongoing costs from provisioned resources.

---

# 🧰 Deploying Using CDK (Same Codebase, Zero Changes)

If you prefer working with TypeScript and high-level constructs, the `cdk/` folder mirrors what SAM deploys.

Inside:

- `cdk/lib/todo-stack.ts` defines:
  - DynamoDB table  
  - Lambda function (pointing at `src/`)  
  - HTTP API or API Gateway routes  

### CDK Commands

From the `cdk` folder:

```bash
cd cdk
npm install
npm run build
npx cdk synth
npx cdk deploy
```

- `cdk synth` → shows the generated CloudFormation template  
- `cdk deploy` → creates/updates resources in your AWS account  

To destroy:

```bash
npx cdk destroy
```

> 🧠 **Key takeaway:** Your **Lambda code in `src/` never changes**. Only the IaC wrapper changes (SAM template vs CDK stack). This keeps your business logic decoupled from deployment tooling.

---

# ⚠️ Important Watchouts — AWS Free Tier & Cost Notes

Although this project is designed to stay *within free-tier limits*, there are some important cost considerations to be aware of.

AWS has a mix of:

- **12-month free tier** (for new accounts)  
- **Always-free** services/quotas  

Understanding which is which matters once you start deploying.

---

## 1️⃣ S3 Upload Costs (SAM / CDK Deployments)

Both **SAM** and **CDK** upload your Lambda package to an S3 bucket.  
S3 is **not always free** unless you are in your first 12 months on AWS.

- S3 storage: may incur small charges after the initial free tier (5GB for 12 months only)  
- S3 PUT requests: may incur costs depending on number of deployments  

> ⚠️ *If you deploy frequently, keep an eye on your S3 usage.*

---

## 2️⃣ API Gateway Free Tier Is NOT “Always Free”

Amazon API Gateway offers (as of writing):

- **1M REST API calls/month — only for the first 12 months** for new accounts  

After that period, you will incur charges per million requests.

If your API is largely idle, cost will be near zero — but it is **not guaranteed to be always free**.

---

## 3️⃣ DynamoDB Has an Always-Free Tier (Up to Limits)

DynamoDB provides an *always-free* tier:

- 25GB of storage  
- A limited amount of read/write capacity per month  

This is more than enough for:

- Hobby projects  
- Small personal apps  
- Low-traffic prototypes  

Just make sure:

- You use **on-demand** mode (good default for unpredictable/low traffic)  
- You monitor usage if your app starts to grow

---

## 4️⃣ Lambda Has an Always-Free Tier

AWS Lambda offers:

- **1M free requests/month** (always-free)  
- **400,000 GB-seconds of compute/month**  

Most personal projects never exceed these limits.

---

## 5️⃣ CloudFormation / CDK / SAM Themselves Are Free

The orchestration tools (CloudFormation, CDK, SAM) are free.  
Costs come only from the resources they create:

- S3  
- Lambda  
- DynamoDB  
- API Gateway  
- CloudWatch Logs  

---

## ✔️ Recommended Cost Guardrail: AWS Budget Alert

Set up an AWS **Budget Alert** (also free):

- Go to **Billing → Budgets** in the AWS Console  
- Create a **Cost budget** (e.g., `$1` or `$2` per month)  
- Configure **email alerts** to notify you if actual or forecasted spend exceeds the threshold  

This is a great safety net when experimenting with deployments.

---

## 📚 Additional Resources

### 🔗 GitHub Repository (Full Source Code)
All code for this backend (SAM, CDK, Lambda, DynamoDB) is available here:

👉 **https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb**

---

# 👀 Coming Up in Part 4 — UI + Cognito Authentication

In **Part 4**, we’ll finally connect a frontend and authentication to this backend:

- React + Vite frontend  
- AWS Cognito Hosted UI  
- Persisting user sessions with JWTs  
- Making authenticated calls from the browser to API Gateway  
- Deploying the UI to Vercel (or AWS Amplify)  

This will complete the full-stack, serverless TODO application. 🚀
