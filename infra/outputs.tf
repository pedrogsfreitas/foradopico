output "url_do_mvp" {
  description = "URL pública do MVP."
  value       = "https://${local.fqdn}"
}

output "ip_publico" {
  value = azurerm_public_ip.app.ip_address
}

output "ssh" {
  description = "Acesso de administração (só funciona a partir do admin_cidr)."
  value       = "ssh azureuser@${local.fqdn}"
}
