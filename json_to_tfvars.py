import argparse
import glob
import ipaddress
import json
import os
import re
import sys


def _tag_value(tags, key: str) -> str:
	for tag in tags or []:
		if tag.get("Key") == key:
			v = (tag.get("Value") or "").strip()
			if v:
				return v
	for tag in tags or []:
		if (tag.get("Key") or "").lower() == key.lower():
			v = (tag.get("Value") or "").strip()
			if v:
				return v
	return ""


def _infer_region(discovery: dict, fallback: str = "us-east-1") -> str:
	# Prefer Region tag if present
	tags = (discovery.get("vpc") or {}).get("tags") or []
	region = _tag_value(tags, "Region")
	if region:
		return region
	# Infer from endpoint service names
	for ep in discovery.get("vpc_endpoints", []) or []:
		svc = (ep.get("service_name") or "")
		m = re.match(r"^com\\.amazonaws\\.([a-z0-9-]+)\\.", svc)
		if m:
			return m.group(1)
	return fallback


def _sorted_cidrs(cidrs):
	out = [c for c in cidrs if c]
	out = list(dict.fromkeys(out))
	try:
		out.sort(key=lambda c: (ipaddress.ip_network(c).version, int(ipaddress.ip_network(c).network_address), ipaddress.ip_network(c).prefixlen))
	except Exception:
		out.sort()
	return out


def _state_folder_name(import_folder: str, vpc_name_fallback: str) -> str:
	# Use the import folder name exactly (including -import) for backend key path.
	base = os.path.basename(os.path.normpath(import_folder))
	return (base or "").strip() or vpc_name_fallback


def _extract_tfvars_values(discovery: dict, import_folder: str) -> dict:
	vpc = discovery.get("vpc") or {}
	tags = vpc.get("tags") or []

	env = _tag_value(tags, "environment") or "dev"
	vpc_name_tag = _tag_value(tags, "Name") or _tag_value(tags, "Environment") or env
	region = _infer_region(discovery)

	vpc_cidr = vpc.get("cidr_block") or ""

	additional = []
	if isinstance(discovery.get("cidr_block_associations"), list):
		additional = [
			a.get("cidr_block")
			for a in discovery.get("cidr_block_associations") or []
			if a.get("cidr_block") and not a.get("primary")
		]
	else:
		additional = vpc.get("additional_cidrs") or []
	# Ensure the primary VPC CIDR is not treated as an additional CIDR.
	additional = [c for c in additional if c and c != vpc_cidr]
	additional = _sorted_cidrs(additional)

	subnets = discovery.get("subnets") or []
	public = _sorted_cidrs([s.get("cidr_block") for s in subnets if (s.get("tier") or "").lower() == "public"])
	private = _sorted_cidrs([s.get("cidr_block") for s in subnets if (s.get("tier") or "").lower() == "private"])
	nonroutable = _sorted_cidrs(
		[s.get("cidr_block") for s in subnets if (s.get("tier") or "").lower() == "nonroutable"]
	)

	azs = sorted({s.get("az") for s in subnets if s.get("az")})

	state_folder = _state_folder_name(import_folder, vpc_name_tag)

	return {
		"env": env,
		"region": region,
		"vpc_cidr": vpc_cidr,
		"additional_cidrs": additional,
		"public_subnet_cidrs": public,
		"private_subnet_cidrs": private,
		"nonroutable_subnet_cidrs": nonroutable,
		"azs": azs,
		"vpc_name": vpc_name_tag,
		"state_folder": state_folder,
	}


def _find_by_tag_name(items, name_value: str):
	for it in items or []:
		if _tag_value(it.get("tags") or [], "Name") == name_value:
			return it
	return None


def _to_rule_obj(entry: dict) -> dict:
	# Map EC2 describe_network_acls Entry shape to our nacl_rules object type.
	rule_number = entry.get("RuleNumber")
	protocol = entry.get("Protocol")
	rule_action = entry.get("RuleAction")
	cidr_block = entry.get("CidrBlock")
	ipv6_cidr_block = entry.get("Ipv6CidrBlock")
	port_range = entry.get("PortRange") or {}
	from_port = port_range.get("From")
	to_port = port_range.get("To")
	# If no port range is present (e.g. protocol -1), keep 0/0.
	if from_port is None:
		from_port = 0
	if to_port is None:
		to_port = 0

	out = {
		"rule_number": int(rule_number) if rule_number is not None else 0,
		"protocol": str(protocol).strip() if protocol is not None else "-1",
		"rule_action": str(rule_action).strip() if rule_action is not None else "allow",
		"from_port": int(from_port),
		"to_port": int(to_port),
	}
	if cidr_block:
		out["cidr_block"] = cidr_block
	if ipv6_cidr_block:
		out["ipv6_cidr_block"] = ipv6_cidr_block
	return out


