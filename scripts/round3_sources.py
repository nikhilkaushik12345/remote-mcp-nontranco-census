#!/usr/bin/env python3
"""Collect non-Tranco remote MCP candidates for the round-3 census.

Sources are deliberately independent of Tranco: the official MCP registry,
curated public lists, and static MCP directory pages.  Candidates are filtered
against the cumulative finaloauth list and prior verified hosts before probing.
"""
import csv
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "round3")
EXCLUDE = os.path.join(ROOT, "finaloauth.txt")
UA = "mcp-census/round3-sources/1.0"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

LIST_URLS = {
    "awesome_punkpeye": "https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md",
    "awesome_wong2": "https://raw.githubusercontent.com/wong2/awesome-mcp-servers/main/README.md",
    "awesome_appcypher": "https://raw.githubusercontent.com/appcypher/awesome-mcp-servers/main/README.md",
    "mcp_registry_repo": "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/README.md",
    "mcp_so": "https://mcp.so/",
    "pulse_mcp": "https://www.pulsemcp.com/servers",
}

URL_RE = re.compile(r"https?://[^\s<>\"'`()\[\]{},|]+", re.I)
BAD_HOSTS = {
    "github.com", "raw.githubusercontent.com", "npmjs.com", "pypi.org",
    "stackoverflow.com", "reddit.com", "youtube.com", "twitter.com",
}


def fetch(url, limit=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/plain,application/json,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return r.status, r.read(limit).decode("utf-8", "ignore")
    except Exception as exc:
        return 0, ""


def load_exclusions():
    out = set()
    if os.path.exists(EXCLUDE):
        with open(EXCLUDE, encoding="utf-8") as f:
            out.update(x.strip().lower().lstrip(".") for x in f if x.strip())
    for path in (
        os.path.join(ROOT, "data", "remote_mcp_servers_new.csv"),
        os.path.join(ROOT, "data", "remote_mcp_servers_round2.csv"),
    ):
        if not os.path.exists(path):
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for key in ("host", "endpoint"):
                    value = row.get(key, "")
                    if key == "endpoint":
                        value = urllib.parse.urlparse(value).hostname or ""
                    if value:
                        out.add(value.lower().rstrip("."))
    return out


def excluded(host, exclusions):
    host = host.lower().rstrip(".")
    return any(host == x or host.endswith("." + x) for x in exclusions)


def candidate_url(url):
    try:
        p = urllib.parse.urlparse(url)
        host = (p.hostname or "").lower().rstrip(".")
        if p.scheme not in ("http", "https") or not host or host in BAD_HOSTS:
            return None
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            return None
        blob = url.lower()
        if not re.search(r"(?:/mcp(?:/|$)|/sse(?:/|$)|mcp\.|modelcontextprotocol|oauth-protected-resource|streamable-http)", blob):
            return None
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path.rstrip("/") or "/", "", p.query, ""))
    except Exception:
        return None


def registry_candidates():
    rows = []
    cursor = ""
    seen_cursors = set()
    for _ in range(200):
        query = {"limit": "100"}
        if cursor:
            query["cursor"] = cursor
        url = "https://registry.modelcontextprotocol.io/v0.1/servers?" + urllib.parse.urlencode(query)
        status, body = fetch(url, limit=2_000_000)
        if status != 200:
            break
        try:
            data = json.loads(body)
        except Exception:
            break
        for item in data.get("servers", []):
            server = item.get("server") or {}
            for remote in server.get("remotes", []):
                u = remote.get("url") if isinstance(remote, dict) else ""
                if u:
                    rows.append({"url": u, "source": "official_mcp_registry", "name": server.get("name", ""), "title": server.get("title", "")})
        nxt = ((data.get("metadata") or {}).get("nextCursor") or "").strip()
        if not nxt or nxt in seen_cursors:
            break
        seen_cursors.add(nxt)
        cursor = nxt
    return rows


def list_candidates():
    rows = []
    for source, url in LIST_URLS.items():
        status, body = fetch(url)
        if not body:
            continue
        with open(os.path.join(OUT, f"source_{source}.txt"), "w", encoding="utf-8") as f:
            f.write(body)
        for raw in URL_RE.findall(body):
            u = raw.rstrip(".,;:!?\\")
            rows.append({"url": u, "source": source})
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    exclusions = load_exclusions()
    rows = registry_candidates() + list_candidates()
    filtered = []
    seen = set()
    source_counts = Counter()
    excluded_count = 0
    for row in rows:
        url = candidate_url(row.get("url", ""))
        if not url:
            continue
        host = urllib.parse.urlparse(url).hostname.lower().rstrip(".")
        if excluded(host, exclusions):
            excluded_count += 1
            continue
        key = (host, urllib.parse.urlparse(url).path or "/")
        if key in seen:
            continue
        seen.add(key)
        row = dict(row)
        row["url"] = url
        row["host"] = host
        filtered.append(row)
        source_counts[row["source"]] += 1

    with open(os.path.join(OUT, "candidates_round3.jsonl"), "w", encoding="utf-8") as f:
        for row in filtered:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(os.path.join(OUT, "candidates_round3.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(row["url"] for row in filtered) + ("\n" if filtered else ""))
    with open(os.path.join(OUT, "source_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"excluded_roots": len(exclusions), "filtered_duplicate_or_invalid": excluded_count, "candidates": len(filtered), "sources": dict(source_counts)}, f, indent=2, sort_keys=True)
    print(json.dumps({"excluded_roots": len(exclusions), "candidates": len(filtered), "sources": dict(source_counts)}, sort_keys=True))


if __name__ == "__main__":
    main()
