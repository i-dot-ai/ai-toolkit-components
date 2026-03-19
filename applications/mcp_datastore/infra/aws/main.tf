locals {
  name              = "${var.env}-mcp-datastore"
  service_namespace = "${var.env}.mcp-datastore.internal"
  vector_db_host    = "vector-db.${local.service_namespace}"
}

data "aws_caller_identity" "current" {}

# ── Alerting ──────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── Networking ────────────────────────────────────────────────────────────────

module "vpc" {
  source = "./modules/infrastructure/vpc"

  name = local.name
  cidr = var.vpc_cidr
}

# ── Container Registry ────────────────────────────────────────────────────────

module "ecr" {
  source = "./modules/infrastructure/ecr"

  repository_names = [
    "vector-db",
    "data-ingestor",
    "mcp-server",
    "vector-query",
  ]
}

# ── TLS Certificate ───────────────────────────────────────────────────────────

module "acm" {
  source = "./modules/infrastructure/acm"

  domain_name    = "mcp.${var.domain_name}"
  hosted_zone_id = var.hosted_zone_id
}

# ── Load Balancer ─────────────────────────────────────────────────────────────

module "load_balancer" {
  source = "./modules/infrastructure/load_balancer"

  name            = local.name
  env             = var.env
  account_id      = data.aws_caller_identity.current.account_id
  vpc_id          = module.vpc.vpc_id
  public_subnets  = module.vpc.public_subnets
  certificate_arn = module.acm.arn
  ip_whitelist    = var.ip_whitelist
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────

module "ecs_cluster" {
  source = "./modules/infrastructure/ecs-cluster"

