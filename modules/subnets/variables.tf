variable "vpc_name" {
  description = "Name to assign to the VPC (e.g., ntw-dev-vpc1)"
  type        = string
  default     = null
}
variable "name" {
  description = "Name tag for the subnet."
  type        = string
  default     = null
}

variable "application" {
  description = "Application tag value."
  type        = string
  default     = null
}

variable "created_by" {
  description = "Created by tag value."
  type        = string
  default     = null
}

variable "creation_date" {
  description = "Creation date tag value."
  type        = string
  default     = null
}
variable "region" {

  type = string

  default = null

}


variable "vpc_id" {

  type = string

}

variable "cidr_block" {

  type = string

  default = null

}

variable "availability_zone" {

  type = string

  default = null

}

variable "availability_zone_id" {

  type = string

  default = null

}

variable "assign_ipv6_address_on_creation" {

  type = bool

  default = false

}

variable "customer_owned_ipv4_pool" {

  type = string

  default = null

}

variable "enable_dns64" {

  type = bool

  default = false

}

variable "enable_lni_at_device_index" {

  type = number

  default = null

}

variable "enable_resource_name_dns_aaaa_record_on_launch" {

  type = bool

  default = false

}

variable "enable_resource_name_dns_a_record_on_launch" {

  type = bool

  default = false

}

variable "ipv6_cidr_block" {

  type = string

  default = null

}

variable "ipv6_native" {

  type = bool

  default = false

}

variable "map_customer_owned_ip_on_launch" {

  type = bool

  default = false

}

variable "map_public_ip_on_launch" {

  type = bool

  default = false

}

variable "outpost_arn" {

  type = string

  default = null

}

variable "private_dns_hostname_type_on_launch" {

  type = string

  default = null

}

variable "tags" {

  type = map(string)

  default = {}

}

 