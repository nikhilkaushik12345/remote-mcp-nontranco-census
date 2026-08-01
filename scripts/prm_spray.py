#!/usr/bin/env python3
"""PRM (RFC 9728) spray — find OAuth MCP via well-known metadata."""
import json, os, re, ssl, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

UA = "mcp-census/prm-spray/1.0"
TIMEOUT = 5
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PATHS = [
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/mcp",
    "/.well-known/oauth-protected-resource/api/mcp",
    "/mcp/.well-known/oauth-protected-resource",
    "/api/mcp/.well-known/oauth-protected-resource",
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            return r.status, r.read(50000).decode("utf8", "ignore")
    except urllib.error.HTTPError as e:
        try:
            body = e.read(20000).decode("utf8", "ignore")
        except Exception:
            body = ""
        return e.code, body
    except Exception:
        return None, ""


def looks_prm(body):
    if not body or not body.strip().startswith("{"):
        return False
    try:
        d = json.loads(body)
    except Exception:
        return False
    if not isinstance(d, dict):
        return False
    if d.get("resource") or d.get("authorization_servers") or d.get("resource_name"):
        return d
    return False


def mcpish(prm, url):
    blob = json.dumps(prm).lower() + " " + url.lower()
    return bool(re.search(r"/mcp|mcp\.|model.context|mcp\b", blob))


def check_domain(domain):
    hits = []
    hosts = [domain, f"api.{domain}", f"mcp.{domain}", f"www.{domain}"]
    for host in hosts:
        for p in PATHS:
            url = f"https://{host}{p}"
            st, body = get(url)
            if st != 200:
                continue
            prm = looks_prm(body)
            if not prm:
                continue
            if not mcpish(prm, url):
                continue
            res = prm.get("resource") or ""
            hits.append({"prm_url": url, "resource": res, "resource_name": prm.get("resource_name") or "",
                         "authorization_servers": prm.get("authorization_servers") or []})
            break
        if hits:
            break
    return domain, hits


def main():
    infile, outfile = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    end = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
    known = set()
    if os.path.exists("data/known_hosts.txt"):
        known = {l.strip().lower() for l in open("data/known_hosts.txt") if l.strip()}
    done = set()
    if os.path.exists(outfile):
        for line in open(outfile):
            try:
                done.add(json.loads(line).get("domain", ""))
            except Exception:
                pass
    domains = []
    for l in open(infile):
        d = l.strip().lower().split(",")[-1].strip() if "," in l else l.strip().lower()
        if d and d not in done:
            domains.append(d)
    domains = domains[start:end]
    print(f"prm_spray domains={len(domains)} workers={workers} shard=[{start},{end})", flush=True)
    n = hits = 0
    t0 = time.time()
    with open(outfile, "a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(check_domain, d): d for d in domains}
        for fut in as_completed(futs):
            n += 1
            try:
                domain, hs = fut.result()
            except Exception:
                domain, hs = "", []
            if hs:
                hits += 1
                f.write(json.dumps({"domain": domain, "hits": hs}) + "\n")
            if n % 2000 == 0:
                f.flush()
                rate = n / max(1e-9, time.time() - t0)
                print(f"  {n}/{len(domains)} hits={hits} ({hits*100/max(1,n):.2f}%) {rate:.0f}/s", flush=True)
    print(f"DONE checked={n} hit_domains={hits}", flush=True)


if __name__ == "__main__":
    main()
