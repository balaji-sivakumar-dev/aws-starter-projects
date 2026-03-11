output "functions" {
  value = {
    for key, fn in aws_lambda_function.this : key => {
      arn        = fn.arn
      invoke_arn = fn.invoke_arn
      name       = fn.function_name
    }
  }
}
