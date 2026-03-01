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
        Action = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = [var.journal_table_arn]
      },
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
        Resource = ["*"]
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
      JOURNAL_TABLE_NAME = var.journal_table_name
      BEDROCK_MODEL_ID   = var.bedrock_model_id
      MAX_INPUT_CHARS    = "8000"
      MAX_OUTPUT_TOKENS  = "256"
    }
  }
}
