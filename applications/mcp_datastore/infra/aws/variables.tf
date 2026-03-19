variable "env" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "domain_name" {
  description = "Base domain name. The MCP server will be accessible at mcp.<domain_name>."
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for the domain, used for ACM DNS validation."
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy across all services."
  type        = string
  default     = "latest"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications. Leave empty to skip subscription."
  type        = string
  default     = ""
}

variable "ip_whitelist" {
  description = "IP CIDRs permitted to reach the load balancer. Null allows public access."
  type        = list(string)
  default     = null
}
