# NACLs for public, private, and nonroutable subnets
module "nacls" {
  source                 = "./modules/nacls"
  vpc_id                 = module.vpc.id
  public_subnet_ids      = [for m in values(module.public_subnets) : m.id]
  private_subnet_ids     = [for m in values(module.private_subnets) : m.id]
  nonroutable_subnet_ids = [for m in values(module.nonroutable_subnets) : m.id]
  base_tag               = var.base_tag
  vpc_name               = var.vpc_name
}
# VPC from child module
module "vpc" {
  source = "./modules/vpc"

  region               = var.region
  cidr_block           = var.vpc_cidr
  additional_cidrs     = var.additional_cidrs
  instance_tenancy     = "default"
  enable_dns_support   = true
  enable_dns_hostnames = true
  base_tag             = var.base_tag
  tags = {
    Name        = var.vpc_name
    Environment = var.vpc_name
  }
}

# Public subnets
module "public_subnets" {
  source     = "./modules/subnets"
  for_each   = toset(var.public_subnet_cidrs)
  depends_on = [module.vpc]

  vpc_id                  = module.vpc.id
  cidr_block              = each.value
  availability_zone       = element(var.azs, index(var.public_subnet_cidrs, each.value))
  map_public_ip_on_launch = true
  region                  = var.region
  name                    = "ntw-dev-public-subnet-${element(var.azs, index(var.public_subnet_cidrs, each.value))}"
  application             = "ntw"
  created_by              = "Cloud Network Team"
  creation_date           = timestamp()
  tags = {
    Tier = "public"
  }
}

# Private subnets
module "private_subnets" {
  source     = "./modules/subnets"
  for_each   = toset(var.private_subnet_cidrs)
  depends_on = [module.vpc]

  vpc_id            = module.vpc.id
  cidr_block        = each.value
  availability_zone = element(var.azs, index(var.private_subnet_cidrs, each.value))
  region            = var.region
  name              = "ntw-dev-private-subnet-${element(var.azs, index(var.private_subnet_cidrs, each.value))}"
  application       = "ntw"
  created_by        = "Cloud Network Team"
  creation_date     = timestamp()
  tags = {
    Tier = "private"
  }
}

# Non‑routable subnets
module "nonroutable_subnets" {
  source     = "./modules/subnets"
  for_each   = toset(var.nonroutable_subnet_cidrs)
  depends_on = [module.vpc]

  vpc_id            = module.vpc.id
  cidr_block        = each.value
  availability_zone = element(var.azs, index(var.nonroutable_subnet_cidrs, each.value))
  region            = var.region
  name              = "ntw-dev-nonroutable-subnet-${element(var.azs, index(var.nonroutable_subnet_cidrs, each.value))}"
  application       = "ntw"
  created_by        = "Cloud Network Team"
  creation_date     = timestamp()
  tags = {
    Tier     = "nonroutable"
    PointsTo = "nat-private-${index(var.nonroutable_subnet_cidrs, each.value) + 1}-${each.value}"
  }
}


# Public route table (single) — associates all public subnets with one RT.
module "public_route_table" {
  source = "./modules/routing-tables"
  vpc_id = module.vpc.id
  # default route for internet-bound traffic
  cidr_block = "0.0.0.0/0"
  gateway_id = module.gateways.igw_id
  subnet_ids = [for m in values(module.public_subnets) : m.id]
  depends_on = [module.gateways]

  tags = {
    Name        = "${var.vpc_name}-public-rt"
    Environment = var.vpc_name
    Tier        = "public"
  }
}

# Private route tables — one per private subnet 

module "private_route_tables" {
  source   = "./modules/routing-tables"
  for_each = toset(var.private_subnet_cidrs)

  vpc_id = module.vpc.id

  # default route for private subnets -> their public NAT gateway

  cidr_block = "0.0.0.0/0"
  # During import, NATs are brought in one-by-one; avoid failing refresh when some keys don't exist yet.
  nat_gateway_id = try(module.gateways.public_nat_ids[each.value], null)
  subnet_ids     = [module.private_subnets[each.value].id]
  depends_on     = [module.gateways]

  tags = {
    Name        = "${var.vpc_name}-private-${index(var.private_subnet_cidrs, each.value) + 1}"
    Environment = var.vpc_name
    Tier        = "private"
  }
}

# Nonroutable route tables — one per nonroutable subnet
module "nonroutable_route_tables" {
  source   = "./modules/routing-tables"
  for_each = toset(var.nonroutable_subnet_cidrs)

  vpc_id = module.vpc.id

  # default route for nonroutable subnets -> private NAT gateway
  cidr_block = "0.0.0.0/0"
  # During import, NATs are brought in one-by-one; avoid failing refresh when some keys don't exist yet.
  nat_gateway_id = try(module.gateways.private_nat_ids[each.value], null)
  subnet_ids     = [module.nonroutable_subnets[each.value].id]
  depends_on     = [module.gateways]

  tags = {
    Name        = "${var.vpc_name}-nonroutable-${index(var.nonroutable_subnet_cidrs, each.value) + 1}"
    Environment = var.vpc_name
    Tier        = "nonroutable"
  }
}

# Gateways: create IGW + NATs
module "gateways" {
  source = "./modules/gateways"

  vpc_id     = module.vpc.id
  create_igw = true
  tags = {
    Environment = var.vpc_name
    Name        = "${var.vpc_name}-gateways"
  }

