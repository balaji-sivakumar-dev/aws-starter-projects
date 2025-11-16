---
title: "🌐 Part 3 — Deploying the Serverless API to AWS with SAM & CDK"
published: false
tags: aws, serverless, sam, cdk
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "Deploying the TODO backend to AWS using SAM & CDK, with credential setup and cost watchouts."
---

# 📘 Serverless TODO App — Article Series

- **Part 1 — Architecture Overview**  
  🔗 [PART1](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m)

- **Part 2 — Local Backend with AWS SAM (This Article)**  
  🔗 [PART2](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m)

- **Part 3 — Deploying the Backend to AWS (SAM + CDK)**  
  🔗 In progress...

---

# 🌐 Part 3 — Deploying the Serverless API to AWS  
### (SAM + CDK + AWS Credentials + Costs)

In **Part 2**, you ran the entire backend locally using SAM, Lambda containers, and DynamoDB Local.

In this part, we move to **real AWS deployment**, covering:

- AWS credentials setup  
- S3 packaging behavior  
- SAM deploy workflow  
- CDK deploy workflow  
- Free tier vs Always-Free services  
- Cost watchouts and best practices  

🔗 **GitHub Repo (Source Code)**  
https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# 🎯 What This Part Covers

- Configuring AWS credentials safely  
- How SAM uploads Lambda packages to S3  
- Deploying the backend using SAM  
- Deploying the backend using CDK  
- Understanding AWS free tier  
- Preventing accidental charges (Budgets)

---

# 🔐 Setting Up AWS Credentials

(placeholder — we will refine later)

- AWS SSO  
- AWS CLI configure  
- Builder ID  
- Which method to choose  

---

# ☁️ Deploying with SAM

Steps:

```bash
sam build
sam deploy --guided
```

CloudFormation creates:

- Lambda  
- DynamoDB  
- API Gateway  
- IAM roles  
- CloudWatch Logs  

Cleanup:

```bash
aws cloudformation delete-stack --stack-name <name>
```

---

# 🧰 Deploying with CDK

Commands:

```bash
npm install
npm run build
npx cdk synth
npx cdk deploy
```

Cleanup:

```bash
npx cdk destroy
```

---

# ⚠️ Important Cost Watchouts

- S3 upload costs  
- API Gateway not always free  
- DynamoDB Always-Free limits  
- Lambda Always-Free limits  
- CloudWatch Logs  
- Safe cost guardrails with AWS Budget alerts  

---

# 📚 Additional Resources

GitHub Repo:  
👉 https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# ⏭️ Next Steps — Part 4

**Part 4 — UI + Cognito Authentication**  
🔗 _URL_PLACEHOLDER_PART4_

(Coming soon!)
