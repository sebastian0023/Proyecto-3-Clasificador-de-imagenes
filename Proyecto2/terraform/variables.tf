variable "aws_region" {
  description = "Región de AWS para desplegar la infraestructura"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Entorno de ejecución (prod, dev, staging)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Nombre base del proyecto"
  type        = string
  default     = "dataset-quality"
}

variable "vpc_cidr" {
  description = "Bloque CIDR para la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zonas de disponibilidad a utilizar"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "s3_bucket_name" {
  description = "Nombre único global para el bucket S3 del remote DVC"
  type        = string
  default     = "dataset-quality-prod-storage"
}

variable "github_repository" {
  description = "Repositorio de GitHub en formato 'owner/repo' para la asunción del rol OIDC"
  type        = string
  default     = "stephy0410/ruta-al-dataset-v1"
}

variable "tags" {
  description = "Etiquetas personalizadas para añadir a todos los recursos"
  type        = map(string)
  default     = {}
}

