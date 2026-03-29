# Step 1 — AWS CLI Configure (one-time per machine / profile)

## 1) Verify AWS CLI is installed

```bash
aws --version
# Expected: aws-cli/2.x.x ...
```

## 2) Configure a named profile (recommended)

```bash
aws configure --profile {{APP_PREFIX}}-dev
```

Suggested values:

| Prompt | Value |
|--------|-------|
| AWS Access Key ID | your IAM user or SSO access key |
| AWS Secret Access Key | your secret |
| Default region name | `us-east-1` (or your preferred region) |
| Default output format | `json` |

> Use an IAM user / role with sufficient permissions:
> `AmazonDynamoDBFullAccess`, `AmazonECR_FullAccess`, `AWSAppRunnerFullAccess`,
> `AWSLambda_FullAccess`, `AmazonS3FullAccess`, `AmazonCognitoPowerUser`,
> `IAMFullAccess`, `CloudFrontFullAccess`, `AmazonAPIGatewayAdministrator`,
> `AWSStepFunctionsFullAccess`.

## 3) Verify the profile

```bash
aws sts get-caller-identity --profile {{APP_PREFIX}}-dev
aws configure list --profile {{APP_PREFIX}}-dev
```

## 4) Export the profile for the session (optional — avoids repeating `--profile`)

```bash
export AWS_PROFILE={{APP_PREFIX}}-dev

# All subsequent AWS CLI commands use this profile automatically
aws sts get-caller-identity
```

Add the export to your shell profile (`~/.zshrc` or `~/.bashrc`) to make it permanent.
