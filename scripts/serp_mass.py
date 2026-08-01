#!/usr/bin/env python3
"""Mass SERP dorking via V4 search gateway (same path as prior census serp_google).
Extract MCP candidate URLs from result titles/snippets/URLs.
"""
import json, os, re, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

GW = os.environ["V4_GATEWAY_URL"].rstrip("/")
TOK = os.environ["V4_RUN_TOKEN"]
URL_RE = re.compile(r"https?://[^\s\)\]\"'<>\\,|]+")
MCP_URL = re.compile(r"https?://[a-zA-Z0-9._:-]+(?:/[a-zA-Z0-9._~/-]*)?(?:/mcp|/sse|mcp\.)[a-zA-Z0-9._~/-]*", re.I)
HOST_MCP = re.compile(r"\bmcp\.[a-zA-Z0-9.-]+\.[a-z]{2,}", re.I)
_lock = threading.Lock()
_local = threading.local()

def post(query, num=10):
    body = json.dumps({"query": query, "num_results": num}).encode()
    req = urllib.request.Request(
        f"{GW}/api/v4/search",
        data=body,
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
        method="POST",
    )
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:
            time.sleep(1.5 + i * 2)
    return None

def extract(blob):
    urls = []
    if not blob:
        return urls
    text = blob if isinstance(blob, str) else json.dumps(blob)
    for u in URL_RE.findall(text):
        u = u.rstrip(".,;:)\"'")
        if re.search(r"/mcp|/sse|mcp\.|modelcontextprotocol|oauth-protected-resource", u, re.I):
            # drop github/npm noise unless path has remote endpoint
            if any(x in u.lower() for x in ("github.com", "npmjs.com", "pypi.org", "stackoverflow", "reddit.com")):
                if not re.search(r"raw\.githubusercontent|/mcp[\"']?\s*:|/mcp\b", u, re.I):
                    continue
            urls.append(u)
    for m in HOST_MCP.findall(text):
        urls.append("https://" + m.rstrip(".,"))
    # bare host patterns in text
    for m in re.findall(r"(?:https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}/(?:api/)?mcp(?:/|\b)", text):
        pass
    for m in re.findall(r"https?://[a-zA-Z0-9._:-]+/(?:api/)?mcp(?:/[a-zA-Z0-9._/-]*)?", text):
        urls.append(m.rstrip(".,;:)\"'"))
    return list(dict.fromkeys(urls))

def one(query):
    j = post(query, 12)
    rec = {"query": query, "ok": bool(j)}
    if not j:
        rec["urls"] = []
        return rec
    blob = j.get("results", "")
    rec["count"] = j.get("count")
    rec["urls"] = extract(blob)
    rec["excerpt"] = (blob if isinstance(blob, str) else json.dumps(blob))[:500]
    return rec

# Comprehensive dork set — thousands of query variants
DORKS = []

# Core protocol dorks with pagination via different engines/modifiers
base = [
    '"model context protocol" remote server https://mcp',
    '"model context protocol" "streamable http" endpoint',
    '"mcpServers" url https mcp oauth',
    '"claude mcp add" https://mcp.',
    '"claude mcp add" "https://" oauth',
    'site:docs. "MCP server" "https://" "/mcp"',
    '"oauth-protected-resource" mcp',
    '"authorization_servers" mcp resource',
    '"MCP-Protocol-Version" endpoint',
    '"protocolVersion" "2025-06-18" serverInfo mcp',
    '"serverInfo" "mcp" "initialize" https',
    'inurl:/mcp "model context"',
    'inurl:/api/mcp oauth OR bearer',
    'inurl:/.well-known/oauth-protected-resource mcp',
    '"Add to Claude" MCP https://',
    '"Add to Cursor" MCP https://mcp',
    '"Connect MCP" "https://" server',
    'mcp remote sse endpoint https',
    '"streamable-http" mcp url',
    '"type": "sse" mcp url https',
    'mcp.json "url": "https://',
    '".cursor/mcp.json" https://',
    'claude_desktop_config "mcpServers" https',
    '"remote MCP server" "https://" documentation',
    'site:developers. MCP server endpoint',
    'site:docs. "Model Context Protocol" url',
    'site:learn. MCP remote server',
    '"hosted MCP" endpoint oauth',
    '"MCP endpoint" "https://" "/mcp"',
    'filetype:json mcpServers url https',
    'filetype:md "mcpServers" "url" "https://mcp"',
    'site:github.com "url": "https://mcp." json',
    'site:github.com "mcpServers" "https://" "/mcp"',
    '"npx" "@modelcontextprotocol" remote url',
    'smithery MCP remote https',
    'glama.ai MCP remote server',
    'pulsemcp remote oauth',
    'mcp.so remote server https',
    '"works with chatgpt" mcp connector',
    'openai apps sdk mcp server https',
    'anthropic MCP connector remote',
    '"resources/list" mcp tools/list https',
    'WWW-Authenticate resource_metadata mcp',
    'RFC 9728 mcp server',
]

