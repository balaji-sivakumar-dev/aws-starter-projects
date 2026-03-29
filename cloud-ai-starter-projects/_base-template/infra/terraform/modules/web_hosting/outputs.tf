output "bucket_name" { value = aws_s3_bucket.this.bucket }
output "site_url" {
  value = "https://${aws_cloudfront_distribution.this.domain_name}"
}
output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.this.id
}
