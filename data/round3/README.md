# MCP census round 3 (non-Tranco)

Generated 2026-08-05 18:24 UTC.

## Results

| Metric | Count |
| --- | ---: |
| New verified MCP hosts | **1,511** |
| New open hosts | **1,181** |
| New OAuth hosts | **224** |
| New JSON-RPC error hosts | **32** |
| New OAuth roots | **200** |
| Shopify `storefront-renderer` removed | **429** |
| Cumulative `finaloauth.txt` roots | **9,327** |

## Discovery

1. Official MCP Registry pagination.
2. Curated MCP lists and the MCP Registry repository.
3. Browser Use V4 SERP dorks.
4. Majestic Million top-100k apex, `api.`, and `mcp.` sprays.
5. RFC 9728 protected-resource metadata spray.

Every candidate was filtered against the 9,127-root `finaloauth.txt` snapshot and prior verified hosts before probing. Verification used MCP `initialize` JSON-RPC plus RFC 9728/RFC 8414 metadata. Generic WAF responses, ambiguous 400/405/406 responses, and Shopify storefront endpoints were excluded.

## Files

- `remote_mcp_servers_round3.csv` — strict final dataset.
- `remote_mcp_servers_round3.json` — JSON copy of the final dataset.
- `oauth_roots_NEW_round3.txt` — 200-root OAuth delta appended to `finaloauth.txt`.
- `finaloauth_before_round3.txt` — exact 9,127-root exclusion snapshot used for this pass.
- `stats_round3.json` — counts and methodology.
- `removed_shopify_storefront.csv` — excluded platform hits.
- `candidates_round3.jsonl` — registry/list discovery candidates.
- `probe_candidates_round3.jsonl` — SERP/registry verification queue.
- `reprobe_candidates_round3.jsonl` — consolidated spray and discovery queue.
