# Load/Bearing

A browser game for learning system design. Each level is an incident: you add components (load balancers, app servers, caches, replicas, CDNs, queues, shards) to a live topology, then run a 60-second load test and try to meet a latency, error-rate and budget target.

| # | Level | Concept |
|---|-------|---------|
| 1 | Hello, World | Two-tier baseline |
| 2 | Front Page | Horizontal scaling, load balancing |
| 3 | Database Meltdown | Caching, read replicas |
| 4 | Thundering Herd | Cache stampedes: coalescing, TTL jitter, stale-while-revalidate |
| 5 | Stale Reads | Replication lag, read-your-own-writes routing |
| 6 | Photo Wall | CDN and edge latency |
| 7 | Flash Sale | Queues and backpressure |
| 8 | Bot Swarm | Rate limiting: algorithm and key |
| 9 | Retry Storm | Retries with backoff, idempotency keys, dead-letter queues |
| 10 | Partition Ceiling | Kafka partitions cap consumer parallelism |
| 11 | Four Nines | Redundancy and failover |
| 12 | Hypergrowth | Sharding for write capacity |
| 13 | Celebrity Shard | Shard keys, hot shards, consistent hashing |
| 14 | Fan-out | News feed push vs pull vs hybrid |
| 15 | Alert Storm | Alerting pipeline: durable ack, dedupe, correlation, dead man's switch |
| ∞ | Sandbox | Your own scenario |

Play it at https://learn.siddharthranjan.app/load-bearing. This repo deploys to the `load-bearing` Vercel project on every push to `main` (built by `build.sh`), and the `learn` app rewrites `/load-bearing/*` to it. To run it locally, open `index.html` in a browser; there are no dependencies.

Articles in `blog/` are generated: edit `tools/build_blog.py` and run `python3 tools/build_blog.py`.

The simulation model lives between the `/*SIM-START*/` and `/*SIM-END*/` markers in `index.html`.
