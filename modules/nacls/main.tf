resource "aws_network_acl" "public" {
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

resource "aws_network_acl_rule" "nonroutable_10_rule" {
  network_acl_id = aws_network_acl.private_nonroutable.id
  rule_number    = 100
  egress         = false
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/8"
  from_port      = 0
  to_port        = 0
}
