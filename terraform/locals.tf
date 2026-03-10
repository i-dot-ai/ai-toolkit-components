locals {
  name          = "${var.team_name}-${var.env}-${var.project_name}"
  is_production = terraform.workspace == "prod"
}
