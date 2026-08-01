# MCP census round 2 (non-Tranco)

Generated 2026-08-01 20:12 UTC

## Results (new vs finaloauth.txt 9054 roots)

| Metric | Count |
| --- | ---: |
| New verified MCP hosts | **304** |
| Product (non-docs) | **261** |
| Docs MCP wrappers | **43** |
| Open (initialize OK) | **214** |
| OAuth hosts | **78** |
| **New OAuth root domains** | **73** |
| Open DCR | **59** |

## Methodology (same as prior census, not Tranco)
1. Mass SERP dorks via Browser Use V4 search (~1,666 queries)
2. Official MCP registry + Smithery/Glama/awesome lists + GitHub code search + urlscan
3. `mcp.<domain>` DNS spray on CrUX+Umbrella (~172k domains)
4. Apex `/mcp` + `api.` path spray
5. RFC 9728 PRM well-known spray
6. Live verify: MCP `initialize` JSON-RPC + OAuth PRM/AS metadata
7. Exclude every root already in `finaloauth.txt`

## Key files
- `remote_mcp_servers_round2.csv` — all new verified hosts
- `remote_mcp_oauth_round2.csv` — OAuth subset
- `oauth_roots_NEW_round2.txt` — new OAuth roots only (delta)
- `finaloauth_updated.txt` — prior + delta
- `finaloauth_delta_round2.txt` — same as oauth roots delta
