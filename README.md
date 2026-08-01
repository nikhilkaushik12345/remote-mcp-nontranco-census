# Remote MCP servers — non-Tranco + mass SERP census

Live-verified **new** remote MCP servers (not in prior `remote-mcp-oauth-census`).

**2,335 new servers** · **1,070 OAuth** · **732 OAuth roots** · **864 open DCR** · **1,019 public**

Generated 2026-08-01 13:08 UTC.

## Totals

| Metric | Count |
| --- | ---: |
| New verified MCP hosts | **2,335** |
| Tier A | **2,192** |
| Tier B | **143** |
| OAuth confirmed | **1,070** |
| OAuth root domains | **732** |
| Open DCR | **864** |
| Public (no auth) | **1,019** |
| Prior census excluded | 24,517 |
| Shopify storefront filtered | 1,053 |

## Discovery (not Tranco)

| Source | Servers |
| --- | ---: |
| serp_dorks | 1,096 |
| mcp_registry | 852 |
| dns_apex_spray | 342 |
| catalogs_lists | 45 |

### SERP mass dorking
- **3,037** search queries (verticals, SaaS brands, `inurl:/mcp`, `site:docs.`, OAuth/PRM dorks)
- **2,899** queries returned MCP-shaped URLs
- Engine: Browser Use V4 `/api/v4/search` (same path as prior census `serp_google.jsonl` — **no SerpAPI key was available in the environment**)

Also: MCP Registry, Cisco Umbrella, Majestic Million, `mcp.` DNS census, RFC 9728 PRM spray, Smithery/awesome lists, GitHub code search, urlscan.

## Verification
1. MCP `initialize` JSON-RPC (or MCP-shaped auth wall / JSON-RPC error)
2. OAuth: RFC 9728 PRM and/or RFC 8414 AS metadata
3. Shopify `storefront-renderer` platform endpoints filtered out

## Files
| Path | Description |
| --- | --- |
| `data/remote_mcp_servers_new.csv` | All new verified servers |
| `data/remote_mcp_oauth_new.csv` | OAuth subset |
| `data/oauth_root_domains.txt` | OAuth root domains |
| `data/removed_platform_auth.csv` | Filtered Shopify hits |
| `data/stats.json` | Stats |
| `index.html` | Searchable explorer |
| `scripts/` | Probe + SERP tools |

## License
Research dataset. Re-probe before relying on a row.
