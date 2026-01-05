resource "aws_route_table" "this" {
  vpc_id = var.vpc_id
  tags   = var.tags
}

locals {
  targets = [
    var.carrier_gateway_id,
    var.core_network_arn,
    var.egress_only_gateway_id,
    var.gateway_id,
    var.local_gateway_id,
    var.nat_gateway_id,
    var.network_interface_id,
    var.transit_gateway_id,
    var.vpc_endpoint_id,
    var.vpc_peering_connection_id,
    var.destination_prefix_list_id,
  ]
  // has_target is true if any of the possible target variables is set
  has_target = length([for t in local.targets : t if t != null && t != ""]) > 0

  // has_destination is true when a destination is provided (IPv4/IPv6/prefix-list)
  has_destination = (var.cidr_block != null && var.cidr_block != "") || (var.ipv6_cidr_block != null && var.ipv6_cidr_block != "") || (var.destination_prefix_list_id != null && var.destination_prefix_list_id != "")
}


resource "aws_route_table_association" "this" {
  for_each       = length(var.subnet_ids) > 0 ? { for idx, s in var.subnet_ids : idx => s } : {}
  subnet_id      = each.value
  route_table_id = aws_route_table.this.id
}
