#!/usr/bin/env python3
"""Mass apex/api MCP path spray — the non-mcp.subdomain shape at internet scale.

For each domain: try https://{domain}/mcp and https://api.{domain}/mcp with
MCP initialize. Keep only protocol-shaped hits (401+Bearer/resource_metadata,
or JSON-RPC/serverInfo).
"""
import json, os, re, ssl, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "mcp-census/apex-spray/1.0"
TIMEOUT = 4
INIT = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "apex", "version": "1"}},
}).encode()
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

PATHS = ["/mcp", "/api/mcp"]  # two highest-yield paths only


def hit_url(url):
    req = urllib.request.Request(url, data=INIT, method="POST", headers={
        "User-Agent": UA, "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            st, body = r.status, r.read(12000).decode("utf8", "ignore")
            wa = r.headers.get("WWW-Authenticate", "") or ""
    except urllib.error.HTTPError as e:
        st = e.code
        try:
            body = e.read(12000).decode("utf8", "ignore")
        except Exception:
            body = ""
        wa = (e.headers or {}).get("WWW-Authenticate", "") or ""
    except Exception:
        return None
    # open MCP
    if st == 200 and (re.search(r"serverInfo|protocolVersion", body) or '"jsonrpc"' in body):
        return {"url": url, "status": st, "tier": "open", "wa": wa[:180]}
    # auth wall with MCP/OAuth signal
    if st in (401, 403):
        blob = (wa + " " + body[:1500]).lower()
        if ("resource_metadata" in wa or "bearer" in wa.lower()
                or "jsonrpc" in body or re.search(r"\bmcp\b|model context", blob)):
            return {"url": url, "status": st, "tier": "auth", "wa": wa[:180]}
    # MCP-shaped reject
    if st in (400, 405, 406) and re.search(r"jsonrpc|mcp|session|accept", body[:800], re.I):
        return {"url": url, "status": st, "tier": "maybe", "wa": wa[:180]}
    return None


def check_domain(domain):
    hits = []
    # apex
    for p in PATHS:
        h = hit_url(f"https://{domain}{p}")
        if h:
            hits.append(h)
            break
    # api. subdomain
    api = "api." + domain
    for p in PATHS:
        h = hit_url(f"https://{api}{p}")
        if h:
            hits.append(h)
            break
    return domain, hits


def main():
    infile, outfile = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 350
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    end = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
    known = set()
    if os.path.exists("data/known_hosts.txt"):
        known = {l.strip().lower() for l in open("data/known_hosts.txt") if l.strip()}
    domains = [l.strip().lower() for l in open(infile) if l.strip()][start:end]
    domains = [d for d in domains if d not in known and not d.startswith("mcp.")]
    done = set()
    if os.path.exists(outfile):
        for l in open(outfile):
            try:
                done.add(json.loads(l).get("domain", ""))
            except Exception:
                pass
    todo = [d for d in domains if d not in done]
    print(f"apex_spray domains={len(domains)} todo={len(todo)} workers={workers} shard=[{start},{end})", flush=True)
    n = k = 0
    t0 = time.time()
    with open(outfile, "a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(check_domain, d) for d in todo]
        for fut in as_completed(futs):
            n += 1
            try:
                domain, hits = fut.result()
            except Exception:
                continue
            if hits:
                k += 1
                f.write(json.dumps({"domain": domain, "hits": hits}) + "\n")
            if n % 2000 == 0:
                f.flush()
                rate = n / max(0.1, time.time() - t0)
                print(f"  {n}/{len(todo)} hits={k} ({k*100/n:.2f}%) {rate:.0f}/s", flush=True)
    print(f"DONE checked={n} hit_domains={k}", flush=True)


if __name__ == "__main__":
    main()
