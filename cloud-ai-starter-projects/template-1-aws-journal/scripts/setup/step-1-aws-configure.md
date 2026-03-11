# Step 1 — AWS CLI Configure (One-time per machine/profile)

## 1) Verify AWS CLI
```bash
aws --version

## 2) Configure a named profile (recommended)
aws configure --profile journal-dev

```
Suggested values:
Region: ca-central-1
Output: json
```

## 3) Verify the profile
```bash
aws sts get-caller-identity --profile journal-dev
aws configure list --profile journal-dev
```

## 4) Use the profile in your shell (optional)
```bash
export AWS_PROFILE=journal-dev

# Now all AWS CLI commands use this profile automatically
aws sts get-caller-identity
```
