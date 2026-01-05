output "id" {
  description = "The ID of the subnet"
  value       = aws_subnet.child_module.id
}

output "cidr_block" {
  description = "CIDR block of the subnet"
  value       = aws_subnet.child_module.cidr_block
}

output "availability_zone" {
  description = "Availability Zone of the subnet"
  value       = aws_subnet.child_module.availability_zone
}
