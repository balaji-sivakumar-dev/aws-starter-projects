# AI gateway kept as separate runtime module to allow lambda/container swaps later.
resource "aws_iam_role" "placeholder" {
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
