resource "aws_sfn_state_machine" "placeholder" {
  name     = "${var.app_prefix}-${var.env}-process-entry-ai"
  role_arn = aws_iam_role.states.arn

  definition = jsonencode({
    Comment = "Placeholder workflow"
    StartAt = "NotImplemented"
    States = {
      NotImplemented = {
        Type  = "Fail"
        Error = "NotImplemented"
      }
    }
  })
}

data "aws_iam_policy_document" "assume_states" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "states" {
  name               = "${var.app_prefix}-${var.env}-states-role"
  assume_role_policy = data.aws_iam_policy_document.assume_states.json
}
