output "public_nacl_id" {
  value = try(aws_network_acl.public[0].id, null)
}

output "private_nonroutable_nacl_id" {
  value = try(aws_network_acl.private_nonroutable[0].id, null)
}
