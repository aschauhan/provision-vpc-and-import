output "route_table_id" {
  description = "The ID of the created route table."
  value       = aws_route_table.this.id
}

output "route_table_arn" {
  description = "The ARN of the created route table."
  value       = aws_route_table.this.arn
}


output "association_ids" {
  description = "Map of association IDs keyed by subnet id."
  value       = { for k, a in aws_route_table_association.this : a.subnet_id => a.id }
}
// routing-tables module outputs removed — placeholder
// Module removed by request; keep this placeholder to avoid accidental reuse.