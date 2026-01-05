import argparse
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


def _tag_value(tags: List[Dict[str, Any]], key: str) -> str:
    for t in tags or []:
        if t.get("Key") == key:
            v = (t.get("Value") or "").strip()
            if v:
                return v
    for t in tags or []:
        if (t.get("Key") or "").lower() == key.lower():
            v = (t.get("Value") or "").strip()
            if v:
                return v
    return ""


def _load_latest_discovery_json(import_dir: str) -> str:
    paths = sorted(glob.glob(os.path.join(import_dir, "vpc_resources_vpc-*_*.json")))
    if not paths:
        raise FileNotFoundError(f"No discovery JSON found under {import_dir}")
    return paths[-1]


def _parse_tfvars(tfvars_path: str) -> Dict[str, Any]:
    if not os.path.isfile(tfvars_path):
        raise FileNotFoundError(tfvars_path)

    with open(tfvars_path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    def parse_string(name: str) -> Optional[str]:
        pattern = re.compile(rf"^\s*{re.escape(name)}\s*=\s*\"([^\"]*)\"\s*$")
        for ln in lines:
            m = pattern.match(ln)
            if m:
                return m.group(1)
        return None

    def parse_list(name: str) -> List[str]:
        start_re = re.compile(rf"^\s*{re.escape(name)}\s*=\s*\[\s*$")
        end_re = re.compile(r"^\s*\]\s*$")
        in_list = False
        out: List[str] = []
        for ln in lines:
            if not in_list:
                if start_re.match(ln):
                    in_list = True
                continue
            if end_re.match(ln):
                break
            m = re.search(r"\"([^\"]+)\"", ln)
            if m:
                out.append(m.group(1))
        return out

    return {
        "environment": parse_string("environment"),
        "region": parse_string("region"),
        "vpc_name": parse_string("vpc_name"),
        "vpc_cidr": parse_string("vpc_cidr"),
        "additional_cidrs": parse_list("additional_cidrs"),
        "public_subnet_cidrs": parse_list("public_subnet_cidrs"),
        "private_subnet_cidrs": parse_list("private_subnet_cidrs"),
        "nonroutable_subnet_cidrs": parse_list("nonroutable_subnet_cidrs"),
        "azs": parse_list("azs"),
    }


def _bash_quote_single(s: str) -> str:
    # Safe single-quote for bash: close, escape, reopen
    return "'" + s.replace("'", "'\\''") + "'"


def _posix_path(path: str) -> str:
    # When running on Windows, Python may emit backslashes; bash + terraform are happier with '/'.
    return (path or "").replace("\\", "/")


def _emit_import(lines: List[str], tfvars_path: str, addr: str, import_id: str, label: str) -> None:
    # Calls bash function import_one <label> <addr> <import_id>
    lines.append(
        "import_one "
        + _bash_quote_single(label)
        + " "
        + _bash_quote_single(addr)
        + " "
        + _bash_quote_single(import_id or "")
    )


def _find_by_tag_name(items: List[Dict[str, Any]], name_value: str) -> Optional[Dict[str, Any]]:
    for it in items or []:
        if _tag_value(it.get("tags") or [], "Name") == name_value:
            return it
    return None


def _extract_nat_key_from_name(name: str) -> Optional[Tuple[str, str]]:
    # nat-public-<n>-<cidr> or nat-private-<n>-<cidr>
    m = re.match(r"^(nat-(public|private))-\d+-(.+)$", name)
    if not m:
        return None
    kind = m.group(2)
    cidr = m.group(3)
    return kind, cidr


def generate(import_dir: str, tfvars_path: str, discovery_json_path: str, out_path: str) -> None:
    with open(discovery_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tfv = _parse_tfvars(tfvars_path)
    vpc_name = tfv.get("vpc_name") or _tag_value((data.get("vpc") or {}).get("tags") or [], "Name") or "vpc"

    public_cidrs = tfv.get("public_subnet_cidrs") or []
    private_cidrs = tfv.get("private_subnet_cidrs") or []
    nonroutable_cidrs = tfv.get("nonroutable_subnet_cidrs") or []
    additional_cidrs = tfv.get("additional_cidrs") or []

    subnets = data.get("subnets") or []
    subnets_by_cidr = {s.get("cidr_block"): s for s in subnets if s.get("cidr_block") and s.get("id")}
    subnets_by_id = {s.get("id"): s for s in subnets if s.get("id")}

    cidr_assoc = {a.get("cidr_block"): a.get("association_id") for a in data.get("cidr_block_associations") or []}

    route_table_assocs = data.get("route_table_associations") or []

    # Route table ids by subnet CIDR using associations
    public_rt_id: Optional[str] = None
    private_rt_by_cidr: Dict[str, str] = {}
    nonroutable_rt_by_cidr: Dict[str, str] = {}

    for a in route_table_assocs:
        subnet_id = a.get("subnet_id")
        if not subnet_id:
            continue
        rt_id = a.get("route_table_id")
        s = subnets_by_id.get(subnet_id)
        if not s or not rt_id:
            continue
        cidr = s.get("cidr_block")
        tier = (s.get("tier") or "").lower()
        if tier == "public" and cidr in public_cidrs:
            public_rt_id = public_rt_id or rt_id
        elif tier == "private" and cidr in private_cidrs:
            private_rt_by_cidr[cidr] = rt_id
        elif tier == "nonroutable" and cidr in nonroutable_cidrs:
            nonroutable_rt_by_cidr[cidr] = rt_id

    # NACLs by Name tag (matches module naming)
    public_nacl_name = f"ntw-{vpc_name}-public-nacl"
    prn_nacl_name = f"ntw-{vpc_name}-private-nonroutable-nacl"
    nacls = data.get("network_acls") or []
    public_nacl = _find_by_tag_name(nacls, public_nacl_name)
    prn_nacl = _find_by_tag_name(nacls, prn_nacl_name)

    # NACL rule: nonroutable_10_rule is fixed in code
    prn_nacl_id = (prn_nacl or {}).get("id") or ""
    nonroutable_10_import_id = f"{prn_nacl_id}:100:-1:false" if prn_nacl_id else ""

    # IGW
    igw_id = ((data.get("internet_gateway") or {}).get("id")) or ""

    # NATs + EIPs: keyed by CIDR
    nat_public_by_key: Dict[str, Dict[str, Any]] = {}
    nat_private_by_key: Dict[str, Dict[str, Any]] = {}
    eipalloc_by_key: Dict[str, str] = {}

    for nat in data.get("nat_gateways") or []:
        nat_id = nat.get("id")
        name = _tag_value(nat.get("tags") or [], "Name")
        if not nat_id or not name:
            continue
        parsed = _extract_nat_key_from_name(name)
        if not parsed:
            continue
        kind, key_cidr = parsed
        if kind == "public" and key_cidr in private_cidrs:
            nat_public_by_key[key_cidr] = nat
            # allocation id for public NAT
            for addr in nat.get("nat_gateway_addresses") or []:
                alloc = addr.get("AllocationId")
                if alloc:
                    eipalloc_by_key[key_cidr] = alloc
                    break
        elif kind == "private" and key_cidr in nonroutable_cidrs:
            nat_private_by_key[key_cidr] = nat

    # EIPs: in JSON, id is allocation id
    eips_by_alloc = {e.get("id"): e for e in data.get("eips") or [] if e.get("id")}

    # Security group: endpoints sg
    sgs = data.get("security_groups") or []
    endpoints_sg_name = f"{vpc_name}-endpoints-sg"
    endpoints_sg = _find_by_tag_name(sgs, endpoints_sg_name)
    endpoints_sg_id = (endpoints_sg or {}).get("id") or ""

    # VPC endpoints by service suffix
    endpoints = data.get("vpc_endpoints") or []
    vpce_by_suffix: Dict[str, str] = {}
    for ep in endpoints:
        ep_id = ep.get("id")
        svc = (ep.get("service_name") or "")
        if not ep_id or not svc:
            continue
        if svc.endswith(".s3"):
            vpce_by_suffix["s3"] = ep_id
        elif svc.endswith(".ec2"):
            vpce_by_suffix["ec2"] = ep_id
        elif svc.endswith(".ssm"):
            vpce_by_suffix["ssm"] = ep_id

    # DHCP
    dhcp_id = (data.get("dhcp_options") or {}).get("id") or ""
    dhcp_assoc_id = (data.get("dhcp_options_association") or {}).get("import_id") or ""

    vpc_id = (data.get("vpc") or {}).get("id") or ""

    lines: List[str] = []
    lines.append("#!/usr/bin/env bash")
    # Don't use set -e: we want to continue importing even if one import fails.
    lines.append("set -u")
    lines.append("set -o pipefail")
    lines.append("\n# Auto-generated terraform import script")
    import_dir_posix = _posix_path(import_dir)
    discovery_posix = _posix_path(discovery_json_path)
    tfvars_posix = _posix_path(tfvars_path)

    lines.append(f"# import_dir: {import_dir_posix}")
    lines.append(f"# discovery_json: {discovery_posix}")
    lines.append(f"# tfvars: {tfvars_posix}\n")

    lines.append(f"TFVARS_FILE={_bash_quote_single(tfvars_posix)}")
    lines.append(f"DISCOVERY_JSON={_bash_quote_single(discovery_posix)}")

    backend_config = f"{import_dir_posix}/backend-config"
    lines.append(f"BACKEND_CONFIG={_bash_quote_single(backend_config)}")
    lines.append("\n")

    # Allow running the script from anywhere.
    lines.append('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
    lines.append('REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"')
    lines.append('cd "$REPO_ROOT"')
    lines.append("\n")

    # Log everything (stdout + stderr) to a timestamped log file under the import folder.
    lines.append('TS="$(date +%Y%m%d_%H%M%S)"')
    lines.append('LOG_FILE="$SCRIPT_DIR/import_${TS}.log"')
    lines.append('echo "Logging to: $LOG_FILE"')
    lines.append('exec > >(tee -a "$LOG_FILE") 2>&1')
    lines.append("\n")

    # Ensure we use the import backend before importing anything.
    lines.append('echo "Initializing Terraform backend (import backend-config)..."')
    lines.append("terraform init -reconfigure -backend-config=$BACKEND_CONFIG")
    lines.append("\n")

    lines.append("# Cache current state list (best effort)")
    lines.append('STATE_LIST_FILE="$SCRIPT_DIR/.state_list_${TS}.txt"')
    lines.append('terraform state list > "$STATE_LIST_FILE" 2>/dev/null || true')
    lines.append("\n")

    lines.append('IMPORTED=0')
    lines.append('SKIPPED=0')
    lines.append('FAILED=0')
    lines.append("\n")

    lines.append('import_one() {')
    lines.append('  local label="$1"')
    lines.append('  local addr="$2"')
    lines.append('  local id="$3"')
    lines.append('')
    lines.append('  if [[ -z "$id" ]]; then')
    lines.append('    echo "WARN: missing id for $label -> $addr"')
    lines.append('    FAILED=$((FAILED+1))')
    lines.append('    return 0')
    lines.append('  fi')
    lines.append('')
    lines.append('  if grep -Fxq -- "$addr" "$STATE_LIST_FILE" 2>/dev/null; then')
    lines.append('    echo "SKIP (already in state): $label -> $addr"')
    lines.append('    SKIPPED=$((SKIPPED+1))')
    lines.append('    return 0')
    lines.append('  fi')
    lines.append('')
    lines.append('  echo "IMPORT: $label -> $addr ($id)"')
    lines.append('  if terraform import -var-file="$TFVARS_FILE" "$addr" "$id"; then')
    lines.append('    echo "OK: $addr"')
    lines.append('    IMPORTED=$((IMPORTED+1))')
    lines.append('    echo "$addr" >> "$STATE_LIST_FILE"')
    lines.append('    return 0')
    lines.append('  else')
    lines.append('    echo "FAIL: $addr"')
    lines.append('    FAILED=$((FAILED+1))')
    lines.append('    return 0')
    lines.append('  fi')
    lines.append('}')
    lines.append("\n")

    # VPC
    _emit_import(lines, tfvars_posix, "module.vpc.aws_vpc.child_module", vpc_id, "VPC")

    # Additional CIDR associations
    for c in additional_cidrs:
        assoc_id = cidr_assoc.get(c) or ""
        addr = f'module.vpc.aws_vpc_ipv4_cidr_block_association.additional["{c}"]'
        _emit_import(lines, tfvars_posix, addr, assoc_id, f"VPC CIDR association {c}")

    # Subnets
    for cidr in public_cidrs:
        sid = (subnets_by_cidr.get(cidr) or {}).get("id") or ""
        addr = f'module.public_subnets["{cidr}"].aws_subnet.child_module'
        _emit_import(lines, tfvars_posix, addr, sid, f"public subnet {cidr}")

    for cidr in private_cidrs:
        sid = (subnets_by_cidr.get(cidr) or {}).get("id") or ""
        addr = f'module.private_subnets["{cidr}"].aws_subnet.child_module'
        _emit_import(lines, tfvars_posix, addr, sid, f"private subnet {cidr}")

    for cidr in nonroutable_cidrs:
        sid = (subnets_by_cidr.get(cidr) or {}).get("id") or ""
        addr = f'module.nonroutable_subnets["{cidr}"].aws_subnet.child_module'
        _emit_import(lines, tfvars_posix, addr, sid, f"nonroutable subnet {cidr}")

    # Gateways
    _emit_import(lines, tfvars_posix, "module.gateways.aws_internet_gateway.igw[0]", igw_id, "internet gateway")

    for cidr in sorted(private_cidrs):
        nat = nat_public_by_key.get(cidr) or {}
        nid = nat.get("id") or ""
        addr = f'module.gateways.aws_nat_gateway.public["{cidr}"]'
        _emit_import(lines, tfvars_posix, addr, nid, f"public NAT {cidr}")

        alloc = eipalloc_by_key.get(cidr) or ""
        if alloc and alloc not in eips_by_alloc:
            # still import by allocation id, even if not in eips list
            pass
        eip_addr = f'module.gateways.aws_eip.nat_eip["{cidr}"]'
        _emit_import(lines, tfvars_posix, eip_addr, alloc, f"EIP for public NAT {cidr}")

    for cidr in sorted(nonroutable_cidrs):
        nat = nat_private_by_key.get(cidr) or {}
        nid = nat.get("id") or ""
        addr = f'module.gateways.aws_nat_gateway.private["{cidr}"]'
        _emit_import(lines, tfvars_posix, addr, nid, f"private NAT {cidr}")

    # Route tables
    if public_rt_id:
        _emit_import(lines, tfvars_posix, "module.public_route_table.aws_route_table.this", public_rt_id, "public route table")

    for cidr in private_cidrs:
        rt_id = private_rt_by_cidr.get(cidr) or ""
        addr = f'module.private_route_tables["{cidr}"].aws_route_table.this'
        _emit_import(lines, tfvars_posix, addr, rt_id, f"private route table {cidr}")

    for cidr in nonroutable_cidrs:
        rt_id = nonroutable_rt_by_cidr.get(cidr) or ""
        addr = f'module.nonroutable_route_tables["{cidr}"].aws_route_table.this'
        _emit_import(lines, tfvars_posix, addr, rt_id, f"nonroutable route table {cidr}")

    # Route table associations
    if public_rt_id:
        # association idx is based on values(module.public_subnets) which is sorted by subnet keys (cidr strings)
        ordered_public = sorted(public_cidrs)
        for idx, cidr in enumerate(ordered_public):
            subnet_id = (subnets_by_cidr.get(cidr) or {}).get("id")
            assoc_id = ""
            if subnet_id:
                # aws_route_table_association import id is subnet-id/route-table-id (NOT rtbassoc-*)
                assoc_id = f"{subnet_id}/{public_rt_id}"
            addr = f'module.public_route_table.aws_route_table_association.this["{idx}"]'
            _emit_import(lines, tfvars_posix, addr, assoc_id, f"public rtb association {cidr}")

    for cidr in private_cidrs:
        rt_id = private_rt_by_cidr.get(cidr)
        subnet_id = (subnets_by_cidr.get(cidr) or {}).get("id")
        assoc_id = ""
        if rt_id and subnet_id:
            # aws_route_table_association import id is subnet-id/route-table-id (NOT rtbassoc-*)
            assoc_id = f"{subnet_id}/{rt_id}"
        addr = f'module.private_route_tables["{cidr}"].aws_route_table_association.this["0"]'
        _emit_import(lines, tfvars_posix, addr, assoc_id, f"private rtb association {cidr}")

    for cidr in nonroutable_cidrs:
        rt_id = nonroutable_rt_by_cidr.get(cidr)
        subnet_id = (subnets_by_cidr.get(cidr) or {}).get("id")
        assoc_id = ""
        if rt_id and subnet_id:
            # aws_route_table_association import id is subnet-id/route-table-id (NOT rtbassoc-*)
            assoc_id = f"{subnet_id}/{rt_id}"
        addr = f'module.nonroutable_route_tables["{cidr}"].aws_route_table_association.this["0"]'
        _emit_import(lines, tfvars_posix, addr, assoc_id, f"nonroutable rtb association {cidr}")

    # Routes (explicit resources in root)
    if public_rt_id:
        _emit_import(lines, tfvars_posix, "aws_route.public_default", f"{public_rt_id}_0.0.0.0/0", "public default route")

    for cidr in private_cidrs:
        rt_id = private_rt_by_cidr.get(cidr) or ""
        addr = f'aws_route.private_default["{cidr}"]'
        rid = f"{rt_id}_0.0.0.0/0" if rt_id else ""
        _emit_import(lines, tfvars_posix, addr, rid, f"private default route {cidr}")

    for cidr in nonroutable_cidrs:
        rt_id = nonroutable_rt_by_cidr.get(cidr) or ""
        addr = f'aws_route.nonroutable_default["{cidr}"]'
        rid = f"{rt_id}_0.0.0.0/0" if rt_id else ""
        _emit_import(lines, tfvars_posix, addr, rid, f"nonroutable default route {cidr}")

    # NACLs
    _emit_import(lines, tfvars_posix, "module.nacls.aws_network_acl.public", (public_nacl or {}).get("id") or "", "public NACL")
    _emit_import(
        lines,
        tfvars_posix,
        "module.nacls.aws_network_acl.private_nonroutable",
        prn_nacl_id,
        "private+nonroutable NACL",
    )
    _emit_import(lines, tfvars_posix, "module.nacls.aws_network_acl_rule.nonroutable_10_rule", nonroutable_10_import_id, "NACL rule nonroutable_10_rule")

    # DHCP
    _emit_import(lines, tfvars_posix, "module.dhcp_options.aws_vpc_dhcp_options.this", dhcp_id, "DHCP options")
    # aws_vpc_dhcp_options_association import id is the VPC id (NOT vpc-id/dopt-id)
    _emit_import(
        lines,
        tfvars_posix,
        "module.dhcp_options.aws_vpc_dhcp_options_association.this",
        vpc_id or dhcp_assoc_id,
        "DHCP association",
    )

    # Security group for endpoints
    _emit_import(lines, tfvars_posix, "module.vpc_endpoints_sg.aws_security_group.this", endpoints_sg_id, "VPC endpoints security group")

    # VPC endpoints
    _emit_import(lines, tfvars_posix, "module.s3_vpc_endpoint.aws_vpc_endpoint.this", vpce_by_suffix.get("s3") or "", "S3 VPC endpoint")
    _emit_import(lines, tfvars_posix, "module.ec2_vpc_endpoint.aws_vpc_endpoint.this", vpce_by_suffix.get("ec2") or "", "EC2 VPC endpoint")
    _emit_import(lines, tfvars_posix, "module.ssm_vpc_endpoint.aws_vpc_endpoint.this", vpce_by_suffix.get("ssm") or "", "SSM VPC endpoint")

    lines.append("\necho \"Done.\"\n")
    lines.append('echo "Summary: imported=$IMPORTED skipped=$SKIPPED failed=$FAILED"')
    lines.append('echo "Log: $LOG_FILE"')
    lines.append('echo ""')
    lines.append('echo "Resource summary (from terraform state):"')
    lines.append('VPC_ID=""')
    lines.append('VPC_ID=$(terraform state show -no-color module.vpc.aws_vpc.child_module 2>/dev/null | awk -F" = " \'/^[[:space:]]*id[[:space:]]*=[[:space:]]*/{gsub(/"/,"",$2); print $2; exit}\' || true)')
    lines.append('echo "VPC: ${VPC_ID:-unknown}"')
    lines.append('')
    lines.append('STATE_UNIQ_FILE="$SCRIPT_DIR/.state_list_${TS}.uniq.txt"')
    lines.append('sort -u "$STATE_LIST_FILE" > "$STATE_UNIQ_FILE" 2>/dev/null || cp "$STATE_LIST_FILE" "$STATE_UNIQ_FILE"')
    lines.append('')
    lines.append('count_re() {')
    lines.append('  local re="$1"')
    lines.append('  grep -cE "$re" "$STATE_UNIQ_FILE" 2>/dev/null || echo 0')
    lines.append('}')
    lines.append('')
    lines.append(r'SUBNETS=$(count_re "^module\\.(public|private|nonroutable)_subnets\\[\\\".*\\\"\\]\\.aws_subnet\\.child_module$")')
    lines.append(r'NACLS=$(count_re "^module\\.nacls\\.aws_network_acl\\..+$")')
    lines.append(r'ROUTE_TABLES=$(count_re "^module\\.(public_route_table|private_route_tables\\[\\\".*\\\"\\]|nonroutable_route_tables\\[\\\".*\\\"\\])\\.aws_route_table\\.this$")')
    lines.append(r'NAT_GWS=$(count_re "^module\\.gateways\\.aws_nat_gateway\\.(public|private)\\[\\\".*\\\"\\]$")')
    lines.append(r'EIPS=$(count_re "^module\\.gateways\\.aws_eip\\.nat_eip\\[\\\".*\\\"\\]$")')
    lines.append(r'IGW_COUNT=$(count_re "^module\\.gateways\\.aws_internet_gateway\\.igw\\[0\\]$")')
    lines.append(r'VPCE=$(count_re "^module\\.(s3|ec2|ssm)_vpc_endpoint\\.aws_vpc_endpoint\\.this$")')
    lines.append(r'SGS=$(count_re "^module\\.vpc_endpoints_sg\\.aws_security_group\\.this$")')
    lines.append(r'DHCP_COUNT=$(count_re "^module\\.dhcp_options\\.aws_vpc_dhcp_options\\.this$")')
    lines.append('')
    lines.append('echo "Subnets: $SUBNETS"')
    lines.append('echo "NACLs: $NACLS"')
    lines.append('echo "Route Tables: $ROUTE_TABLES"')
    lines.append('echo "NAT Gateways: $NAT_GWS"')
    lines.append('echo "EIPs: $EIPS"')
    lines.append('if [[ "$IGW_COUNT" -gt 0 ]]; then echo "IGW: yes"; else echo "IGW: no"; fi')
    lines.append('echo "VPC Endpoints: $VPCE"')
    lines.append('echo "Security Groups: $SGS"')
    lines.append('if [[ "$DHCP_COUNT" -gt 0 ]]; then echo "DHCP Options: yes"; else echo "DHCP Options: no"; fi')
    lines.append('echo "====================="')
    lines.append('TOTAL_IMPORTED=$((IMPORTED+SKIPPED))')
    lines.append('echo "Total resource imported: $TOTAL_IMPORTED"')
    lines.append('if [[ "$FAILED" -ne 0 ]]; then exit 1; fi')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate terraform import script from discovery JSON + terraform.tfvars")
    parser.add_argument(
        "import_dir",
        nargs="?",
        default=None,
        help="Import directory (env/<env>/<vpc>-import). If omitted, lists env/*/*-import.",
    )
    parser.add_argument("--tfvars", default=None, help="Path to terraform.tfvars (default: <import_dir>/terraform.tfvars)")
    parser.add_argument("--json", dest="json_path", default=None, help="Discovery JSON path (default: latest under import_dir)")
    parser.add_argument("--out", default=None, help="Output script path (default: <import_dir>/import_all.sh)")
    args = parser.parse_args()

    if not args.import_dir:
        candidates = sorted(glob.glob(os.path.join("env", "*", "*-import")))
        if not candidates:
            print("No import folders found under env/*/*-import", file=sys.stderr)
            return 1
        print("Select an import folder:")
        for i, c in enumerate(candidates, 1):
            print(f"  {i}. {c}")
        sel = input(f"Enter number [1-{len(candidates)}]: ").strip()
        try:
            idx = int(sel)
            args.import_dir = candidates[idx - 1]
        except Exception:
            print("Invalid selection", file=sys.stderr)
            return 1

    import_dir = args.import_dir
    tfvars_path = args.tfvars or os.path.join(import_dir, "terraform.tfvars")
    discovery_json_path = args.json_path or _load_latest_discovery_json(import_dir)
    out_path = args.out or os.path.join(import_dir, "import_all.sh")

    generate(import_dir, tfvars_path, discovery_json_path, out_path)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
