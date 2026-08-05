#!/usr/bin/env python3
"""Build filtered round-3 probe inputs from registry, SERP, and Majestic."""
import csv
import json
import os
import re
import urllib.parse
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "round3")
FINALOAUTH = os.path.join(ROOT, "finaloauth.txt")
MAJESTIC = "/tmp/majestic_million.csv"
TOPN = int(os.environ.get("ROUND3_MAJESTIC_TOPN", "100000"))
URL_RE = re.compile(r"https?://[^\s<>\"'`()\[\]{},|]+", re.I)


def host_of(value):
    try:
        p = urllib.parse.urlparse(value if "://" in value else "https://" + value)
        return (p.hostname or "").lower().rstrip(".")
    except Exception:
        return ""


def excluded(host, roots):
    labels = host.split(".")
    return any(".".join(labels[i:]) in roots for i in range(len(labels)))


def valid_host(host):
    return bool(host and "." in host and not host.startswith(("localhost", "127.", "0.")))


def candidate_url(value):
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return None
    try:
        p = urllib.parse.urlparse(value.rstrip(".,;:!?\\"))
        host = (p.hostname or "").lower().rstrip(".")
        if not valid_host(host):
            return None
        if not re.search(r"(?:/mcp(?:/|$)|/sse(?:/|$)|mcp\.|modelcontextprotocol|oauth-protected-resource|streamable-http)", value, re.I):
            return None
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path.rstrip("/") or "/", "", p.query, ""))
    except Exception:
        return None


def load_roots():
    roots = set()
    with open(FINALOAUTH, encoding="utf-8") as f:
        roots.update(x.strip().lower().lstrip(".") for x in f if x.strip())
    for name in ("remote_mcp_servers_new.csv", "remote_mcp_servers_round2.csv"):
        path = os.path.join(ROOT, "data", name)
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for key in ("host", "endpoint"):
                    host = host_of(row.get(key, ""))
                    if host:
                        roots.add(host)
    return roots


def write_lines(path, values):
    with open(path, "w", encoding="utf-8") as f:
        for value in values:
            f.write(value + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    roots = load_roots()
    url_rows = []
    for path in (os.path.join(OUT, "candidates_round3.jsonl"), os.path.join(ROOT, "work", "round3", "serp_mass.jsonl")):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                values = [row.get("url", "")] + (row.get("urls") or [])
                for raw in values:
                    if isinstance(raw, str):
                        url_rows.append({"url": raw, "source": row.get("source") or "serp_dorks"})

    seen = set()
    probe_rows = []
    source_counts = Counter()
    skipped = 0
    for row in url_rows:
        url = candidate_url(row["url"])
        if not url:
            continue
        host = host_of(url)
        if excluded(host, roots):
            skipped += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        source = row["source"]
        source_counts[source] += 1
        probe_rows.append({"url": url, "host": host, "source": source})

    with open(os.path.join(OUT, "probe_candidates_round3.jsonl"), "w", encoding="utf-8") as f:
        for row in probe_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_lines(os.path.join(OUT, "probe_candidates_round3.txt"), [r["url"] for r in probe_rows])
    write_lines(os.path.join(OUT, "probe_domains_round3.txt"), sorted({r["host"] for r in probe_rows}))

    spray = []
    if os.path.exists(MAJESTIC):
        with open(MAJESTIC, newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= TOPN:
                    break
                host = host_of(row.get("Domain", ""))
                if valid_host(host) and not excluded(host, roots):
                    spray.append(host)
    spray = sorted(set(spray))
    write_lines(os.path.join(OUT, "spray_domains_round3.txt"), spray)
    stats = {
        "excluded_roots": len(roots),
        "probe_candidates": len(probe_rows),
        "probe_domains": len({r["host"] for r in probe_rows}),
        "spray_source": "majestic_million",
        "spray_topn": TOPN,
        "spray_domains": len(spray),
        "skipped_excluded_probe_rows": skipped,
        "probe_sources": dict(source_counts),
    }
    with open(os.path.join(OUT, "prepared_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, sort_keys=True)
    print(json.dumps(stats, sort_keys=True))


if __name__ == "__main__":
    main()
