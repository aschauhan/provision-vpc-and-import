variable "domain_name" {
  type    = string
  default = null
}
variable "domain_name_servers" {
  type    = list(string)
  default = []
}
variable "ntp_servers" {
  type    = list(string)
  default = []
}
variable "netbios_name_servers" {
  type    = list(string)
  default = []
}
variable "netbios_node_type" {
  type    = string
  default = null
}
variable "tags" {
  type    = map(string)
  default = {}
}
variable "vpc_id" {
  type = string
}
