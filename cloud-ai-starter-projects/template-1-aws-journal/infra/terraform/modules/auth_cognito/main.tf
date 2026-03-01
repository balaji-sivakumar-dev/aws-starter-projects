resource "aws_cognito_user_pool" "this" {
  name = "${var.app_prefix}-${var.env}-users"

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.app_prefix}-${var.env}-web-client"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                               = false
  allowed_oauth_flows_user_pool_client          = true
  allowed_oauth_flows                           = ["code"]
  allowed_oauth_scopes                          = ["openid", "email", "profile"]
  supported_identity_providers                  = ["COGNITO"]
  callback_urls                                 = var.callback_urls
  logout_urls                                   = var.logout_urls
  prevent_user_existence_errors                 = "ENABLED"
  explicit_auth_flows                           = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
