variable "base_tag" {
  description = "Common tags for all resources (Region, application, vpc_name, created by)"
  type        = map(string)
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

