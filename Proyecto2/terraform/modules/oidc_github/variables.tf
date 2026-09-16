variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Entorno de despliegue (prod, dev, staging)"
  type        = string
}

variable "github_repository" {
  description = "Repositorio de GitHub en formato 'owner/repo' autorizado para asumir el rol (ej: stephy0410/ruta-al-dataset-v1)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN del bucket S3 de datasets para otorgar permisos mínimos de lectura/escritura"
  type        = string
}

variable "tags" {
  description = "Etiquetas adicionales para los recursos IAM"
  type        = map(string)
  default     = {}
}

