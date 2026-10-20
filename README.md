# Load/Bearing

A browser game for learning system design. Each level is an incident: you add components (load balancers, app servers, caches, replicas, CDNs, queues, shards) to a live topology, then run a 60-second load test and try to meet a latency, error-rate and budget target.

| # | Level | Concept |
|---|-------|---------|
| 1 | Hello, World | Two-tier baseline |
| 2 | Front Page | Horizontal scaling, load balancing |
| 3 | Database Meltdown | Caching, read replicas |
| 4 | Photo Wall | CDN and edge latency |
| 5 | Flash Sale | Queues and backpressure |
| 6 | Four Nines | Redundancy and failover |
| 7 | Hypergrowth | Sharding |
| ∞ | Sandbox | Your own scenario |

Play it at https://learn.siddharthranjan.app/load-bearing/index.html. This repo deploys to the `load-bearing` Vercel project on every push to `main` (built by `build.sh`), and the `learn` app rewrites `/load-bearing/*` to it. To run it locally, open `index.html` in a browser; there are no dependencies.

Articles in `blog/` are generated: edit `tools/build_blog.py` and run `python3 tools/build_blog.py`.

The simulation model lives between the `/*SIM-START*/` and `/*SIM-END*/` markers in `index.html`.
