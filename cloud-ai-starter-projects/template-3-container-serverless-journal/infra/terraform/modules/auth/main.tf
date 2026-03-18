# ── Pre-Signup Lambda (allowlist enforcement) ──────────────────────────────────

data "archive_file" "pre_signup_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/pre_signup.py"
  output_path = "${path.module}/lambda/pre_signup.zip"
}

resource "aws_iam_role" "pre_signup_lambda" {
  name = "${var.app_prefix}-${var.env}-cognito-pre-signup"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "pre_signup_lambda" {
  name = "ssm-read-and-logs"
  role = aws_iam_role.pre_signup_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Read the allowlist from SSM
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = "arn:aws:ssm:*:*:parameter/${var.app_prefix}/${var.env}/cognito/allowed_emails"
      },
      {
        # CloudWatch Logs
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "pre_signup" {
  function_name    = "${var.app_prefix}-${var.env}-cognito-pre-signup"
  role             = aws_iam_role.pre_signup_lambda.arn
  runtime          = "python3.12"
  handler          = "pre_signup.handler"
  filename         = data.archive_file.pre_signup_zip.output_path
  source_code_hash = data.archive_file.pre_signup_zip.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      ALLOWED_EMAILS_SSM_PATH = "/${var.app_prefix}/${var.env}/cognito/allowed_emails"
    }
  }
}

resource "aws_lambda_permission" "cognito_invoke_pre_signup" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_signup.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.this.arn
}

# ── Cognito User Pool ─────────────────────────────────────────────────────────

resource "aws_cognito_user_pool" "this" {
  name                     = "${var.app_prefix}-${var.env}-users"
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  lambda_config {
    pre_sign_up = aws_lambda_function.pre_signup.arn
  }

  # Collect first name during sign-up (shown in hosted UI as it is required)
  schema {
    name                     = "given_name"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    string_attribute_constraints {
      min_length = 1
      max_length = 100
    }
  }

  # Family name is optional — not shown in hosted UI but storable via API
  schema {
    name                     = "family_name"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    string_attribute_constraints {
      min_length = 0
      max_length = 100
    }
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.app_prefix}-${var.env}-web-client"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls

  # Expose name attributes in the id_token (profile scope covers these,
  # but explicit read_attributes ensures they are always included)
  read_attributes  = ["email", "given_name", "family_name"]
  write_attributes = ["email", "given_name", "family_name"]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
