resource "aws_cognito_user_pool" "this" {
  name                     = "${var.app_prefix}-${var.env}-users"
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  # Collect first name during sign-up (shown in hosted UI as it is required)
  schema {
    name                     = "given_name"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    string_attribute_constraints {
      min_length = 1
      max_length = 100
    }
  }

  # Family name is optional — not shown in hosted UI but storable via API
  schema {
    name                     = "family_name"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    string_attribute_constraints {
      min_length = 0
      max_length = 100
    }
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "${var.app_prefix}-${var.env}-web-client"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = var.callback_urls
  logout_urls                          = var.logout_urls

  # Expose name attributes in the id_token (profile scope covers these,
  # but explicit read_attributes ensures they are always included)
  read_attributes  = ["email", "given_name", "family_name"]
  write_attributes = ["email", "given_name", "family_name"]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
