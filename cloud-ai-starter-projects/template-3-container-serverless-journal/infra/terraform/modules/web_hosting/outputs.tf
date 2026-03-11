data "aws_region" "current" {}
output "bucket_name" { value = aws_s3_bucket.this.bucket }
output "site_url" {
  value = "http://${aws_s3_bucket.this.bucket}.s3-website-${data.aws_region.current.name}.amazonaws.com"
}
