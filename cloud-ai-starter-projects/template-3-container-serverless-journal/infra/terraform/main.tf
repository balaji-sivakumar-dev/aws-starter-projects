locals {
  name_prefix            = "${var.app_prefix}-${var.env}"
  cognito_domain_prefix  = var.cognito_domain_prefix != "" ? var.cognito_domain_prefix : "${var.app_prefix}-${var.env}"

  use_lambda_api         = var.compute_mode == "serverless" || var.compute_mode == "hybrid"
  use_container_api      = var.compute_mode == "container" || var.compute_mode == "hybrid"

  api_routes = {
    health = { route_key = "GET /health", authorization = "NONE" }
    me = { route_key = "GET /me", authorization = "JWT" }
    list_entries = { route_key = "GET /entries", authorization = "JWT" }
    create_entry = { route_key = "POST /entries", authorization = "JWT" }
    get_entry = { route_key = "GET /entries/{entryId}", authorization = "JWT" }
    update_entry = { route_key = "PUT /entries/{entryId}", authorization = "JWT" }
    delete_entry = { route_key = "DELETE /entries/{entryId}", authorization = "JWT" }
    enqueue_ai = { route_key = "POST /entries/{entryId}/ai", authorization = "JWT" }
  }

  # Hybrid mode keeps contract stable by splitting ownership of routes.
  # Lambda handles core CRUD and container handles AI enqueue endpoint.
  lambda_route_keys = (var.compute_mode == "hybrid"
    ? toset(["health", "me", "list_entries", "create_entry", "get_entry", "update_entry", "delete_entry"])
    : (var.compute_mode == "serverless" ? toset(keys(local.api_routes)) : toset([])))

  container_route_keys = (var.compute_mode == "hybrid"
    ? toset(["enqueue_ai"])
    : (var.compute_mode == "container" ? toset(keys(local.api_routes)) : toset([])))
}

module "auth" {
  source = "./modules/auth"

  app_prefix    = var.app_prefix
  env           = var.env
  domain_prefix = local.cognito_domain_prefix
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls
}

module "db" {
  source = "./modules/db"

  app_prefix = var.app_prefix
  env        = var.env
}

module "compute_lambda" {
  source = "./modules/compute_lambda"
  count  = local.use_lambda_api ? 1 : 0

  app_prefix        = var.app_prefix
  env               = var.env
  source_dir        = "${path.module}/../../services/lambda_api/src"
  handler           = "handler.handler"
  runtime           = "python3.13"
  journal_table_arn = module.db.table_arn
  journal_table_name = module.db.table_name
  workflow_arn      = module.workflow.state_machine_arn
}

module "ai_gateway" {
  source = "./modules/ai_gateway"

  app_prefix        = var.app_prefix
  env               = var.env
  source_dir        = "${path.module}/../../services/workflows/src"
  handler           = "ai_gateway.handler"
  runtime           = "python3.13"
  journal_table_arn = module.db.table_arn
  journal_table_name = module.db.table_name
  bedrock_model_id  = var.bedrock_model_id
}

module "workflow" {
  source = "./modules/workflow"

  app_prefix = var.app_prefix
  env        = var.env

  definition_path = "${path.module}/../../services/workflows/statemachine/process_entry_ai.asl.json"
  definition_substitutions = {
    ai_gateway_lambda_arn = module.ai_gateway.lambda_arn
  }
  ai_gateway_lambda_arn = module.ai_gateway.lambda_arn
}

module "compute_container" {
  source = "./modules/compute_container"
  count  = local.use_container_api ? 1 : 0

  app_prefix          = var.app_prefix
  env                 = var.env
  image_uri           = var.container_image_uri
  container_port      = var.container_port
  journal_table_name  = module.db.table_name
  workflow_arn        = module.workflow.state_machine_arn
  cognito_issuer      = "https://cognito-idp.${var.aws_region}.amazonaws.com/${module.auth.user_pool_id}"
  cognito_client_id   = module.auth.user_pool_client_id
}

module "api_edge" {
  source = "./modules/api_edge"

  app_prefix           = var.app_prefix
  env                  = var.env
  jwt_issuer           = "https://cognito-idp.${var.aws_region}.amazonaws.com/${module.auth.user_pool_id}"
  jwt_audience         = [module.auth.user_pool_client_id]
  cors_allow_origins   = var.cors_allow_origins

  lambda_routes = local.use_lambda_api ? {
    for key, route in local.api_routes : key => {
      route_key         = route.route_key
      authorization     = route.authorization
      lambda_arn        = module.compute_lambda[0].function_arn
      lambda_invoke_arn = module.compute_lambda[0].function_invoke_arn
    }
    if contains(local.lambda_route_keys, key)
  } : {}

  container_routes = local.use_container_api ? {
    for key, route in local.api_routes : key => {
      route_key      = route.route_key
      authorization  = route.authorization
      integration_uri = module.compute_container[0].service_url
    }
    if contains(local.container_route_keys, key)
  } : {}
}

module "web_hosting" {
  source = "./modules/web_hosting"

  app_prefix        = var.app_prefix
  env               = var.env
  enable_cloudfront = var.web_enable_cloudfront
}
