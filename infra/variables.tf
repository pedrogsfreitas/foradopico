variable "subscription_id" {
  description = "ID da assinatura Azure (az account show --query id -o tsv)."
  type        = string
}

variable "location" {
  description = "Região Azure. Assinaturas de estudante podem restringir regiões; troque se o apply for negado por política."
  type        = string
  default     = "brazilsouth"
}

variable "prefix" {
  description = "Prefixo dos nomes dos recursos."
  type        = string
  default     = "foradopico"
}

variable "dns_label" {
  description = "Rótulo DNS do IP público. Precisa ser único na região: vira <rotulo>.<regiao>.cloudapp.azure.com."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,61}[a-z0-9]$", var.dns_label))
    error_message = "Use só letras minúsculas, números e hífen, começando por letra."
  }
}

variable "admin_cidr" {
  description = "Único endereço autorizado a acessar o SSH (porta 22), no formato x.x.x.x/32."
  type        = string

  validation {
    condition     = can(cidrhost(var.admin_cidr, 0)) && !endswith(var.admin_cidr, "/0")
    error_message = "A porta de administração nunca pode ficar aberta para a internet inteira (0.0.0.0/0). Informe o seu IP público com /32."
  }
}

variable "ssh_public_key" {
  description = "Conteúdo da chave pública SSH do administrador (ex.: arquivo id_ed25519.pub ou id_rsa.pub)."
  type        = string
}

variable "vm_size" {
  description = "Tamanho da VM."
  type        = string
  default     = "Standard_B1s"
}

variable "image" {
  description = "Imagem do app no GHCR, sem a tag (ex.: ghcr.io/usuario/foradopico). Tudo em minúsculas."
  type        = string

  validation {
    condition     = var.image == lower(var.image)
    error_message = "O nome da imagem precisa estar em minúsculas."
  }
}

variable "acme_email" {
  description = "E-mail usado pelo Caddy para emitir o certificado HTTPS (Let's Encrypt)."
  type        = string
}
