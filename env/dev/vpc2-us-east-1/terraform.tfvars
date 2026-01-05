base_tag = {
  Region       = "us-east-1"
  application  = "ntw"
  environment  = "dev"
  "created by" = "Cloud Network Team"
}
region = "us-east-1"

vpc_cidr = "10.63.0.0/24"

additional_cidrs = [
  "100.63.0.0/20",
  "100.62.0.0/24",
]

public_subnet_cidrs = [
  "100.63.0.0/26",
  "100.63.0.64/26",
  "100.63.0.128/26",
]

private_subnet_cidrs = [
  "10.63.0.0/28",
  "10.63.0.16/28",
  "10.63.0.32/28",
]

nonroutable_subnet_cidrs = [
  "100.62.0.0/28",
  "100.62.0.16/28",
  "100.62.0.32/28",
]

azs = [
  "us-east-1a",
  "us-east-1b",
  "us-east-1c"
]

# Add vpc_name for all modules
vpc_name = "ntw-dev-demo-2-vpc"