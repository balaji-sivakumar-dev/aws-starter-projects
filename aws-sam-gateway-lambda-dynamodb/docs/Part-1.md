---
title: "🚀 Building a Serverless TODO App with AWS + Vercel — My First AWS Project"
published: true
tags: aws, vercel, serverless, beginners
cover_image: https://dev-to-uploads.s3.amazonaws.com/uploads/articles/kjdkh7z4gye6o3c2afwi.png

description: "How I combined AWS Lambda, DynamoDB, Cognito, and Vercel hosting to build a modern full-stack TODO app with zero servers to manage."
---

# 📘 Serverless TODO App — Article Series

| Part | Title | 
|------|--------|
| **1** | [Architecture Overview](https://dev.to/balaji_sivakumar_e7a4b07a/building-a-serverless-todo-app-with-aws-vercel-my-first-aws-project-1h1m) |
| **2** | [Local Backend with AWS SAM *(You are here)*](https://dev.to/balaji_sivakumar_e7a4b07a/part-2-running-a-serverless-api-locally-with-aws-sam-api-gateway-lambda-dynamodb-dob) |
| **3** | Deploying Backend to AWS (SAM + CDK) - *(Coming soon…)* |

---

## 🧰 How I Built a Serverless TODO App with AWS Lambda, DynamoDB & Vercel

I’ve always wanted to build a **real full-stack application** that’s completely **serverless**, scalable, and affordable to host.  
This project marks that milestone — a **simple but powerful TODO App** built with **React + Vite on Vercel** (frontend) and an **AWS backend** powered by **Cognito, Lambda, and DynamoDB**.

---

## 🎯 Motivation

Most of my side projects started as experiments — a script here, a local app there. But I wanted to go one step further and **deploy a working cloud application** that could:

- Scale without managing servers  
- Stay *within free-tier limits* (important for solo devs!)  
- Integrate modern authentication (AWS Cognito)  
- Be fully automated using **Infrastructure as Code** (AWS CDK)

Instead of learning theory from tutorials, I decided to **build something end-to-end** — a small, achievable project that would teach me *how real serverless systems fit together*.

---

## 🧩 What I Built

### **Todo App (Vercel + AWS)**

A lightweight yet production-ready **serverless TODO manager** with:

- ⚛️ **React + Vite** SPA hosted on **Vercel**  
- 🔐 **AWS Cognito Hosted UI** for user authentication (email/password for now, social login ready for later via identity providers)  
- 🧠 **AWS Lambda Function URL** exposing CRUD endpoints (Create, Read, Update, Delete)  
- 💾 **DynamoDB (on-demand mode)** to store tasks per user  
- 🛠 **AWS CDK (TypeScript)** to automate deployment of all backend infrastructure (Cognito, Lambda, DynamoDB, IAM roles, etc.)  
- 🌐 **AWS Amplify JS (Auth module)** integrated with the frontend to handle sign-in and token-based API calls  

Everything is **stateless and serverless**, meaning no EC2, no manual scaling, and no backend servers to patch — ever.

---

## 🏗 Architecture Overview

Here’s the flow:

1. The React app is deployed to **Vercel**.  
2. Users sign in using **Cognito Hosted UI**.  
3. Upon login, the app stores a **JWT token**.  
4. Every API call goes through the **Lambda Function URL**, validated using that token.  
5. The Lambda reads and writes tasks to **DynamoDB**, partitioned by `userId`.

🧠 **Note:** Lambda Function URLs are public by default — the token validation happens *inside* the Lambda to ensure secure access.

It’s clean, secure, and built on services that can scale infinitely.

![AWS serverless architecture diagram](https://dev-to-uploads.s3.amazonaws.com/uploads/articles/dkejpjx2z1dtvadeskeb.png)
---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-------------|
| **Frontend** | React + Vite + AWS Amplify JS (Auth module) |
| **Hosting** | Vercel (free tier) |
| **Auth** | AWS Cognito Hosted UI |
| **API** | AWS Lambda (Function URL) |
| **Database** | DynamoDB (on-demand) |
| **IaC** | AWS CDK (TypeScript) |

---

## 💵 AWS Free Tier — Cost & Scalability

One of my key goals was to **stay within AWS’s always-free tier**, so I could build, test, and learn without worrying about surprise bills.

Here’s how each service fits into the free tier and what kind of traffic it can handle before costs start:

| AWS Service | Free Tier Limit | What It Covers | Practical Impact |
|--------------|----------------|----------------|------------------|
| **AWS Lambda** | 1M requests/month + 400,000 GB-seconds compute/month | All function invocations | Enough for tens of thousands of TODO operations per month. Perfect for hobby apps or small prototypes. |
| **Amazon DynamoDB (On-Demand)** | 25 GB free storage | Automatically scales with traffic | No need to pre-provision read/write capacity — great for unpredictable workloads. |
| **Amazon Cognito** | 50,000 monthly active users (MAUs) free | Authentication and token management | Easily supports most side projects and MVPs without cost. |
| **AWS CDK / CloudFormation** | Free | Infrastructure management and provisioning | No runtime cost — only pays for created resources (still free if resources are within free tier). |
| **Vercel Hosting** | Free plan for hobby projects | Static site hosting and serverless frontend delivery | Perfect for individual or small-team projects. |
| **AWS Amplify Hosting** | 1,000 build minutes/month + 5 GB storage (free for first year only) | Static site hosting on AWS | Would have kept everything inside AWS, but the free tier is limited to the first year. |
| **AWS Budget & Cost Monitor** | Free | Budget alerts and cost tracking | Always set up a budget alert (e.g., $1 threshold) to monitor expenses and avoid surprises. |
| **AWS API Gateway (optional)** | 1M REST API calls/month | Only if used instead of Lambda URL | Useful for advanced routing or throttling setups later. |

🧠 **Tip:** All of these services automatically scale down when idle, meaning you only pay when your app is being used — ideal for experimentation and side projects.

---

## 💡 Lessons Learned

- **CDK is game-changing** — writing infrastructure in TypeScript feels natural once you get used to it.  
- **Vercel + AWS work beautifully together** — frontend on Vercel, backend on AWS, no friction.  
- **JWT validation** in Lambda keeps APIs lightweight yet secure.  
- Keeping things **modular** (frontend + backend folders) makes local dev and deployment easy.  
- Always configure **budget alerts early** — they’re free and prevent billing surprises.

---

## 🧭 What’s Next

- Add **Google & GitHub sign-in** via Cognito Identity Providers.  
- Add **real-time updates** using AWS AppSync or WebSockets.  
- Build **automated deployments** using GitHub Actions (with AWS OIDC roles, no static keys).  
- Write detailed follow-ups on each part (Cognito setup, CDK deployment, etc.).

---

## ❤️ Final Thoughts

This project isn’t just a TODO app — it’s a **template for future serverless ideas**.

If you’re someone who’s been reading about AWS and Vercel but never *connected the dots*, this kind of project is the perfect start. It’s small enough to finish, yet rich enough to teach you real-world cloud development.

---

✨ Coming Soon

In my next post, I’ll share a step-by-step guide to set up this project from scratch —  
perfect for beginners who want to clone, deploy, and learn while building along.

Stay tuned! 🚀

Thanks for reading 🙏  
This was my **first post on Dev.to** — more articles coming soon!

---

