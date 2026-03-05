data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  bucket_name    = "${var.app_prefix}-${var.env}-web-${data.aws_region.current.name}-${data.aws_caller_identity.current.account_id}"
  website_domain = "${local.bucket_name}.s3-website-${data.aws_region.current.name}.amazonaws.com"
}

resource "aws_s3_bucket" "this" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = var.enable_cloudfront
  block_public_policy     = var.enable_cloudfront
  ignore_public_acls      = var.enable_cloudfront
  restrict_public_buckets = var.enable_cloudfront
}

resource "aws_s3_bucket_website_configuration" "this" {
  count  = var.enable_cloudfront ? 0 : 1
  bucket = aws_s3_bucket.this.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_policy" "public_read" {
  count  = var.enable_cloudfront ? 0 : 1
  bucket = aws_s3_bucket.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject"]
        Resource  = "${aws_s3_bucket.this.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.this]
}

resource "aws_cloudfront_origin_access_control" "this" {
  count = var.enable_cloudfront ? 1 : 0

  name                              = "${local.bucket_name}-oac"
  description                       = "OAC for ${local.bucket_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "this" {
  count = var.enable_cloudfront ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.this.bucket_regional_domain_name
    origin_id                = "s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.this[0].id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "s3-origin"

    forwarded_values {
      query_string = true

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }
}

data "aws_iam_policy_document" "cloudfront_oac" {
  count = var.enable_cloudfront ? 1 : 0

  statement {
    sid     = "AllowCloudFrontServiceRead"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.this.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.this[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "cloudfront_oac" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.cloudfront_oac[0].json
}
