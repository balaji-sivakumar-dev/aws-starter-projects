data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "archive_file" "function_zip" {
  for_each = var.functions

  type        = "zip"
  source_dir  = each.value.source_dir
  output_path = "${path.module}/.build/${each.key}.zip"
}

resource "aws_iam_role" "this" {
  for_each = var.functions

  name               = "${var.app_prefix}-${var.env}-${each.key}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  for_each = var.functions

  role       = aws_iam_role.this[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "inline" {
  for_each = {
    for key, fn in var.functions : key => fn
    if length(fn.policy_statements) > 0
  }

  dynamic "statement" {
    for_each = each.value.policy_statements
    content {
      sid       = try(statement.value.sid, null)
      effect    = try(statement.value.effect, "Allow")
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

resource "aws_iam_role_policy" "inline" {
  for_each = data.aws_iam_policy_document.inline

  name   = "${var.app_prefix}-${var.env}-${each.key}-inline"
  role   = aws_iam_role.this[each.key].id
  policy = each.value.json
}

resource "aws_cloudwatch_log_group" "this" {
  for_each = var.functions

  name              = "/aws/lambda/${var.app_prefix}-${var.env}-${each.key}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "this" {
  for_each = var.functions

  function_name = "${var.app_prefix}-${var.env}-${each.key}"
  role          = aws_iam_role.this[each.key].arn
  handler       = each.value.handler
  runtime       = each.value.runtime
  filename      = data.archive_file.function_zip[each.key].output_path
  timeout       = each.value.timeout
  memory_size   = each.value.memory_size

  source_code_hash = data.archive_file.function_zip[each.key].output_base64sha256

  environment {
    variables = each.value.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy_attachment.basic_execution
  ]
}
