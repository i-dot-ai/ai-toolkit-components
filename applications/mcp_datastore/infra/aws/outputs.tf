output "mcp_server_url" {
  description = "HTTPS URL for the MCP server SSE endpoint"
  value       = "https://mcp.${var.domain_name}"
}

output "vector_db_internal_endpoint" {
  description = "Internal DNS endpoint for Qdrant (accessible within the VPC only)"
  value       = "${local.vector_db_host}:6333"
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer — create a CNAME from mcp.<domain_name> to this"
  value       = module.load_balancer.load_balancer_dns_name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs keyed by service name, used for docker push"
  value       = module.ecr.ecr_repository_url
}
