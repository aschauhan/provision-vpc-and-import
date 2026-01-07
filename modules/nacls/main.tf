locals {
  create_public_nacl  = var.enabled && var.enable_public_nacl && length(var.public_subnet_ids) > 0
  create_private_nacl = var.enabled && var.enable_private_nacl && (length(var.private_subnet_ids) > 0 || length(var.nonroutable_subnet_ids) > 0)

  public_ingress_rules  = { for r in var.public_ingress_rules : tostring(r.rule_number) => r }
  public_egress_rules   = { for r in var.public_egress_rules : tostring(r.rule_number) => r }
  private_ingress_rules = { for r in var.private_ingress_rules : tostring(r.rule_number) => r }
  private_egress_rules  = { for r in var.private_egress_rules : tostring(r.rule_number) => r }
}

resource "aws_network_acl" "public" {
  count      = local.create_public_nacl ? 1 : 0
  vpc_id     = var.vpc_id
  subnet_ids = var.public_subnet_ids
  tags = merge(var.base_tag, {
    Name            = "ntw-${var.vpc_name}-public-nacl"
    Environment     = var.vpc_name
    "Resource Type" = "nacl"
    "Creation Date" = timestamp()
  })

  lifecycle {
    ignore_changes = [tags["Creation Date"]]
  }
}

resource "aws_network_acl" "private_nonroutable" {
  count      = local.create_private_nacl ? 1 : 0
  vpc_id     = var.vpc_id
  subnet_ids = concat(var.private_subnet_ids, var.nonroutable_subnet_ids)
  tags = merge(var.base_tag, {
    Name            = "ntw-${var.vpc_name}-private-nonroutable-nacl"
    Environment     = var.vpc_name
    "Resource Type" = "nacl"
    "Creation Date" = timestamp()
  })

  lifecycle {
    ignore_changes = [tags["Creation Date"]]
  }
}

resource "aws_network_acl_rule" "public_ingress" {
  for_each        = local.create_public_nacl ? local.public_ingress_rules : {}
  network_acl_id  = aws_network_acl.public[0].id
  rule_number     = each.value.rule_number
  egress          = false
  protocol        = each.value.protocol
  rule_action     = each.value.rule_action
  cidr_block      = try(each.value.cidr_block, null)
  ipv6_cidr_block = try(each.value.ipv6_cidr_block, null)
  from_port       = each.value.from_port
  to_port         = each.value.to_port
}

resource "aws_network_acl_rule" "public_egress" {
  for_each        = local.create_public_nacl ? local.public_egress_rules : {}
  network_acl_id  = aws_network_acl.public[0].id
  rule_number     = each.value.rule_number
  egress          = true
  protocol        = each.value.protocol
  rule_action     = each.value.rule_action
  cidr_block      = try(each.value.cidr_block, null)
  ipv6_cidr_block = try(each.value.ipv6_cidr_block, null)
  from_port       = each.value.from_port
  to_port         = each.value.to_port
}

resource "aws_network_acl_rule" "private_ingress" {
  for_each        = local.create_private_nacl ? local.private_ingress_rules : {}
  network_acl_id  = aws_network_acl.private_nonroutable[0].id
  rule_number     = each.value.rule_number
  egress          = false
  protocol        = each.value.protocol
  rule_action     = each.value.rule_action
  cidr_block      = try(each.value.cidr_block, null)
  ipv6_cidr_block = try(each.value.ipv6_cidr_block, null)
  from_port       = each.value.from_port
  to_port         = each.value.to_port
}

resource "aws_network_acl_rule" "private_egress" {
  for_each        = local.create_private_nacl ? local.private_egress_rules : {}
  network_acl_id  = aws_network_acl.private_nonroutable[0].id
  rule_number     = each.value.rule_number
  egress          = true
  protocol        = each.value.protocol
  rule_action     = each.value.rule_action
  cidr_block      = try(each.value.cidr_block, null)
  ipv6_cidr_block = try(each.value.ipv6_cidr_block, null)
  from_port       = each.value.from_port
  to_port         = each.value.to_port
}
