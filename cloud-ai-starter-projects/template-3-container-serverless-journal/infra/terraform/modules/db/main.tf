resource "aws_dynamodb_table" "this" {
  name         = "${var.app_prefix}-${var.env}-journal"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    enabled        = true
    attribute_name = "ttl"
  }
}
