locals {
  name_prefix   = "${var.app_prefix}-${var.env}"
  cognito_domain_prefix = var.cognito_domain_prefix != "" ? var.cognito_domain_prefix : "${var.app_prefix}-${var.env}"

  # Platform layer routes remain stable while domain implementation behind Lambdas can evolve.
  api_routes = {
    health = {
      route_key         = "GET /health"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "NONE"
    }
    me = {
      route_key         = "GET /me"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    list_entries = {
      route_key         = "GET /entries"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    create_entry = {
      route_key         = "POST /entries"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    get_entry = {
      route_key         = "GET /entries/{entryId}"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    update_entry = {
      route_key         = "PUT /entries/{entryId}"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    delete_entry = {
      route_key         = "DELETE /entries/{entryId}"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
    enqueue_ai = {
      route_key         = "POST /entries/{entryId}/ai"
      lambda_arn        = module.lambda_api.functions["api"].arn
      lambda_invoke_arn = module.lambda_api.functions["api"].invoke_arn
      authorization     = "JWT"
    }
  }
}

# Platform layer
module "s3_spa_hosting" {
  source = "./modules/s3_spa_hosting"

  app_prefix        = var.app_prefix
  env               = var.env
  enable_cloudfront = var.web_enable_cloudfront
}

module "auth_cognito" {
  source = "./modules/auth_cognito"

  app_prefix     = var.app_prefix
  env            = var.env
  callback_urls  = var.callback_urls
  logout_urls    = var.logout_urls
  domain_prefix  = local.cognito_domain_prefix
}

module "dynamodb" {
  source = "./modules/dynamodb"

  app_prefix = var.app_prefix
  env        = var.env
}

module "lambda_ai" {
  source = "./modules/lambda"

  app_prefix          = var.app_prefix
  env                 = var.env
  log_retention_days  = var.log_retention_days

  functions = {
    ai_gateway = {
      handler    = "ai_gateway.handler"
      runtime    = "python3.13"
      source_dir = "${path.module}/../../services/workflows/src"
      timeout    = 30
      memory_size = 256
      environment = {
        JOURNAL_TABLE_NAME = module.dynamodb.table_name
        BEDROCK_MODEL_ID   = var.bedrock_model_id
        MAX_INPUT_CHARS    = "8000"
        MAX_OUTPUT_TOKENS  = "256"
        AI_RATE_LIMIT_MAX_REQUESTS = "5"
        AI_RATE_LIMIT_WINDOW_SECONDS = "60"
      }
      policy_statements = [
        {
          sid       = "JournalTableWrite"
          actions   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
          resources = [module.dynamodb.table_arn]
        },
        {
          sid       = "BedrockInvoke"
          actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
          resources = ["*"]
        }
      ]
    }
  }
}

module "step_functions" {
  source = "./modules/step_functions"

  app_prefix          = var.app_prefix
  env                 = var.env
  definition_path     = "${path.module}/../../services/workflows/statemachine/process_entry_ai.asl.json"
  definition_substitutions = {
    ai_gateway_lambda_arn = module.lambda_ai.functions["ai_gateway"].arn
  }
  lambda_invoke_arns  = [module.lambda_ai.functions["ai_gateway"].arn]
}

module "lambda_api" {
  source = "./modules/lambda"

  app_prefix          = var.app_prefix
  env                 = var.env
  log_retention_days  = var.log_retention_days

  functions = {
    api = {
      handler     = "handlers.handler"
      runtime     = "python3.13"
      source_dir  = "${path.module}/../../services/api/src"
      timeout     = 30
      memory_size = 256
      environment = {
        JOURNAL_TABLE_NAME = module.dynamodb.table_name
        WORKFLOW_ARN       = module.step_functions.state_machine_arn
      }
      policy_statements = [
        {
          sid       = "JournalTableAccess"
          actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
          resources = [module.dynamodb.table_arn]
        },
        {
          sid       = "StartWorkflow"
          actions   = ["states:StartExecution"]
          resources = [module.step_functions.state_machine_arn]
        }
      ]
    }
  }
}

module "api_gateway_http" {
  source = "./modules/api_gateway_http"

  app_prefix            = var.app_prefix
  env                   = var.env
  log_retention_days    = var.log_retention_days
  routes                = local.api_routes
  enable_jwt_authorizer = true
  jwt_issuer            = "https://cognito-idp.${var.aws_region}.amazonaws.com/${module.auth_cognito.user_pool_id}"
  jwt_audience          = [module.auth_cognito.user_pool_client_id]
}
