variable "vpc_id" {
  description = "The ID of the VPC to create the route table in."
  type        = string
}

variable "cidr_block" {
  description = "(Optional) The CIDR block of the route (IPv4). If omitted no route will be created unless `destination_prefix_list_id` or `ipv6_cidr_block` is set."
  type        = string
  default     = null
}

variable "ipv6_cidr_block" {
  description = "(Optional) The IPv6 CIDR block of the route."
  type        = string
  default     = null
}

variable "destination_prefix_list_id" {
  description = "(Optional) The ID of a managed prefix list destination for the route."
  type        = string
  default     = null
}

variable "carrier_gateway_id" {
  description = "(Optional) Identifier of a carrier gateway (Wavelength)."
  type        = string
  default     = null
}

variable "core_network_arn" {
  description = "(Optional) The ARN of a core network."
  type        = string
  default     = null
}

variable "egress_only_gateway_id" {
  description = "(Optional) Identifier of an Egress Only Internet Gateway."
  type        = string
  default     = null
}

variable "gateway_id" {
  description = "(Optional) Identifier of an Internet Gateway / Virtual Private Gateway."
  type        = string
  default     = null
}

variable "local_gateway_id" {
  description = "(Optional) Identifier of an Outpost local gateway."
  type        = string
  default     = null
}

variable "nat_gateway_id" {
  description = "(Optional) Identifier of a NAT Gateway."
  type        = string
  default     = null
}

variable "network_interface_id" {
  description = "(Optional) Identifier of an EC2 network interface."
  type        = string
  default     = null
}

variable "transit_gateway_id" {
  description = "(Optional) Identifier of a Transit Gateway."
  type        = string
  default     = null
}

variable "vpc_endpoint_id" {
  description = "(Optional) Identifier of a VPC endpoint."
  type        = string
  default     = null
}

variable "vpc_peering_connection_id" {
  description = "(Optional) Identifier of a VPC peering connection."
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "(Optional) List of Subnet IDs to associate this route table with."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to the route table."
  type        = map(string)
  default     = {}
}
// routing-tables module variables removed — placeholder file
// Module removed by request; keep this placeholder to avoid accidental reuse.