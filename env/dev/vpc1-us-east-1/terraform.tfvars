base_tag = {
  Region       = "us-east-1"
  application  = "ntw"
  environment  = "dev"
  "created by" = "Cloud Network Team"
}
environment = "dev"
region      = "us-east-1"

vpc_cidr = "10.65.0.0/24"

additional_cidrs = [
  "100.65.0.0/20",
  "100.64.0.0/24",
]

public_subnet_cidrs = [
  "100.65.0.0/26",
  "100.65.0.64/26",
  "100.65.0.128/26",
]

private_subnet_cidrs = [
  "10.65.0.0/28",
  "10.65.0.16/28",
  "10.65.0.32/28",
]

nonroutable_subnet_cidrs = [
  "100.64.0.0/28",
  "100.64.0.16/28",
  "100.64.0.32/28",
]

azs = [
  "us-east-1a",
  "us-east-1b",
  "us-east-1c"
]

# Add vpc_name for all modules
vpc_name = "ntw-dev-demo-vpc"

# VPC1-only: add an extra private route
enable_private_onprem_route     = false
private_onprem_destination_cidr = "10.0.0.0/8"