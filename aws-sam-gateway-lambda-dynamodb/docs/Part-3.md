---
title: "🏗️ Part 2 — Running a Serverless API Locally with AWS SAM"
published: false
tags: aws, serverless, sam, dynamodb
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png
description: "Local-first backend development with AWS SAM, Lambda, and DynamoDB Local."
---

# 📘 Serverless TODO App — Article Series
- **Part 1 — Architecture Overview**  
  🔗 [PART1](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m)
- **Part 2 — Local Backend with AWS SAM (This Article)**  
  🔗 [PART2](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m)

- **Part 3 — Deploying the Backend to AWS (SAM + CDK)**  
  🔗 In progress...

---

# 🏗️ Part 2 — Running a Serverless API Locally with AWS SAM  
### (API Gateway + Lambda + DynamoDB Local)

This article is the **local development chapter** of the Serverless TODO App series.  
Here, we focus on running the backend **100% locally**, using:

- AWS SAM  
- Lambda emulation in Docker  
- DynamoDB Local  
- Seed scripts  
- Local testing workflows  

**Cloud deployment will be covered in Part 3.**

🔗 **GitHub Repo (Source Code)**  
https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# 🎯 What This Part Covers

- Backend architecture and motivations  
- Explaining Lambda, routing, validation, and data layer  
- How AWS SAM fully emulates Lambda + API Gateway locally  
- Using DynamoDB Local for fast development  
- Local debugging and testing  
- Preparing for AWS deployment (next part)

---

# 🧭 Motivation — Why Local First?

Cloud deployment is powerful, but cloud iteration is slow.

Local-first development means you can:

- Iterate instantly  
- Avoid AWS costs  
- Work offline  
- Debug faster  
- Prepare for cloud deployment confidently  

This project lets you experience *real Lambda + API Gateway* behavior locally using SAM.

---

# 🏗️ Architecture Overview

```
[Local API Gateway (SAM)]
         |
         |
   [Lambda Container]
         |
         |
[DynamoDB Local (Docker)]
```

Components:

| Component | Purpose |
|----------|---------|
| SAM | Emulates API Gateway and Lambda locally |
| Lambda (Python) | Backend logic |
| DynamoDB Local | Local NoSQL storage |
| Docker | Runs Lambda + DynamoDB containers |

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

Includes details on:

- Routing logic  
- Pydantic validation  
- DynamoDB Local connection via environment variables  
- How SAM template wires API + Lambda + Env  

---

# 🏃‍♂️ Running the Backend Locally

Includes instructions for:

- Starting DynamoDB Local  
- Seeding test data  
- Building the SAM app  
- Running `sam local start-api`  
- Testing with curl  

---

# 📚 Additional Resources

GitHub Repo:  
👉 https://github.com/balaji-sivakumar-dev/aws-starter-projects/tree/main/aws-sam-gateway-lambda-dynamodb

---

# ⏭️ Next Steps — Part 3

Continue with:  
**🌐 Part 3 — Deploying the Serverless API to AWS with SAM & CDK**  
🔗 In progress...