# Brand/vertical + MCP
verticals = [
    "crm","erp","saas","devtools","observability","security","fintech","payments",
    "banking","insurance","healthcare","ehr","legal","hr","recruiting","marketing",
    "analytics","data warehouse","etl","cdn","cloud","kubernetes","ci/cd","git",
    "ticketing","support","chat","email","calendar","storage","database","vector db",
    "search","maps","weather","news","sports","crypto","defi","nft","blockchain",
    "exchange","wallet","identity","sso","oauth","auth0","okta","supabase","firebase",
    "shopify","stripe","twilio","sendgrid","hubspot","salesforce","jira","confluence",
    "notion","slack","discord","linear","asana","monday","airtable","figma","canva",
    "vercel","netlify","cloudflare","aws","azure","gcp","datadog","sentry","pagerduty",
    "github","gitlab","bitbucket","docker","terraform","ansible","prometheus","grafana",
    "elasticsearch","mongodb","postgres","mysql","redis","kafka","snowflake","databricks",
    "bigquery","redshift","looker","tableau","powerbi","segment","mixpanel","amplitude",
    "intercom","zendesk","freshdesk","servicenow","workday","sap","oracle","adobe",
    "atlassian","microsoft","google workspace","dropbox","box","onedrive","zoom","webex",
    "spotify","youtube","twitter","linkedin","instagram","tiktok","reddit","pinterest",
    "ebay","amazon","walmart","shopify apps","woocommerce","magento","bigcommerce",
    "travel","booking","hotels","flights","real estate","mls","iot","robotics","ai agent",
]
for v in verticals:
    DORKS.append(f'{v} remote MCP server endpoint https://')
    DORKS.append(f'{v} "model context protocol" MCP oauth')
    DORKS.append(f'{v} site:docs. MCP server URL')

# Country/TLD and language variants
for tld in ["io","ai","dev","app","co","cloud","tech","so","sh","gg","to","fm","xyz","com"]:
    DORKS.append(f'"https://mcp." {tld} OAuth MCP server')
    DORKS.append(f'inurl:mcp.{tld} "initialize" OR oauth')

# Explicit host pattern harvest
for prefix in ["mcp","api","agent","ai","developer","developers","docs","platform","hooks","connect"]:
    DORKS.append(f'"{prefix}." "model context protocol" OR "/mcp" oauth endpoint')

# Company-list style: top SaaS names from a fixed list (high yield)
saas = open("corpuses/saas_brands.txt").read().splitlines() if os.path.exists("corpuses/saas_brands.txt") else []
for b in saas:
    b=b.strip()
    if not b: continue
    DORKS.append(f'{b} official remote MCP server endpoint URL')
    DORKS.append(f'{b} MCP "https://" "/mcp" OR "mcp."')

DORKS.extend(base)
if os.path.exists("corpuses/extra_dorks.txt"):
    DORKS.extend([l.strip() for l in open("corpuses/extra_dorks.txt") if l.strip()])
# dedupe preserve order
seen=set(); Q=[]
for q in DORKS:
    if q not in seen:
        seen.add(q); Q.append(q)

def main():
    outfile = sys.argv[1] if len(sys.argv)>1 else "work/serp_mass.jsonl"
    workers = int(sys.argv[2]) if len(sys.argv)>2 else 20
    start = int(sys.argv[3]) if len(sys.argv)>3 else 0
    end = int(sys.argv[4]) if len(sys.argv)>4 else len(Q)
    queries = Q[start:end]
    done=set()
    if os.path.exists(outfile):
        for line in open(outfile):
            try: done.add(json.loads(line).get("query",""))
            except: pass
    todo=[q for q in queries if q not in done]
    print(f"serp_mass total_dorks={len(Q)} shard=[{start},{end}) todo={len(todo)} workers={workers}", flush=True)
    n=hits=0
    with open(outfile,"a") as f, ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(one,q):q for q in todo}
        for fut in as_completed(futs):
            n+=1
            try: rec=fut.result()
            except Exception as e:
                rec={"query":futs[fut],"ok":False,"urls":[],"err":str(e)[:120]}
            with _lock:
                f.write(json.dumps(rec)+"\n")
                if n%25==0: f.flush()
            if rec.get("urls"): hits+=1
            if n%25==0:
                print(f"  {n}/{len(todo)} queries_with_urls={hits} last_urls={len(rec.get('urls') or [])}", flush=True)
    print(f"DONE n={n} with_urls={hits}", flush=True)

if __name__=="__main__":
    main()
