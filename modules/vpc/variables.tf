variable "region" {
  type    = string
  default = null
}

variable "cidr_block" {
  type    = string
  default = null
}

variable "instance_tenancy" {
  type    = string
  default = "default"
}

variable "ipv4_ipam_pool_id" {
  type    = string
  default = null
}

variable "ipv4_netmask_length" {
  type    = number
  default = null
}

variable "ipv6_cidr_block" {
  type    = string
  default = null
}

variable "ipv6_ipam_pool_id" {
  type    = string
  default = null
}

variable "ipv6_netmask_length" {
  type    = number
  default = null
}

variable "ipv6_cidr_block_network_border_group" {
  type    = string
  default = null
}

variable "enable_dns_support" {
  type    = bool
  default = true
}

variable "enable_network_address_usage_metrics" {
  type    = bool
  default = false
}

variable "enable_dns_hostnames" {
  type    = bool
  default = false
}

variable "assign_generated_ipv6_cidr_block" {
  type    = bool
  default = false
}

variable "base_tag" {
  description = "Common tags for all resources."
  type        = map(string)
}

variable "tags" {
  description = "Resource-specific tags."
  type        = map(string)
  default     = {}
}

variable "additional_cidrs" {
  description = "Additional IPv4 CIDR blocks to associate with the VPC"
  type        = list(string)
  default     = []
}