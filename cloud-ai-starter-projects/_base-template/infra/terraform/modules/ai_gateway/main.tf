# Read Groq API key from SSM at apply time (SecureString, never stored in tfvars).
# Store it first with: scripts/setup/step-2b-store-secrets.sh
data "aws_ssm_parameter" "groq_key" {
  count           = var.llm_provider == "groq" ? 1 : 0
  name            = "/${var.app_prefix}/${var.env}/groq_api_key"
  with_decryption = true
}

data "archive_file" "zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/ai-gateway.zip"
}

resource "aws_iam_role" "this" {
  name = "${var.app_prefix}-${var.env}-ai-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "inline" {
  name = "${var.app_prefix}-${var.env}-ai-gateway-inline"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"]
        Resource = [
          var.app_table_arn,
          "${var.app_table_arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = ["*"]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter"]
        Resource = ["arn:aws:ssm:*:*:parameter/${var.app_prefix}/${var.env}/*"]
      }
    ]
  })
}

resource "aws_lambda_function" "this" {
  function_name = "${var.app_prefix}-${var.env}-ai-gateway"
  role          = aws_iam_role.this.arn
  handler       = var.handler
  runtime       = var.runtime
  filename      = data.archive_file.zip.output_path
  timeout       = 30
  memory_size   = 256

  source_code_hash = data.archive_file.zip.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.app_table_name
      LLM_PROVIDER       = var.llm_provider
      GROQ_API_KEY       = var.llm_provider == "groq" ? data.aws_ssm_parameter.groq_key[0].value : ""
      GROQ_MODEL_ID      = var.groq_model_id
      BEDROCK_MODEL_ID   = var.bedrock_model_id
      BEDROCK_REGION     = var.bedrock_region
      MAX_INPUT_CHARS    = "8000"
      MAX_OUTPUT_TOKENS  = "256"
      MAX_SUMMARY_TOKENS = "512"
    }
  }
}
