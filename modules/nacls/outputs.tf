output "public_nacl_id" {
  value = aws_network_acl.public.id
}

output "private_nonroutable_nacl_id" {
  value = aws_network_acl.private_nonroutable.id
}
