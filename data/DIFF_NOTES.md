# Diff vs finaloauth.txt

`finaloauth.txt` is the **cumulative OAuth root-domain allow/exclude list**.

## This pass
- Started from remote `finaloauth.txt` (**8,420** roots)
- Compared our live-verified OAuth hosts
- **577 new root domains** were not in the file → appended
- **155** OAuth roots overlapped (already had) → skipped
- File now has **8,997** roots

## Files
| Path | Meaning |
| --- | --- |
| `finaloauth.txt` | Full cumulative OAuth root list (updated) |
| `data/oauth_roots_NEW_vs_finaloauth.txt` | Only the 577 roots added this pass |
| `data/remote_mcp_oauth_NEW_vs_finaloauth.csv` | Host-level OAuth rows for those 577 roots only |

Further discovery must **exclude every root in finaloauth.txt** and only append brand-new OAuth roots to that file.
