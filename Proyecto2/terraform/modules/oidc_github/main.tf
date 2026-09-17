# -----------------------------------------------------------------------------
# Proveedor OIDC de GitHub Actions
# Permite autenticación federada sin almacenar claves estáticas en el repositorio,
# garantizando el cumplimiento estricto de la compuerta M2 (cero secretos).
# -----------------------------------------------------------------------------
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = distinct(concat(
    [data.tls_certificate.github.certificates[0].sha1_fingerprint],
    ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f8d264fcd9"]
  ))

  tags = merge(
    var.tags,
    {
      Name        = "github-actions-oidc-provider"
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# -----------------------------------------------------------------------------
# Política de asunción de rol (Trust Policy)
# Solo permite asumir el rol a flujos de trabajo de GitHub Actions originados
# en el repositorio configurado.
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:*"]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.project_name}-${var.environment}-github-actions-role"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-github-actions-role"
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
    }
  )
}

# -----------------------------------------------------------------------------
# Política de privilegios mínimos para el remote DVC en S3
# Otorga únicamente ListBucket, GetObject, PutObject y DeleteObject.
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "dvc_s3_access" {
  statement {
    sid    = "ListDvcBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = var.s3_bucket_arns
  }

  statement {
    sid    = "ReadWriteDvcObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [for arn in var.s3_bucket_arns : "${arn}/*"]
  }
}

resource "aws_iam_policy" "dvc_s3_access" {
  name        = "${var.project_name}-${var.environment}-dvc-s3-access"
  description = "Política de mínimos privilegios para el remote DVC sobre S3"
  policy      = data.aws_iam_policy_document.dvc_s3_access.json

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

resource "aws_iam_role_policy_attachment" "github_actions_s3" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.dvc_s3_access.arn
}

