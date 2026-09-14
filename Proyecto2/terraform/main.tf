# =============================================================================
# Infraestructura Proyecto 2: Calidad y Versionado de Datasets
# Orquestación de módulos: Red + S3 Gateway Endpoint, S3 Storage y OIDC IAM.
# =============================================================================

module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  tags               = var.tags
}

module "s3" {
  source = "./modules/s3"

  bucket_name  = var.s3_bucket_name
  environment  = var.environment
  project_name = var.project_name
  tags         = var.tags
}

module "oidc_github" {
  source = "./modules/oidc_github"

  project_name      = var.project_name
  environment       = var.environment
  github_repository = var.github_repository
  s3_bucket_arn     = module.s3.bucket_arn
  tags              = var.tags
}