def _extract_nacl_rules(discovery: dict, vpc_name: str) -> dict:
	# Build nacl_rules from discovery so import can bring rules into state and avoid duplicate rule_number errors.
	nacls = discovery.get("network_acls") or []
	public_nacl_name = f"ntw-{vpc_name}-public-nacl"
	prn_nacl_name = f"ntw-{vpc_name}-private-nonroutable-nacl"
	public_nacl = _find_by_tag_name(nacls, public_nacl_name)
	prn_nacl = _find_by_tag_name(nacls, prn_nacl_name)
	public_id = (public_nacl or {}).get("id")
	prn_id = (prn_nacl or {}).get("id")

	rules = discovery.get("network_acl_rules") or []

	def keep_rule(e: dict) -> bool:
		rn = e.get("RuleNumber")
		try:
			rn = int(rn)
		except Exception:
			return False
		# Skip implicit default deny rules.
		if rn == 32767:
			return False
		return True

	public_ingress = []
	public_egress = []
	private_ingress = []
	private_egress = []

	for e in rules:
		if not keep_rule(e):
			continue
		nacl_id = e.get("network_acl_id")
		if not nacl_id:
			continue
		egress = bool(e.get("Egress"))
		obj = _to_rule_obj(e)
		if public_id and nacl_id == public_id:
			(public_egress if egress else public_ingress).append(obj)
		elif prn_id and nacl_id == prn_id:
			(private_egress if egress else private_ingress).append(obj)

	# Deterministic ordering (rule_number ascending)
	public_ingress.sort(key=lambda r: r.get("rule_number", 0))
	public_egress.sort(key=lambda r: r.get("rule_number", 0))
	private_ingress.sort(key=lambda r: r.get("rule_number", 0))
	private_egress.sort(key=lambda r: r.get("rule_number", 0))

	return {
		"public_ingress": public_ingress,
		"public_egress": public_egress,
		"private_ingress": private_ingress,
		"private_egress": private_egress,
	}


def _write_backend_config(out_dir: str, env: str, state_folder: str, region: str, bucket: str, prefix: str) -> str:
	# Match repo convention: envs/<env>/<vpcname>/terraform.tfstate
	key = f"{prefix}/{env}/{state_folder}/terraform.tfstate"
	path = os.path.join(out_dir, "backend-config")
	with open(path, "w", newline="\n") as f:
		f.write(f'bucket = "{bucket}"\n')
		f.write(f'key    = "{key}"\n')
		f.write(f'region = "{region}"\n')
	return path


def _write_tfvars(discovery_path: str, out_path: str) -> dict:
	with open(discovery_path, "r") as f:
		data = json.load(f)

	out_dir = os.path.dirname(out_path)
	values = _extract_tfvars_values(data, out_dir)
	nacl_rules = _extract_nacl_rules(data, values["vpc_name"])

	with open(out_path, "w", newline="\n") as f:
		f.write("base_tag = {\n")
		f.write(f"  Region      = \"{values['region']}\"\n")
		f.write("  application = \"ntw\"\n")
		f.write(f"  environment = \"{values['env']}\"\n")
		f.write('  "created by" = "Cloud Network Team"\n')
		f.write("}\n")

		f.write(f"environment = \"{values['env']}\"\n")
		f.write(f"region      = \"{values['region']}\"\n\n")
		f.write(f"vpc_cidr = \"{values['vpc_cidr']}\"\n\n")

		f.write("additional_cidrs = [\n")
		for c in values["additional_cidrs"]:
			f.write(f"  \"{c}\",\n")
		f.write("]\n\n")

		f.write("public_subnet_cidrs = [\n")
		for c in values["public_subnet_cidrs"]:
			f.write(f"  \"{c}\",\n")
		f.write("]\n\n")

		f.write("private_subnet_cidrs = [\n")
		for c in values["private_subnet_cidrs"]:
			f.write(f"  \"{c}\",\n")
		f.write("]\n\n")

		f.write("nonroutable_subnet_cidrs = [\n")
		for c in values["nonroutable_subnet_cidrs"]:
			f.write(f"  \"{c}\",\n")
		f.write("]\n\n")

		f.write("azs = [\n")
		for az in values["azs"]:
			f.write(f"  \"{az}\",\n")
		f.write("]\n\n")

		f.write(f"vpc_name = \"{values['vpc_name']}\"\n")

		# Provisioning toggles (so import + lifecycle can be controlled via tfvars)
		f.write("\n# Provisioning toggles\n")
		f.write("enable_additional_cidrs          = true\n")
		f.write("enable_public_subnets            = true\n")
		f.write("enable_private_subnets           = true\n")
		f.write("enable_nonroutable_subnets       = true\n")
		f.write("enable_gateways                  = true\n")
		f.write("enable_internet_gateway          = true\n")
		f.write("enable_public_nat_gateways       = true\n")
		f.write("enable_private_nat_gateways      = true\n")
		f.write("enable_public_route_table        = true\n")
		f.write("enable_private_route_tables      = true\n")
		f.write("enable_nonroutable_route_tables  = true\n")
		f.write("enable_nacls                     = true\n")
		f.write("enable_public_nacl               = true\n")
		f.write("enable_private_nonroutable_nacl  = true\n")
		f.write("enable_s3_gateway_endpoint       = true\n")
		f.write("enable_interface_endpoints       = true\n")
		f.write("enable_vpc_endpoints_sg          = true\n")
		f.write("vpc_endpoints_security_group_ids = []\n")

		# NACL rules discovered from AWS (import-friendly)
		f.write("\n# NACL rules\n")
		f.write("nacl_rules = {\n")
		for key in ["public_ingress", "public_egress", "private_ingress", "private_egress"]:
			f.write(f"  {key} = [\n")
			for r in nacl_rules.get(key) or []:
				f.write("    {\n")
				f.write(f"      rule_number = {r['rule_number']}\n")
				f.write(f"      protocol    = \"{r['protocol']}\"\n")
				f.write(f"      rule_action = \"{r['rule_action']}\"\n")
				if "cidr_block" in r:
					f.write(f"      cidr_block  = \"{r['cidr_block']}\"\n")
				if "ipv6_cidr_block" in r:
					f.write(f"      ipv6_cidr_block = \"{r['ipv6_cidr_block']}\"\n")
				f.write(f"      from_port   = {r['from_port']}\n")
				f.write(f"      to_port     = {r['to_port']}\n")
				f.write("    },\n")
			f.write("  ]\n")
		f.write("}\n")

		# Optional feature-config stubs
		f.write("\n# Optional managed extras (empty by default)\n")
		f.write("security_groups        = {}\n")
		f.write("public_extra_routes    = []\n")
		f.write("private_extra_routes   = []\n")
		f.write("nonroutable_extra_routes = []\n")

	return values


