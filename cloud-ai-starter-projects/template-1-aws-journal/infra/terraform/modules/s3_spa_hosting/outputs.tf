output "bucket_name" {
  value = aws_s3_bucket.this.bucket
}

output "site_url" {
  value = var.enable_cloudfront ? "https://${aws_cloudfront_distribution.this[0].domain_name}" : "http://${aws_s3_bucket.this.bucket}.s3-website-${data.aws_region.current.name}.amazonaws.com"
}

output "cloudfront_distribution_id" {
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.this[0].id : ""
  description = "CloudFront distribution ID (empty when disabled)"
}
