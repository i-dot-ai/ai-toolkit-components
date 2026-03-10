variable "region" {
  type        = string
  description = "AWS region"
  default     = "eu-west-2"
}

variable "state_bucket" {
  type        = string
  description = "S3 bucket for Terraform state"
}

variable "account_id" {
  type        = string
  description = "AWS account ID"
  sensitive   = true
}

variable "env" {
  type        = string
  description = "Environment name"
  default     = "dev"
}

variable "project_name" {
  type        = string
  description = "Project name"
  default     = "ai-toolkit"
}

variable "team_name" {
  type        = string
  description = "Team name"
}

variable "qdrant_url" {
  type        = string
  description = "URL of the Qdrant instance (e.g. https://qdrant.example.com:6333)"
}

variable "qdrant_api_key" {
  type        = string
  description = "API key for Qdrant (leave empty if not required)"
  sensitive   = true
  default     = ""
}

variable "github_org" {
  type    = string
  default = "github.com/i-dot-ai/"
}

variable "repository_name" {
  type    = string
  default = "ai-toolkit-components"
}

variable "deployed_via" {
  type    = string
  default = "GitHub_Actions"
}