def main() -> int:
	parser = argparse.ArgumentParser(description="Generate terraform.tfvars under *-import folders from discovery JSON.")
	parser.add_argument(
		"path",
		nargs="?",
		default=None,
		help="Optional: import folder path (env/.../*-import) OR a discovery json file path. If omitted, prompts.",
	)
	parser.add_argument(
		"--backend-bucket",
		default="tmo-aws-tf-state-bucket",
		help="S3 bucket to use in backend-config (default: tmo-aws-tf-state-bucket).",
	)
	parser.add_argument(
		"--backend-prefix",
		default="envs",
		help="S3 key prefix to use (default: envs).",
	)
	args = parser.parse_args()

	target_dir = os.getcwd()
	json_files = glob.glob(os.path.join(target_dir, 'env', '*', '*-import', 'vpc_resources_vpc-*.json'))
	if not json_files:
		print("No vpc_resources_vpc-*.json file found in env/*/*-import/", file=sys.stderr)
		return 1

	selected_files = []
	if args.path:
		p = args.path
		if os.path.isdir(p):
			selected_files = sorted(glob.glob(os.path.join(p, 'vpc_resources_vpc-*.json')))
			if selected_files:
				selected_files = [selected_files[-1]]
		elif os.path.isfile(p) and os.path.basename(p).startswith('vpc_resources_vpc-'):
			selected_files = [p]
		else:
			print(f"Invalid path: {p}", file=sys.stderr)
			return 1
	else:
		print("Available discovery JSON files:")
		json_files = sorted(json_files)
		for idx, jf in enumerate(json_files, 1):
			try:
				with open(jf) as f:
					jdata = json.load(f)
				vpc_tags = (jdata.get("vpc") or {}).get("tags", [])
				vpc_name = _tag_value(vpc_tags, "Name") or (jdata.get("vpc") or {}).get("id", "?")
			except Exception:
				vpc_name = "?"
			print(f"  {idx}. {jf} (VPC: {vpc_name})")

		sel = input(f"Select file(s) [1-{len(json_files)}] (comma-separated, press Enter for latest only): ").strip()
		if not sel:
			selected_files = [json_files[-1]]
		else:
			indices = [int(i) for i in sel.split(',') if i.strip().isdigit()]
			selected_files = [json_files[i-1] for i in indices if 0 < i <= len(json_files)]

	if not selected_files:
		print("No valid discovery JSON selected.", file=sys.stderr)
		return 1

	for discovery_path in selected_files:
		out_tfvars = os.path.join(os.path.dirname(discovery_path), "terraform.tfvars")
		values = _write_tfvars(discovery_path, out_tfvars)
		print(f"Wrote: {out_tfvars}")

		out_dir = os.path.dirname(discovery_path)
		backend_path = _write_backend_config(
			out_dir=out_dir,
			env=values["env"],
			state_folder=values["state_folder"],
			region=values["region"],
			bucket=args.backend_bucket,
			prefix=args.backend_prefix,
		)
		print(f"Wrote: {backend_path}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
