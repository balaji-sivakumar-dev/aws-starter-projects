locals {
  use_service = var.image_uri != ""
}

resource "aws_iam_role" "apprunner_access" {
  count = local.use_service ? 1 : 0

  name = "${var.app_prefix}-${var.env}-apprunner-ecr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_access" {
  count = local.use_service ? 1 : 0

  role       = aws_iam_role.apprunner_access[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_service" "this" {
  count = local.use_service ? 1 : 0

  service_name = "${var.app_prefix}-${var.env}-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access[0].arn
    }

    image_repository {
      image_repository_type = "ECR"
      image_identifier      = var.image_uri

      image_configuration {
        port = tostring(var.container_port)
        runtime_environment_variables = {
          TABLE_NAME = var.app_table_name
          WORKFLOW_ARN       = var.workflow_arn
          COGNITO_ISSUER     = var.cognito_issuer
          COGNITO_CLIENT_ID  = var.cognito_client_id
        }
      }
    }

    auto_deployments_enabled = false
  }
}
