locals {
  all_routes = merge(
    { for key, route in var.lambda_routes : "lambda-${key}" => merge(route, { kind = "lambda" }) },
    { for key, route in var.container_routes : "container-${key}" => merge(route, { kind = "container" }) }
  )
}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.app_prefix}-${var.env}-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "${var.app_prefix}-${var.env}-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = var.jwt_audience
    issuer   = var.jwt_issuer
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  for_each = {
    for key, route in local.all_routes : key => route
    if route.kind == "lambda"
  }

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "container" {
  for_each = {
    for key, route in local.all_routes : key => route
    if route.kind == "container"
  }

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = each.value.integration_uri
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "this" {
  for_each = local.all_routes

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value.route_key

  target = each.value.kind == "lambda" ? "integrations/${aws_apigatewayv2_integration.lambda[each.key].id}" : "integrations/${aws_apigatewayv2_integration.container[each.key].id}"

  authorization_type = each.value.authorization == "NONE" ? "NONE" : "JWT"
  authorizer_id      = each.value.authorization == "NONE" ? null : aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_lambda_permission" "allow_apigw" {
  for_each = {
    for key, route in local.all_routes : key => route
    if route.kind == "lambda"
  }

  statement_id  = "AllowExecutionFromApiGateway-${replace(each.key, "_", "-")}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
