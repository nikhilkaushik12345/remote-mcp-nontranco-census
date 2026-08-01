#!/usr/bin/env python3
"""Live-verify candidate remote MCP endpoints and their auth scheme.

Evidence collected per endpoint (no inference):
  * MCP `initialize` JSON-RPC response  -> proves it is an MCP server
  * HTTP 401 + WWW-Authenticate header  -> proves auth is required
  * /.well-known/oauth-protected-resource (RFC 9728) -> proves OAuth
  * authorization server metadata (RFC 8414) -> auth/token/registration endpoints

Usage: mcp_probe.py candidates.txt out.jsonl [workers]
"""
import json, os, re, sys, ssl, socket, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "mcp-census/1.0 (+verification probe)"
TIMEOUT = 6
PATHS = ["/mcp", "/sse", "/api/mcp", "/"]
INIT = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "census-probe", "version": "1.0"}},
}).encode()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def http(url, method="GET", data=None, headers=None, timeout=TIMEOUT):
    h = {"User-Agent": UA, "Accept": "application/json, text/event-stream",
         "Content-Type": "application/json", "MCP-Protocol-Version": "2025-06-18"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, dict(r.headers), r.read(200000).decode("utf8", "ignore")
    except urllib.error.HTTPError as e:
        try:
            body = e.read(200000).decode("utf8", "ignore")
        except Exception:
            body = ""
        return e.code, dict(e.headers or {}), body
    except Exception as e:
        return None, {"_err": type(e).__name__ + ":" + str(e)[:120]}, ""


def parse_jsonrpc(body):
    """MCP replies as plain JSON or as an SSE `data:` frame."""
    if not body:
        return None
    for chunk in ([body] + re.findall(r"data:\s*(\{.*)", body, re.S)):
        chunk = chunk.strip()
        if not chunk.startswith("{"):
            continue
        try:
            d = json.loads(chunk)
        except Exception:
            continue
        if isinstance(d, dict) and "jsonrpc" in d:
            return d
    return None


def oauth_metadata(endpoint, hdrs):
    """RFC 9728 protected-resource metadata -> RFC 8414 AS metadata."""
    from urllib.parse import urlparse, urljoin
    out = {}
    wa = hdrs.get("WWW-Authenticate") or hdrs.get("www-authenticate") or ""
    out["www_authenticate"] = wa[:400]
    urls = []
    m = re.search(r'resource_metadata="([^"]+)"', wa)
    if m:
        urls.append(m.group(1))
    p = urlparse(endpoint)
    root = f"{p.scheme}://{p.netloc}"
    path = p.path.rstrip("/")
    urls += [root + "/.well-known/oauth-protected-resource" + path,
             root + "/.well-known/oauth-protected-resource"]
    for u in dict.fromkeys(urls):
        st, h, b = http(u)
        if st == 200:
            try:
                prm = json.loads(b)
            except Exception:
                continue
            if isinstance(prm, dict) and ("authorization_servers" in prm or "resource" in prm):
                out["prm_url"] = u
                out["prm"] = {k: prm.get(k) for k in
                              ("resource", "resource_name", "authorization_servers",
                               "scopes_supported", "bearer_methods_supported")}
                as_list = [x for x in (prm.get("authorization_servers") or []) if isinstance(x, str)]
                for as_url in as_list[:1]:
                    for asm in (as_url.rstrip("/") + "/.well-known/oauth-authorization-server",
                                as_url.rstrip("/") + "/.well-known/openid-configuration"):
                        st2, _, b2 = http(asm)
                        if st2 == 200:
                            try:
                                asd = json.loads(b2)
                            except Exception:
                                continue
                            out["as_url"] = asm
                            out["as"] = {k: asd.get(k) for k in
                                         ("issuer", "authorization_endpoint", "token_endpoint",
                                          "registration_endpoint", "scopes_supported",
                                          "grant_types_supported",
                                          "code_challenge_methods_supported")}
                            break
                    if "as" in out:
                        break
                break
    # bare AS metadata even without PRM
    if "as" not in out:
        st, _, b = http(root + "/.well-known/oauth-authorization-server")
        if st == 200:
            try:
                asd = json.loads(b)
                if "authorization_endpoint" in asd:
                    out["as_url"] = root + "/.well-known/oauth-authorization-server"
                    out["as"] = {k: asd.get(k) for k in
                                 ("issuer", "authorization_endpoint", "token_endpoint",
                                  "registration_endpoint", "scopes_supported")}
            except Exception:
                pass
    return out


def classify(status, hdrs, body, rpc):
    if rpc and isinstance(rpc.get("result"), dict) and "serverInfo" in rpc["result"]:
        return "open"          # live MCP, no auth needed
    if status in (401, 403):
        return "auth_required"
    if rpc and "error" in rpc:
        return "mcp_error"     # speaks MCP but rejected our call
    if status in (400, 405, 406) and re.search(r"jsonrpc|mcp|session", body, re.I):
        return "mcp_maybe"
    return "no"


def probe_endpoint(url):
    st, h, b = http(url, method="POST", data=INIT)
    if st is None:
        return {"endpoint": url, "verdict": "unreachable", "error": h.get("_err")}
    rpc = parse_jsonrpc(b)
    verdict = classify(st, h, b, rpc)
    rec = {"endpoint": url, "status": st, "verdict": verdict,
           "server_header": h.get("Server", "")[:60],
           "content_type": (h.get("Content-Type") or "")[:60]}
    if rpc and isinstance(rpc.get("result"), dict):
        si = rpc["result"].get("serverInfo") or {}
        rec["server_name"] = si.get("name")
        rec["server_version"] = si.get("version")
        rec["protocol_version"] = rpc["result"].get("protocolVersion")
        rec["capabilities"] = sorted((rpc["result"].get("capabilities") or {}).keys())
        instr = rpc["result"].get("instructions")
        if instr:
            rec["instructions"] = instr[:300]
    if rpc and "error" in rpc:
        rec["rpc_error"] = str(rpc["error"])[:200]
    if verdict in ("auth_required", "mcp_error", "mcp_maybe", "open"):
        om = oauth_metadata(url, h)
        rec.update(om)
        if om.get("prm") or om.get("as"):
            rec["auth"] = "oauth"
        elif re.search(r"bearer", om.get("www_authenticate", ""), re.I):
            rec["auth"] = "bearer"
        elif verdict == "auth_required":
            rec["auth"] = "auth_unknown"
        elif verdict == "open":
            rec["auth"] = "none"
    return rec


def probe_target(target):
    try:
        return _probe_target(target)
    except Exception as e:
        return {"target": target, "endpoint": target if target.startswith("http") else "https://" + target,
                "verdict": "error", "error": type(e).__name__ + ":" + str(e)[:120]}


def _probe_target(target):
    """target: 'host' or full URL. Returns best record for that host."""
    cands = []
    if target.startswith("http"):
        cands.append(target)
        from urllib.parse import urlparse
        p = urlparse(target)
        cands += [f"{p.scheme}://{p.netloc}{x}" for x in PATHS]
    else:
        cands += [f"https://{target}{x}" for x in PATHS]
    seen, best = set(), None
    rank = {"open": 5, "auth_required": 4, "mcp_error": 3, "mcp_maybe": 2, "no": 1,
            "unreachable": 0}
    for c in dict.fromkeys(cands):
        if c in seen:
            continue
        seen.add(c)
        r = probe_endpoint(c)
        r["target"] = target
        if best is None or rank.get(r["verdict"], 0) > rank.get(best["verdict"], 0):
            best = r
        if r["verdict"] in ("open", "auth_required"):
            break
        if r["verdict"] == "unreachable" and c.endswith("/mcp"):
            # host itself is dead; don't burn 7 more requests
            if "NameError" in (r.get("error") or "") or "gaierror" in (r.get("error") or ""):
                break
    return best


def main():
    infile, outfile = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    targets = [l.strip() for l in open(infile) if l.strip()]
    done = set()
    if os.path.exists(outfile):
        for l in open(outfile):
            try:
                done.add(json.loads(l)["target"])
            except Exception:
                pass
    todo = [t for t in targets if t not in done]
    print(f"targets={len(targets)} done={len(done)} todo={len(todo)} workers={workers}", flush=True)
    n = 0
    hits = 0
    with open(outfile, "a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(probe_target,t) for t in todo]
        for fut in as_completed(futs):
            rec=fut.result()
            n += 1
            if rec:
                f.write(json.dumps(rec) + "\n")
                if rec.get("verdict") in ("open", "auth_required"):
                    hits += 1
            if n % 100 == 0:
                f.flush()
                print(f"  probed {n}/{len(todo)}  mcp_hits={hits}", flush=True)
    print(f"DONE probed={n} hits={hits}", flush=True)


if __name__ == "__main__":
    main()
