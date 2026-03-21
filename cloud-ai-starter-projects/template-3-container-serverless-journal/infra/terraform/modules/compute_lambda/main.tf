# Read Groq API key from SSM at apply time (SecureString, never stored in tfvars).
# Store it first with: scripts/setup/step-2b-store-secrets.sh
data "aws_ssm_parameter" "groq_key" {
  count           = var.llm_provider == "groq" ? 1 : 0
  name            = "/journal/${var.env}/groq_api_key"
  with_decryption = true
}

data "archive_file" "zip" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/api.zip"
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.app_prefix}-${var.env}-lambda-api-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "inline" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:BatchWriteItem"]
    resources = [var.journal_table_arn]
  }

  statement {
    actions   = ["states:StartExecution"]
    resources = [var.workflow_arn]
  }

  statement {
    actions   = ["ssm:GetParameter"]
    resources = ["arn:aws:ssm:*:*:parameter/journal/${var.env}/*"]
  }

  # RAG: Bedrock Titan embeddings + LLM inference
  # Access is IAM-controlled; no public endpoint exposed.
  statement {
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
      "arn:aws:bedrock:*::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

resource "aws_iam_role_policy" "inline" {
  name   = "${var.app_prefix}-${var.env}-lambda-api-inline"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.inline.json
}

resource "aws_lambda_function" "this" {
  function_name = "${var.app_prefix}-${var.env}-lambda-api"
  role          = aws_iam_role.this.arn
  handler       = var.handler
  runtime       = var.runtime
  filename      = data.archive_file.zip.output_path
  timeout       = 30
  memory_size   = 256

  source_code_hash = data.archive_file.zip.output_base64sha256

  environment {
    variables = {
      JOURNAL_TABLE_NAME  = var.journal_table_name
      WORKFLOW_ARN        = var.workflow_arn
      AI_ENABLED          = var.ai_enabled
      ADMIN_EMAILS        = var.admin_emails
      # ── LLM provider: "bedrock" (default, no key needed) or "openai" ──────
      LLM_PROVIDER        = var.llm_provider
      BEDROCK_MODEL_ID    = var.bedrock_model_id
      OPENAI_LLM_MODEL    = var.openai_llm_model
      # ── Embedding provider: "bedrock" (default) or "openai" ──────────────
      EMBEDDING_PROVIDER  = var.embedding_provider
      OPENAI_EMBED_MODEL  = var.openai_embed_model
      # OPENAI_API_KEY injected from SSM via separate aws_ssm_parameter lookup
      OPENAI_API_KEY      = var.openai_api_key
      # ── Groq (key fetched from SSM at apply time) ─────────────────────────
      GROQ_API_KEY        = var.llm_provider == "groq" ? data.aws_ssm_parameter.groq_key[0].value : ""
      GROQ_MODEL_ID       = var.groq_model_id
      # ── Bedrock cross-region (Titan Embeddings not available in all regions) ─
      BEDROCK_REGION      = var.bedrock_region
      # ── Vector store: "dynamodb" (default, serverless) or "chroma" (local) ─
      VECTOR_STORE        = var.vector_store
    }
  }
}
