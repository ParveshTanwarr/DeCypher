# DeCypher Synthetic Dataset

Fully synthetic dark-web-style dataset built for prototype development. No real dark-web
content, no real people, no real infrastructure — safe to use, share, and demo publicly.

**Total size:** 1,054,559 cells across 7 source tables (well over the requested 1,000,000).

## Files

| File | Rows | Columns | What it's for |
|---|---|---|---|
| `posts.csv` | 115,000 | 9 | Marketplace posts — the bulk of the dataset. Text is templated but each ground-truth actor has a consistent "writing profile" (filler word, punctuation habit, typo rate, emoji use) so real stylometric similarity signal exists between an actor's different handles. |
| `handles.csv` | 896 | 9 | One row per persona/account. Each actor has 1-3 handles; ~35% of actors have 2-3 handles simulating rebrands. |
| `actors.csv` | 600 | 7 | **Ground truth only** — the ground-truth actor identity and their writing profile. In a real system you would never have this table; it exists here so you can score your own AI model's accuracy (does it correctly re-link handles belonging to the same `actor_id`?). |
| `wallets.csv` | 1,043 | 5 | Wallet addresses per handle. ~40% of the time, an actor's wallet is deliberately reused across their own multiple handles — this is your Level 1 correlation signal. |
| `infrastructure_indicators.csv` | 250 | 8 | Level 2 data — simulated Tor misconfiguration leaks (SSL cert reuse, exposed status pages, banners) linking an actor to a clearnet domain. |
| `marketplaces.csv` | 20 | 4 | Reference table of marketplace names. |
| `trust_links.csv` | 12 | 7 | Synthetic PGP-backed trust/signature relationships between handles for graph correlation. |

## How to use this for each part of your system

- **Neo4j graph (Level 1):** Load `handles.csv` + `wallets.csv` + `trust_links.csv`. PGP fingerprints are normalized into first-class PGP key nodes; selected synthetic rebrands deliberately reuse a PGP fingerprint so the graph can demonstrate key reuse, while trust/signature relationships create additional cross-marketplace handle links. Wallet reuse remains an independent correlation signal.
- **Stylometry AI (Level 1):** Use `posts.csv`, grouped by `handle_id`. Train/test your similarity model on pairs of handles — pairs sharing the same `actor_id_ground_truth` should score high; pairs that don't should score low. `actor_id_ground_truth` is your answer key for measuring accuracy — don't feed it to the model itself.
- **Infrastructure attribution (Level 2):** Use `infrastructure_indicators.csv` as your demo data for the cert/banner leak-matching module.
- **Dashboard:** Join `handles.csv` + `posts.csv` + `wallets.csv` + `infrastructure_indicators.csv` + `trust_links.csv` on `handle_id` / `actor_id_ground_truth` for a full actor profile and relationship view.

## Important
Every value here — names, wallet addresses, PGP fingerprints, onion addresses, post text — is
randomly generated. Nothing was scraped from a real source, and nothing here corresponds to a
real system or person.