  name = local.name
}

# ── EFS — persistent storage for Qdrant ──────────────────────────────────────
# EFS is used rather than EBS so Qdrant storage persists across Fargate task
# replacements and is reachable from any private subnet. For higher IOPS
# requirements, consider switching to EC2 launch type with an attached EBS volume.

resource "aws_efs_file_system" "qdrant_storage" {
  creation_token = "${local.name}-qdrant"
  encrypted      = true

  tags = { Name = "${local.name}-qdrant-storage" }
}

# Security group is defined without its ingress rule here to avoid a circular
# dependency with module.vector_db (see aws_security_group_rule below).
resource "aws_security_group" "efs" {
  name        = "${local.name}-efs"
  description = "NFS access to Qdrant EFS volume"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_efs_mount_target" "qdrant_storage" {
  for_each = toset(module.vpc.private_subnets)

  file_system_id  = aws_efs_file_system.qdrant_storage.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

# ── Cloud Map — internal DNS for vector_db ────────────────────────────────────
# Other services connect to Qdrant at vector-db.<namespace>:6333 without
# needing a load balancer, since Qdrant is not exposed externally.

resource "aws_service_discovery_private_dns_namespace" "internal" {
  name = local.service_namespace
  vpc  = module.vpc.vpc_id
}

resource "aws_service_discovery_service" "vector_db" {
  name = "vector-db"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.internal.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ── ECS Services ──────────────────────────────────────────────────────────────

module "vector_db" {
  source = "./modules/infrastructure/ecs"

  name                         = "${local.name}-vector-db"
  vpc_id                       = module.vpc.vpc_id
  private_subnets              = module.vpc.private_subnets
  aws_lb_arn                   = module.load_balancer.alb_arn
  certificate_arn              = module.acm.arn
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  ecs_cluster_id               = module.ecs_cluster.ecs_cluster_id
  ecs_cluster_name             = module.ecs_cluster.ecs_cluster_name
  ecr_repository_uri           = module.ecr.ecr_repository_url["vector-db"]
  image_tag                    = var.image_tag

  container_port  = 6333
  cpu             = 2048
  memory          = 4096
  create_listener = false

  health_check = {
    path                = "/healthz"
    accepted_response   = "200"
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  environment_variables = {
    VECTOR_DB_BIND_HOST = "0.0.0.0"
    VECTOR_DB_HTTP_PORT = "6333"
    VECTOR_DB_GRPC_PORT = "6334"
  }

  efs_mount_configuration = [{
    file_system_id = aws_efs_file_system.qdrant_storage.id
    container_path = "/qdrant/storage"
  }]

  service_discovery_service_arn = aws_service_discovery_service.vector_db.arn

  # Ensure mount targets exist in all subnets before the task starts
  depends_on = [aws_efs_mount_target.qdrant_storage]
}

module "mcp_server" {
  source = "./modules/infrastructure/ecs"

  name                         = "${local.name}-mcp-server"
  vpc_id                       = module.vpc.vpc_id
  private_subnets              = module.vpc.private_subnets
  aws_lb_arn                   = module.load_balancer.alb_arn
  certificate_arn              = module.acm.arn
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  ecs_cluster_id               = module.ecs_cluster.ecs_cluster_id
  ecs_cluster_name             = module.ecs_cluster.ecs_cluster_name
  ecr_repository_uri           = module.ecr.ecr_repository_url["mcp-server"]
  image_tag                    = var.image_tag

  container_port  = 8080
  cpu             = 1024
  memory          = 2048
  create_listener = true
  host            = "mcp.${var.domain_name}"

  health_check = {
    path                = "/health"
    accepted_response   = "200"
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  environment_variables = {
    MCP_SERVER_HOST = "0.0.0.0"
    MCP_SERVER_PORT = "8080"
    VECTOR_DB_HOST  = local.vector_db_host
    VECTOR_DB_PORT  = "6333"
  }
}

# data_ingestor and vector_query are long-running worker services with no HTTP
# endpoint. http_healthcheck is disabled and a process-based container
# healthcheck is used instead. The ecs module always creates an ALB target
# group, but no listener rule is attached so no ALB traffic reaches them.

module "data_ingestor" {
  source = "./modules/infrastructure/ecs"

  name                         = "${local.name}-data-ingestor"
  vpc_id                       = module.vpc.vpc_id
  private_subnets              = module.vpc.private_subnets
  aws_lb_arn                   = module.load_balancer.alb_arn
  certificate_arn              = module.acm.arn
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  ecs_cluster_id               = module.ecs_cluster.ecs_cluster_id
  ecs_cluster_name             = module.ecs_cluster.ecs_cluster_name
  ecr_repository_uri           = module.ecr.ecr_repository_url["data-ingestor"]
  image_tag                    = var.image_tag

  cpu              = 1024
  memory           = 2048
  create_listener  = false
  http_healthcheck = false

  container_healthcheck = {
    command     = ["CMD-SHELL", "pgrep -x sleep > /dev/null || exit 1"]
    interval    = 30
    timeout     = 5
    retries     = 3
    startPeriod = 60
  }

  environment_variables = {
    VECTOR_DB_HOST = local.vector_db_host
    VECTOR_DB_PORT = "6333"
  }
}

module "vector_query" {
  source = "./modules/infrastructure/ecs"

  name                         = "${local.name}-vector-query"
  vpc_id                       = module.vpc.vpc_id
  private_subnets              = module.vpc.private_subnets
  aws_lb_arn                   = module.load_balancer.alb_arn
  certificate_arn              = module.acm.arn
  load_balancer_security_group = module.load_balancer.load_balancer_security_group_id
  ecs_cluster_id               = module.ecs_cluster.ecs_cluster_id
  ecs_cluster_name             = module.ecs_cluster.ecs_cluster_name
  ecr_repository_uri           = module.ecr.ecr_repository_url["vector-query"]
  image_tag                    = var.image_tag

  cpu              = 1024
  memory           = 2048
  create_listener  = false
  http_healthcheck = false

  container_healthcheck = {
    command     = ["CMD-SHELL", "pgrep -x sleep > /dev/null || exit 1"]
    interval    = 30
    timeout     = 5
    retries     = 3
    startPeriod = 60
  }

  environment_variables = {
    VECTOR_DB_HOST = local.vector_db_host
    VECTOR_DB_PORT = "6333"
  }
}

# ── Inter-service security group rules ────────────────────────────────────────
# Defined as separate resources after all ECS modules to avoid circular
# dependencies between the EFS security group and vector_db, and between
# vector_db and its consumer services.

resource "aws_security_group_rule" "efs_from_vector_db" {
  description              = "NFS from vector_db ECS task"
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = aws_security_group.efs.id
  source_security_group_id = module.vector_db.ecs_sg_id
}

resource "aws_security_group_rule" "vector_db_from_mcp_server" {
  description              = "mcp_server → vector_db (HTTP + gRPC)"
  type                     = "ingress"
  from_port                = 6333
  to_port                  = 6334
  protocol                 = "tcp"
  security_group_id        = module.vector_db.ecs_sg_id
  source_security_group_id = module.mcp_server.ecs_sg_id
}

resource "aws_security_group_rule" "vector_db_from_data_ingestor" {
  description              = "data_ingestor → vector_db (HTTP + gRPC)"
  type                     = "ingress"
  from_port                = 6333
  to_port                  = 6334
  protocol                 = "tcp"
  security_group_id        = module.vector_db.ecs_sg_id
  source_security_group_id = module.data_ingestor.ecs_sg_id
}

resource "aws_security_group_rule" "vector_db_from_vector_query" {
  description              = "vector_query → vector_db (HTTP + gRPC)"
  type                     = "ingress"
  from_port                = 6333
  to_port                  = 6334
  protocol                 = "tcp"
  security_group_id        = module.vector_db.ecs_sg_id
  source_security_group_id = module.vector_query.ecs_sg_id
}

# ── Alarms ────────────────────────────────────────────────────────────────────

module "mcp_server_alarms" {
  source = "./modules/observability/ecs-alarms"

  name             = "${local.name}-mcp-server"
  ecs_cluster_name = module.ecs_cluster.ecs_cluster_name
  ecs_service_name = module.mcp_server.ecs_service_name
  sns_topic_arn    = [aws_sns_topic.alerts.arn]
}

module "vector_db_alarms" {
  source = "./modules/observability/ecs-alarms"

  name             = "${local.name}-vector-db"
  ecs_cluster_name = module.ecs_cluster.ecs_cluster_name
  ecs_service_name = module.vector_db.ecs_service_name
  sns_topic_arn    = [aws_sns_topic.alerts.arn]
}

module "alb_alarms" {
  source = "./modules/observability/alb-alarms"

  name          = local.name
  alb_arn       = module.load_balancer.alb_arn
  target_group  = module.mcp_server.aws_lb_target_group_name
  sns_topic_arn = [aws_sns_topic.alerts.arn]
}
