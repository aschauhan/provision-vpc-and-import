resource "aws_subnet" "child_module" {
  vpc_id            = var.vpc_id
  cidr_block        = var.cidr_block
  availability_zone = var.availability_zone

  map_public_ip_on_launch = var.map_public_ip_on_launch

  tags = merge(var.tags, {
    Name               = var.name != null ? var.name : coalesce(lookup(var.tags, "Name", null), var.vpc_name != null && var.application != null ? "${var.application}-${var.vpc_name}-subnet" : var.vpc_name != null ? "${var.vpc_name}-subnet" : "subnet")
    Region             = var.region
    Environment        = var.vpc_name
    "Application o..." = var.application
    "Resource Type"    = "subnet"
    "Created by"       = var.created_by
    "Creation Date"    = var.creation_date
  })

  lifecycle {
    ignore_changes = [tags["Creation Date"]]
  }
}
