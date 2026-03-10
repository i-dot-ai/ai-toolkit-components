module "mcp_server" {
  source      = "./modules/lambda"
  source_name = "mcp_server"

  function_name = "${local.name}-mcp-server"
  handler       = "main.lambda_handler"
  timeout       = 60
  memory_size   = 256

  environment_variables = {
    QDRANT_URL     = var.qdrant_url
    QDRANT_API_KEY = var.qdrant_api_key
    ENVIRONMENT    = terraform.workspace
    REPO           = "ai-toolkit-components"
  }
}

module "data_ingestor" {
  source      = "./modules/lambda"
  source_name = "data_ingestor"

  function_name = "${local.name}-data-ingestor"
  handler       = "main.lambda_handler"
  timeout       = 300  # ingestion can be slow
  memory_size   = 512  # embedding models need more memory

  environment_variables = {
    QDRANT_URL     = var.qdrant_url
    QDRANT_API_KEY = var.qdrant_api_key
    ENVIRONMENT    = terraform.workspace
    REPO           = "ai-toolkit-components"
  }
}