  // create one public NAT per private subnet placed in the corresponding public subnet (same index)
  public_nat_configs = {
    for idx, cidr in var.private_subnet_cidrs : cidr => {
      private_subnet_id = module.private_subnets[cidr].id
      public_subnet_id  = module.public_subnets[element(var.public_subnet_cidrs, idx)].id

      availability_mode = "zonal"
      connectivity_type = "public"

      nat_name     = "nat-public-${idx + 1}-${cidr}"
      display_name = "${var.vpc_name}-public-${idx + 1}"
    }
  }

  // create one private NAT per nonroutable subnet (no public EIP)

  private_nat_configs = {
    for idx, cidr in var.nonroutable_subnet_cidrs : cidr => {
      subnet_id         = module.nonroutable_subnets[cidr].id
      availability_mode = "zonal"
      # user-friendly display name for the nonroutable route table -> NAT mapping
      display_name = "${var.vpc_name}-nonroutable-${idx + 1}"
      # nat resource name: include an index and the CIDR for easy lookup
      nat_name = "nat-private-${idx + 1}-${cidr}"
    }
  }
}

# Explicit aws_route resources for each route table
# Public route table: default route to IGW
resource "aws_route" "public_default" {
  route_table_id         = module.public_route_table.route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = module.gateways.igw_id
}

# Private route tables: default route to public NAT gateway
resource "aws_route" "private_default" {
  for_each               = module.private_route_tables
  route_table_id         = each.value["route_table_id"]
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = try(module.gateways.public_nat_ids[each.key], null)
}

# Optional: additional route for private route tables (enabled per-VPC via tfvars)
resource "aws_route" "private_onprem" {
  for_each               = var.enable_private_onprem_route ? module.private_route_tables : {}
  route_table_id         = each.value["route_table_id"]
  destination_cidr_block = var.private_onprem_destination_cidr
  nat_gateway_id         = try(module.gateways.public_nat_ids[each.key], null)
}

# Nonroutable route tables: default route to private NAT gateway

resource "aws_route" "nonroutable_default" {
  for_each               = module.nonroutable_route_tables
  route_table_id         = each.value["route_table_id"]
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = try(module.gateways.private_nat_ids[each.key], null)
}

# DHCP Options Set
module "dhcp_options" {
  source               = "./modules/dhcp-options"
  vpc_id               = module.vpc.id
  domain_name          = "ec2.internal"
  domain_name_servers  = ["AmazonProvidedDNS"]
  ntp_servers          = []
  netbios_name_servers = []
  netbios_node_type    = null
  tags = {
    Name        = "${var.vpc_name}-dhcp-options"
    Environment = var.vpc_name
  }
}

# S3 Gateway Endpoint (private and nonroutable subnets only)

module "s3_vpc_endpoint" {
  source            = "./modules/vpc-endpoint"
  vpc_id            = module.vpc.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat([for m in values(module.private_route_tables) : m.route_table_id], [for m in values(module.nonroutable_route_tables) : m.route_table_id])
  tags = {
    Name        = "${var.vpc_name}-s3-endpoint"
    Environment = var.vpc_name
  }
}


# Security group for VPC endpoints 
module "vpc_endpoints_sg" {
  source      = "./modules/security-group"
  name        = "${var.vpc_name}-endpoints-sg"
  description = "Security group for VPC endpoints (EC2, SSM)"
  vpc_id      = module.vpc.id
  ingress_rules = [
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = [var.vpc_cidr]
      description = "Allow HTTPS from within VPC"
    }
  ]
  egress_rules = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
      description = "Allow all outbound traffic"
    }
  ]
  base_tag = var.base_tag
  tags = {
    Name        = "${var.vpc_name}-endpoints-sg"
    Environment = var.vpc_name
  }
}

# EC2 Interface Endpoint (all subnets except public)

module "ec2_vpc_endpoint" {
  source            = "./modules/vpc-endpoint"
  vpc_id            = module.vpc.id
  service_name      = "com.amazonaws.${var.region}.ec2"
  vpc_endpoint_type = "Interface"
  subnet_ids = distinct([for az in var.azs :
    lookup({ for k, s in module.private_subnets : s.availability_zone => s.id }, az, null) != null ? lookup({ for k, s in module.private_subnets : s.availability_zone => s.id }, az, null) : lookup({ for k, s in module.nonroutable_subnets : s.availability_zone => s.id }, az, null)
  ])
  security_group_ids  = [module.vpc_endpoints_sg.security_group_id]
  private_dns_enabled = true
  tags = {
    Name        = "${var.vpc_name}-ec2-endpoint"
    Environment = var.vpc_name
  }
}

# SSM Interface Endpoint (all subnets except public)

module "ssm_vpc_endpoint" {
  source            = "./modules/vpc-endpoint"
  vpc_id            = module.vpc.id
  service_name      = "com.amazonaws.${var.region}.ssm"
  vpc_endpoint_type = "Interface"
  subnet_ids = distinct([for az in var.azs :
    lookup({ for k, s in module.private_subnets : s.availability_zone => s.id }, az, null) != null ? lookup({ for k, s in module.private_subnets : s.availability_zone => s.id }, az, null) : lookup({ for k, s in module.nonroutable_subnets : s.availability_zone => s.id }, az, null)
  ])
  security_group_ids  = [module.vpc_endpoints_sg.security_group_id]
  private_dns_enabled = true
  tags = {
    Name        = "${var.vpc_name}-ssm-endpoint"
    Environment = var.vpc_name
  }
}



