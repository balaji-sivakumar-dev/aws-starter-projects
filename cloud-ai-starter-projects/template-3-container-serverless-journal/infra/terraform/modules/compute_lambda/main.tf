data "archive_file" "zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/api.zip"
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.app_prefix}-${var.env}-lambda-api-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "inline" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query"]
    resources = [var.journal_table_arn]
  }

  statement {
    actions   = ["states:StartExecution"]
    resources = [var.workflow_arn]
  }
}

resource "aws_iam_role_policy" "inline" {
  name   = "${var.app_prefix}-${var.env}-lambda-api-inline"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.inline.json
}

resource "aws_lambda_function" "this" {
  function_name = "${var.app_prefix}-${var.env}-lambda-api"
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
      WORKFLOW_ARN       = var.workflow_arn
      AI_ENABLED         = var.ai_enabled
    }
  }
}
