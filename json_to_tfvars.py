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
		default="tmo-aws-tf-state-bucket-new-2",
		help="S3 bucket to use in backend-config (default: tmo-aws-tf-state-bucket-new-2).",
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
