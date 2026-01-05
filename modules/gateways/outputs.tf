output "igw_id" {
  description = "The Internet Gateway ID (if created)."
  value       = length(aws_internet_gateway.igw) > 0 ? aws_internet_gateway.igw[0].id : null
}

output "public_nat_ids" {
  description = "Map of public NAT gateway IDs keyed by config key."
  value       = { for k, v in aws_nat_gateway.public : k => v.id }
}

output "private_nat_ids" {
  description = "Map of private NAT gateway IDs keyed by config key."
  value       = { for k, v in aws_nat_gateway.private : k => v.id }
}
