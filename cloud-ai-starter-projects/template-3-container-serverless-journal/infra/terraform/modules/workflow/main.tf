resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/states/${var.app_prefix}-${var.env}-process-entry-ai"
  retention_in_days = 14
}

resource "aws_iam_role" "states" {
  name = "${var.app_prefix}-${var.env}-states-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "states_invoke" {
  name = "${var.app_prefix}-${var.env}-states-invoke"
  role = aws_iam_role.states.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [var.ai_gateway_lambda_arn]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "this" {
  name     = "${var.app_prefix}-${var.env}-process-entry-ai"
  role_arn = aws_iam_role.states.arn

  definition = templatefile(var.definition_path, var.definition_substitutions)

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.this.arn}:*"
  }
}
