resource "aws_vpc_endpoint" "this" {
  vpc_id              = var.vpc_id
  service_name        = var.service_name
  vpc_endpoint_type   = var.vpc_endpoint_type
  subnet_ids          = var.subnet_ids
  security_group_ids  = var.security_group_ids
  private_dns_enabled = var.private_dns_enabled
  policy              = var.policy
  route_table_ids     = var.route_table_ids
  ip_address_type     = var.ip_address_type
  tags                = var.tags
}
