resource "aws_vpc" "child_module" {
  cidr_block                           = var.cidr_block
  instance_tenancy                     = var.instance_tenancy
  ipv4_ipam_pool_id                    = var.ipv4_ipam_pool_id
  ipv4_netmask_length                  = var.ipv4_netmask_length
  ipv6_cidr_block                      = var.ipv6_cidr_block
  ipv6_ipam_pool_id                    = var.ipv6_ipam_pool_id
  ipv6_netmask_length                  = var.ipv6_netmask_length
  ipv6_cidr_block_network_border_group = var.ipv6_cidr_block_network_border_group
  enable_dns_support                   = var.enable_dns_support
  enable_network_address_usage_metrics = var.enable_network_address_usage_metrics
  enable_dns_hostnames                 = var.enable_dns_hostnames
  assign_generated_ipv6_cidr_block     = var.assign_generated_ipv6_cidr_block
  tags                                 = merge(var.base_tag, var.tags)
}

resource "aws_vpc_ipv4_cidr_block_association" "additional" {
  for_each = toset(var.additional_cidrs)

  vpc_id     = aws_vpc.child_module.id
  cidr_block = each.value
}