#!/usr/bin/env python3
"""Build strict, deduplicated round-3 MCP outputs from the final re-probe."""
import csv
import json
import os
import urllib.parse
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "round3")
WORK = os.path.join(ROOT, "work", "round3")
REPROBE = os.path.join(WORK, "reprobe.jsonl")
QUEUE = os.path.join(OUT, "reprobe_candidates_round3.jsonl")
FINALOAUTH = os.path.join(ROOT, "finaloauth.txt")

FIELDS = [
    "root_domain", "host", "endpoint", "server_name", "server_version",
    "protocol_version", "verdict", "auth", "quality", "http_status",
    "dynamic_client_registration", "authorization_endpoint", "token_endpoint",
    "registration_endpoint", "issuer", "prm_url", "scopes", "is_docs_mcp",
    "source_file",
]


def host_of(value):
    try:
        p = urllib.parse.urlparse(value if "://" in value else "https://" + value)
        return (p.hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def root_of(host):
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    two_part = {
        "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au",
        "com.br", "com.cn", "com.mx", "co.in", "co.nz", "co.za", "com.tr",
        "com.sg", "com.hk", "com.ar", "com.tw", "com.pl", "com.ua", "co.jp",
    }
    return ".".join(labels[-3:]) if ".".join(labels[-2:]) in two_part else ".".join(labels[-2:])


def excluded(host, roots):
    labels = host.split(".")
    return any(".".join(labels[i:]) in roots for i in range(len(labels)))


def as_values(row):
    prm = row.get("prm") or {}
    asd = row.get("as") or {}
    scopes = prm.get("scopes_supported") or asd.get("scopes_supported") or []
    if isinstance(scopes, str):
        return scopes
    return ",".join(str(x) for x in scopes)


def strict_keep(row):
    verdict = row.get("verdict")
    if verdict == "open":
        return row.get("server_name") != "storefront-renderer"
    if verdict == "mcp_error":
        return bool(row.get("rpc_error"))
    if verdict == "auth_required":
        return bool(row.get("prm") or row.get("as") or row.get("www_authenticate"))
    return False


def main():
    before_path = os.path.join(OUT, "finaloauth_before_round3.txt")
    roots_path = before_path if os.path.exists(before_path) else FINALOAUTH
    final_roots = {x.strip().lower() for x in open(roots_path, encoding="utf-8") if x.strip()}
    exclusions = set(final_roots)
    for name in ("remote_mcp_servers_new.csv", "remote_mcp_servers_round2.csv"):
        with open(os.path.join(ROOT, "data", name), newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                for key in ("host", "endpoint"):
                    h = host_of(r.get(key, ""))
                    if h:
                        exclusions.add(h)

    sources = {}
    with open(QUEUE, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            sources[r["endpoint"]] = r.get("source", "")

    rows = []
    removed = []
    seen = set()
    verdicts = Counter()
    with open(REPROBE, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            verdicts[row.get("verdict", "")] += 1
            endpoint = row.get("endpoint", "")
            host = host_of(endpoint)
            if not strict_keep(row) or not host or excluded(host, exclusions):
                if row.get("server_name") == "storefront-renderer":
                    removed.append(row)
                continue
            if endpoint in seen:
                continue
            seen.add(endpoint)
            root = root_of(host)
            asd = row.get("as") or {}
            rec = {
                "root_domain": root,
                "host": host,
                "endpoint": endpoint,
                "server_name": row.get("server_name", ""),
                "server_version": row.get("server_version", ""),
                "protocol_version": row.get("protocol_version", ""),
                "verdict": row.get("verdict", ""),
                "auth": row.get("auth", ""),
                "quality": ("open" if row.get("verdict") == "open" else
                            "oauth" if row.get("auth") == "oauth" else
                            "bearer" if row.get("auth") == "bearer" else
                            "auth" if row.get("verdict") == "auth_required" else
                            "mcp_error"),
                "http_status": row.get("status", ""),
                "dynamic_client_registration": bool(asd.get("registration_endpoint")),
                "authorization_endpoint": asd.get("authorization_endpoint", ""),
                "token_endpoint": asd.get("token_endpoint", ""),
                "registration_endpoint": asd.get("registration_endpoint", ""),
                "issuer": asd.get("issuer", ""),
                "prm_url": row.get("prm_url", ""),
                "scopes": as_values(row),
                "is_docs_mcp": bool("/docs" in endpoint.lower() or "docs" in (row.get("server_name") or "").lower()),
                "source_file": sources.get(endpoint, ""),
            }
            rows.append(rec)

    rows.sort(key=lambda r: r["endpoint"])
    with open(os.path.join(OUT, "remote_mcp_servers_round3.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT, "remote_mcp_servers_round3.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "removed_shopify_storefront.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["endpoint", "host", "server_name", "status", "target"], lineterminator="\n")
        w.writeheader()
        for r in removed:
            w.writerow({"endpoint": r.get("endpoint", ""), "host": host_of(r.get("endpoint", "")), "server_name": r.get("server_name", ""), "status": r.get("status", ""), "target": r.get("target", "")})

    oauth_delta = sorted({r["root_domain"] for r in rows if r["auth"] == "oauth" and r["root_domain"] not in final_roots})
    with open(os.path.join(OUT, "oauth_roots_NEW_round3.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(oauth_delta) + ("\n" if oauth_delta else ""))
    merged = sorted(final_roots | set(oauth_delta))
    with open(FINALOAUTH, "w", encoding="utf-8") as f:
        f.write("\n".join(merged) + "\n")

    stats = {
        "excluded_finaloauth_roots_before": len(final_roots),
        "finaloauth_after": len(merged),
        "new_verified_hosts": len(rows),
        "new_open_hosts": sum(r["verdict"] == "open" for r in rows),
        "new_oauth_hosts": sum(r["auth"] == "oauth" for r in rows),
        "new_mcp_error_hosts": sum(r["verdict"] == "mcp_error" for r in rows),
        "new_oauth_roots": len(oauth_delta),
        "shopify_storefront_removed": len(removed),
        "strict_verdict_counts": dict(verdicts),
        "methodology": "official MCP registry + curated MCP lists + V4 SERP dorks + Majestic Million apex/mcp subdomain/RFC 9728 sprays; live MCP initialize and OAuth metadata; excludes finaloauth and prior verified hosts",
    }
    with open(os.path.join(OUT, "stats_round3.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
