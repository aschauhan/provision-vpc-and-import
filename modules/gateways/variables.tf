variable "vpc_id" {
  description = "VPC ID where gateways will be created."
  type        = string
}

variable "create_igw" {
  description = "Whether to create an Internet Gateway."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to created resources."
  type        = map(string)
  default     = {}
}

// Map of public NAT configs keyed by a name. Each entry should include:
// - private_subnet_id: the subnet that will use the NAT
// - public_subnet_id: the subnet where NAT will be placed
// Optional fields mirror aws_nat_gateway arguments: allocation_id, availability_mode, connectivity_type, private_ip, secondary_allocation_ids, secondary_private_ip_address_count, secondary_private_ip_addresses, availability_zone_address (list of objects)
variable "public_nat_configs" {
  description = "Map of configs to create public NAT gateways."
  type = map(object({
    private_subnet_id                  = string
    public_subnet_id                   = string
    allocation_id                      = optional(string)
    availability_mode                  = optional(string)
    availability_zone_address          = optional(list(object({ availability_zone = string, allocation_id = string })))
    connectivity_type                  = optional(string)
    private_ip                         = optional(string)
    secondary_allocation_ids           = optional(list(string))
    secondary_private_ip_address_count = optional(number)
    secondary_private_ip_addresses     = optional(list(string))
    # Optional display/naming helpers
    nat_name     = optional(string)
    display_name = optional(string)
  }))
  default = {}
}

// Map of private NAT configs (no public EIP). Similar shape but allocation_id must not be set.
variable "private_nat_configs" {
  description = "Map of configs to create private NAT gateways (no public EIP)."
  type = map(object({
    subnet_id                          = string
    availability_mode                  = optional(string)
    private_ip                         = optional(string)
    secondary_private_ip_address_count = optional(number)
    secondary_private_ip_addresses     = optional(list(string))
    # Optional display/naming helpers
    nat_name     = optional(string)
    display_name = optional(string)
  }))
  default = {}
}
