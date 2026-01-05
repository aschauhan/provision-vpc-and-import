variable "vpc_id" {
  type = string
}
variable "service_name" {
  type = string
}
variable "vpc_endpoint_type" {
  type = string
}
variable "subnet_ids" {
  type    = list(string)
  default = []
}
variable "security_group_ids" {
  type    = list(string)
  default = []
}
variable "private_dns_enabled" {
  type    = bool
  default = false
}
variable "policy" {
  type    = string
  default = null
}
variable "route_table_ids" {
  type    = list(string)
  default = []
}
variable "dns_options" {
  type    = any
  default = null
}
variable "ip_address_type" {
  type    = string
  default = null
}
variable "tags" {
  type    = map(string)
  default = {}
}
