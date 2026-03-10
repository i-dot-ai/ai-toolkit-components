terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.5"
    }
  }

  required_version = ">= 1.2.2"

  backend "s3" {
    key = "ai-toolkit-components/infra/terraform.tfstate"
  }
}

provider "aws" {
  default_tags {
    tags = {
      "platform:repository"    = "${var.github_org}${var.repository_name}"
      "platform:environment"   = terraform.workspace
      "platform:deployed-via"  = var.deployed_via
    }
  }
}
