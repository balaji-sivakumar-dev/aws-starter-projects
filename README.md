# AWS Starter Projects

Curated AWS Infrastructure-as-Code examples that pair **hands-on application code** with **SAM or CDK** stacks. Each subfolder is a self-contained project you can run locally, inspect, and adapt for your workloads.

## How to Use This Repo
- Pick an example folder and follow its `README.md` for a high-level tour.
- Use the companion `Setup.md` (when present) for step-by-step local and cloud deployment instructions.
- Copy/paste or import only the pieces you need into your own project.

## Examples

| Project | Stack | Highlights |
| --- | --- | --- |
| [`aws-sam-gateway-lambda-dynamodb`](aws-sam-gateway-lambda-dynamodb/README.md) | AWS SAM (Python) with optional CDK adapter (TypeScript) | Local-first Todo API using API Gateway + Lambda + DynamoDB, Dockerized DynamoDB Local, seeded sample data, and a matching CDK stack for future deployments. See the [Setup guide](aws-sam-gateway-lambda-dynamodb/Setup.md) for instructions. |


