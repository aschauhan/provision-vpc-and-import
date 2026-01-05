variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "dev"
}
variable "base_tag" {
  description = "Common tags for all resources (Region, application, vpc_name, created by)"
  type        = map(string)
}


variable "vpc_name" {
  description = "Name to assign to the VPC (e.g., ntw-dev-vpc1)"
  type        = string
  default     = "ntw-dev-vpc1"
}


variable "region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "vpc_cidr" {
  description = "Primary CIDR block for the VPC"
  type        = string
}

variable "additional_cidrs" {
  description = "Additional CIDR blocks to associate with the VPC"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "List of CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "List of CIDR blocks for private subnets"
  type        = list(string)
}

variable "nonroutable_subnet_cidrs" {
  description = "List of CIDR blocks for non-routable subnets"
  type        = list(string)
}

variable "azs" {
  description = "List of Availability Zones to spread subnets across"
  type        = list(string)
}

variable "enable_private_onprem_route" {
  description = "If true, add an additional route to all private route tables (VPC-specific via tfvars)."
  type        = bool
  default     = false
}

variable "private_onprem_destination_cidr" {
  description = "Destination CIDR for the optional private on-prem route."
  type        = string
  default     = "10.0.0.0/8"
}