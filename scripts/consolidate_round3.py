#!/usr/bin/env python3
"""Consolidate discovery hits into a deduplicated final verification queue."""
import csv
import json
import os
import re
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "round3")
WORK = os.path.join(ROOT, "work", "round3")


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
    suffix = ".".join(labels[-2:])
    return ".".join(labels[-3:]) if suffix in two_part else suffix


def load_exclusions():
    roots = set()
    with open(os.path.join(ROOT, "finaloauth.txt"), encoding="utf-8") as f:
        roots.update(x.strip().lower().lstrip(".") for x in f if x.strip())
    for name in ("remote_mcp_servers_new.csv", "remote_mcp_servers_round2.csv"):
        with open(os.path.join(ROOT, "data", name), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for key in ("host", "endpoint"):
                    h = host_of(row.get(key, ""))
                    if h:
                        roots.add(h)
    return roots


def excluded(host, roots):
    labels = host.split(".")
    return any(".".join(labels[i:]) in roots for i in range(len(labels)))


def add(rows, endpoint, source):
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        return
    endpoint = endpoint.rstrip(".,;:!?\\\"")
    host = host_of(endpoint)
    if not host:
        return
    rows.append({"endpoint": endpoint, "host": host, "source": source})


def main():
    roots = load_exclusions()
    rows = []
    probe_path = os.path.join(WORK, "probe_candidates.jsonl")
    if os.path.exists(probe_path):
        with open(probe_path, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("verdict") in {"open", "auth_required", "mcp_error", "mcp_maybe"}:
                    add(rows, row.get("endpoint", ""), "registry_serp_curated")

    for name, source in (
        ("apex_spray.jsonl", "majestic_apex"),
        ("apex_spray_tail.jsonl", "majestic_apex"),
        ("mcp_sub_spray.jsonl", "majestic_mcp_sub"),
        ("prm_spray.jsonl", "majestic_prm"),
        ("prm_spray_tail.jsonl", "majestic_prm"),
    ):
        path = os.path.join(WORK, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                for hit in row.get("hits", []):
                    add(rows, hit.get("url", ""), source)
                    for key in ("resource",):
                        add(rows, hit.get(key, ""), source)

    unique = {}
    for row in rows:
        if excluded(row["host"], roots):
            continue
        key = row["endpoint"]
        if key in unique:
            unique[key]["source"] = ";".join(sorted(set(unique[key]["source"].split(";") + [row["source"]])))
        else:
            unique[key] = row
    final = list(unique.values())
    final.sort(key=lambda r: r["endpoint"])
    with open(os.path.join(OUT, "reprobe_candidates_round3.jsonl"), "w", encoding="utf-8") as f:
        for row in final:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "reprobe_candidates_round3.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(row["endpoint"] for row in final) + ("\n" if final else ""))
    print(json.dumps({"exclusions": len(roots), "reprobe_candidates": len(final)}, sort_keys=True))


if __name__ == "__main__":
    main()
