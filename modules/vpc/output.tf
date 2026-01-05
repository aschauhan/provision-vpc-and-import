output "id" {
  description = "The ID of the VPC"
  value       = aws_vpc.child_module.id
}