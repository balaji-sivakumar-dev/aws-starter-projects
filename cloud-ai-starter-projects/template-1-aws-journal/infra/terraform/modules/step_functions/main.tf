data "aws_iam_policy_document" "assume_states" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.app_prefix}-${var.env}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.assume_states.json
}

data "aws_iam_policy_document" "this" {
  statement {
    sid = "InvokeWorkflowLambdas"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = var.lambda_invoke_arns
  }
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.app_prefix}-${var.env}-sfn-policy"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.this.json
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/states/${var.app_prefix}-${var.env}-process-entry-ai"
  retention_in_days = 14
}

resource "aws_sfn_state_machine" "this" {
  name     = "${var.app_prefix}-${var.env}-process-entry-ai"
  role_arn = aws_iam_role.this.arn

  definition = templatefile(var.definition_path, var.definition_substitutions)

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.this.arn}:*"
  }
}
