variable "base_tag" {
  description = "Common tags for all resources (Region, application, vpc_name, created by)"
  type        = map(string)
}

variable "enabled" {
  description = "Master toggle for this module. When false, no NACLs or rules are created."
  type        = bool
  default     = true
}

variable "enable_public_nacl" {
  description = "If false, do not create the public NACL."
  type        = bool
  default     = true
}

variable "enable_private_nacl" {
  description = "If false, do not create the combined private/nonroutable NACL."
  type        = bool
  default     = true
}

variable "public_ingress_rules" {
  description = "Ingress rules for the public NACL."
  type = list(object({
    rule_number     = number
    protocol        = string
    rule_action     = string
    cidr_block      = optional(string)
    ipv6_cidr_block = optional(string)
    from_port       = number
    to_port         = number
  }))
  default = []
}

variable "public_egress_rules" {
  description = "Egress rules for the public NACL."
  type = list(object({
    rule_number     = number
    protocol        = string
    rule_action     = string
    cidr_block      = optional(string)
    ipv6_cidr_block = optional(string)
    from_port       = number
    to_port         = number
  }))
  default = []
}

variable "private_ingress_rules" {
  description = "Ingress rules for the private/nonroutable NACL."
  type = list(object({
    rule_number     = number
    protocol        = string
    rule_action     = string
    cidr_block      = optional(string)
    ipv6_cidr_block = optional(string)
    from_port       = number
    to_port         = number
  }))
  default = []
}

variable "private_egress_rules" {
  description = "Egress rules for the private/nonroutable NACL."
  type = list(object({
    rule_number     = number
    protocol        = string
    rule_action     = string
    cidr_block      = optional(string)
    ipv6_cidr_block = optional(string)
    from_port       = number
    to_port         = number
  }))
  default = []
}
variable "vpc_id" {
  description = "The VPC ID."
  type        = string
}
variable "public_subnet_ids" {
  description = "List of public subnet IDs."
  type        = list(string)
}
variable "private_subnet_ids" {
  description = "List of private subnet IDs."
  type        = list(string)
}
variable "nonroutable_subnet_ids" {
  description = "List of nonroutable subnet IDs."
  type        = list(string)
}
variable "vpc_name" {
  description = "Name to assign to the VPC (e.g., ntw-dev-vpc1)"
  type        = string
}

