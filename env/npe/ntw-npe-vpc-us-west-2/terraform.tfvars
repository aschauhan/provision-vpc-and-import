base_tag = {
  Region       = "us-west-2"
  application  = "ntw"
  environment  = "npe"
  "created by" = "Cloud Network Team"
}
environment = "npe"
region      = "us-west-2"

vpc_cidr = "10.65.254.0/24"

additional_cidrs = [
  "100.65.253.0/24",
  "100.65.254.0/24",
]

# 3 public subnets across 3 AZs (from 100.65.253.0/24)
public_subnet_cidrs = [
  "100.65.253.0/28",    # us-west-2a
  "100.65.253.16/28",   # us-west-2b
  "100.65.253.32/28",   # us-west-2c
]

# 3 private subnets across 3 AZs (from 10.65.254.0/24)
private_subnet_cidrs = [
  "10.65.254.0/28",     # us-west-2a
  "10.65.254.16/28",    # us-west-2b
  "10.65.254.32/28",    # us-west-2c
]

# 3 non-routable subnets across 3 AZs (from 100.65.254.0/24)
nonroutable_subnet_cidrs = [
  "100.65.254.0/26",    # us-west-2a
  "100.65.254.64/26",   # us-west-2b
  "100.65.254.128/26",  # us-west-2c
]

azs = [
  "us-west-2a",
  "us-west-2b",
  "us-west-2c"
]

vpc_name = "ntw-npe-vpc"

############################
# Provisioning toggles
############################

enable_additional_cidrs          = true
enable_public_subnets            = true
enable_private_subnets           = true
enable_nonroutable_subnets       = true

enable_gateways                  = true
enable_internet_gateway          = true
enable_public_nat_gateways       = true
enable_private_nat_gateways      = true

enable_public_route_table        = true
enable_private_route_tables      = true
enable_nonroutable_route_tables  = true

enable_nacls                     = true
enable_public_nacl               = true
enable_private_nonroutable_nacl  = true

enable_s3_gateway_endpoint       = true
enable_interface_endpoints       = true
enable_vpc_endpoints_sg          = true

vpc_endpoints_security_group_ids = []

############################
# NACL rules
############################

nacl_rules = {
  public_ingress = [
    {
      rule_number = 100
      protocol    = "-1"
      rule_action = "allow"
      cidr_block  = "0.0.0.0/0"
      from_port   = 0
      to_port     = 0
    },
  ]
  public_egress = [
    {
      rule_number = 100
      protocol    = "-1"
      rule_action = "allow"
      cidr_block  = "0.0.0.0/0"
      from_port   = 0
      to_port     = 0
    },
  ]

  private_ingress = [
    {
      rule_number = 100
      protocol    = "-1"
      rule_action = "allow"
      cidr_block  = "10.0.0.0/8"
      from_port   = 0
      to_port     = 0
    },
  ]
  private_egress = [
    {
      rule_number = 100
      protocol    = "-1"
      rule_action = "allow"
      cidr_block  = "0.0.0.0/0"
      from_port   = 0
      to_port     = 0
    },
  ]
}

############################
# Security groups
############################

security_groups = {}

############################
# Extra routes
############################

public_extra_routes      = []
private_extra_routes     = []
nonroutable_extra_routes = []
