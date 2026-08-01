#!/usr/bin/env python3
"""Resolve mcp.<domain> via system DNS then MCP-probe hits only."""
import json, os, re, ssl, sys, socket, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA="mcp-census/mcp-sub/1.0"
TIMEOUT=4
INIT=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"sub","version":"1"}}}).encode()
CTX=ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE
PATHS=["/mcp","/","/sse","/api/mcp"]

def resolve(host):
    try:
        socket.setdefaulttimeout(2)
        infos=socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        return bool(infos)
    except Exception:
        return False

def hit(url):
    req=urllib.request.Request(url, data=INIT, method="POST", headers={
        "User-Agent":UA,"Content-Type":"application/json",
        "Accept":"application/json, text/event-stream","MCP-Protocol-Version":"2025-06-18"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
            st, body = r.status, r.read(10000).decode("utf8","ignore")
            wa = r.headers.get("WWW-Authenticate","") or ""
    except urllib.error.HTTPError as e:
        st=e.code
        try: body=e.read(10000).decode("utf8","ignore")
        except: body=""
        wa=(e.headers or {}).get("WWW-Authenticate","") or ""
    except Exception:
        return None
    if st==200 and (re.search(r"serverInfo|protocolVersion", body) or '"jsonrpc"' in body):
        return {"url":url,"status":st,"tier":"open","wa":wa[:180]}
    if st in (401,403):
        blob=(wa+" "+body[:1200]).lower()
        if "resource_metadata" in wa or "bearer" in wa.lower() or "jsonrpc" in body or re.search(r"\bmcp\b|model context", blob):
            return {"url":url,"status":st,"tier":"auth","wa":wa[:180]}
    if st in (400,405,406) and re.search(r"jsonrpc|mcp|session|accept", body[:800], re.I):
        return {"url":url,"status":st,"tier":"maybe","wa":wa[:180]}
    return None

def check(domain):
    host="mcp."+domain
    if not resolve(host):
        return domain, []
    hits=[]
    for p in PATHS:
        h=hit(f"https://{host}{p}")
        if h:
            hits.append(h); break
    return domain, hits

def main():
    infile, outfile = sys.argv[1], sys.argv[2]
    workers=int(sys.argv[3]) if len(sys.argv)>3 else 300
    start=int(sys.argv[4]) if len(sys.argv)>4 else 0
    end=int(sys.argv[5]) if len(sys.argv)>5 else 10**9
    known=set()
    if os.path.exists("data/known_hosts.txt"):
        known={l.strip().lower() for l in open("data/known_hosts.txt") if l.strip()}
    domains=[l.strip().lower() for l in open(infile) if l.strip()][start:end]
    domains=[d for d in domains if f"mcp.{d}" not in known]
    done=set()
    if os.path.exists(outfile):
        for l in open(outfile):
            try: done.add(json.loads(l).get("domain",""))
            except: pass
    todo=[d for d in domains if d not in done]
    print(f"mcp_sub domains={len(todo)} workers={workers}", flush=True)
    n=k=0; t0=time.time()
    with open(outfile,"a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(check,d) for d in todo]
        for fut in as_completed(futs):
            n+=1
            try:
                domain, hits=fut.result()
            except Exception:
                continue
            if hits:
                k+=1
                f.write(json.dumps({"domain":domain,"host":"mcp."+domain,"hits":hits})+"\n")
            if n%2000==0:
                f.flush(); rate=n/max(0.1,time.time()-t0)
                print(f"  {n}/{len(todo)} hits={k} resolved_hit_rate={k*100/n:.3f}% {rate:.0f}/s", flush=True)
    print(f"DONE n={n} hits={k}", flush=True)
if __name__=="__main__":
    main()
