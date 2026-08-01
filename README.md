# Remote MCP servers — non-Tranco discovery pass

Live-verified **new** remote Model Context Protocol servers found with the **same methodology** as
[`remote-mcp-oauth-census`](https://github.com/nikhilkaushik12345/remote-mcp-oauth-census), using
**non-Tranco** discovery sources only.

**1,115 new servers** · **414 OAuth** · **268 OAuth root domains** · **338 open DCR**

Generated 2026-08-01 12:26 UTC.

## Totals

| Metric | Count |
| --- | ---: |
| New verified MCP hosts (not in prior census) | **1,115** |
| Tier A (initialize / PRM / JSON-RPC) | **1,011** |
| Tier B (Bearer / probable) | **104** |
| OAuth confirmed (PRM and/or AS metadata) | **414** |
| OAuth root domains | **268** |
| Open Dynamic Client Registration | **338** |
| Public (no auth) | **538** |
| Prior census hosts excluded | 29,140 |
| Shopify storefront platform auth filtered | 735 |

## Discovery sources (not Tranco)

| Source | Role |
| --- | --- |
| Official MCP Registry | Full cursor pagination (63,349 records → 10,895 remote URLs); live-probed unknown hosts |
| Cisco Umbrella top-1M | Apex + `api.` `/mcp` spray on 150k domains absent from prior census |
| Majestic Million | Apex spray on 100k majestic-only domains |
| `mcp.<domain>` DNS census | 200k umbrella-unknown domains |
| RFC 9728 PRM spray | `/.well-known/oauth-protected-resource` on 50k domains |
| Smithery + awesome-mcp-servers | Catalog / README remote URL harvest |

Tranco was **not** used. Prior `remote-mcp-oauth-census` hosts (29,140) were excluded before probing.

## Verification bar (same as prior census)

1. MCP `initialize` JSON-RPC (or MCP-shaped auth wall / JSON-RPC error)
2. For OAuth: RFC 9728 PRM and/or RFC 8414/OIDC AS metadata
3. Authorization/token endpoints must be public `https://`
4. Shopify storefront-renderer platform endpoints filtered to `removed_platform_auth.csv`

## Files

| Path | Description |
| --- | --- |
| `data/remote_mcp_servers_new.csv` | All new verified servers |
| `data/remote_mcp_oauth_new.csv` | OAuth subset |
| `data/oauth_root_domains.txt` | Unique OAuth root domains |
| `data/removed_platform_auth.csv` | Filtered Shopify storefront hits |
| `data/stats.json` | Run stats |
| `index.html` | Searchable explorer |
| `scripts/` | Probe tools (`mcp_probe`, `apex_spray`, `prm_spray`, `mcp_sub_spray`) |

## By discovery source

- **mcp_registry**: 851
- **umbrella_majestic_apex**: 219
- **smithery_awesome**: 29
- **awesome_lists**: 16

## Probe coverage

- Umbrella apex: 149,994 domains → 4,501 raw hits
- Majestic apex: 99,999 domains → 1,162 raw hits
- `mcp.` DNS: 200,000 domains → 347 raw hits
- Registry remotes probed: 3,003
- Full quality re-probes: 3,126

## License / use

Research dataset. Auth posture changes; re-probe before relying on a row.
