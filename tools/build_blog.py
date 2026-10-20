#!/usr/bin/env python3
"""Generate the Field Notes blog (blog/*.html) from the posts defined below.

Run: python3 tools/build_blog.py
The generated pages are committed so the site works without a build step.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "blog"

# Level ids match LEVELS in index.html.
LEVELS = {
    "hello": (1, "Hello, World"),
    "frontpage": (2, "Front Page"),
    "meltdown": (3, "Database Meltdown"),
    "photowall": (4, "Photo Wall"),
    "flashsale": (5, "Flash Sale"),
    "nines": (6, "Four Nines"),
    "hypergrowth": (7, "Hypergrowth"),
}

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800'
         '&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">')


def diagram(cols, caption):
    """cols: list of columns; each column is a list of (tag, sub, hot) boxes. Draws all-to-all arrows between neighbours."""
    bw, bh, gx, gy, pad = 112, 50, 52, 14, 8
    heights = [len(c) * bh + (len(c) - 1) * gy for c in cols]
    H = max(heights) + pad * 2
    W = len(cols) * bw + (len(cols) - 1) * gx + pad * 2
    pos = []
    for i, col in enumerate(cols):
        x = pad + i * (bw + gx)
        y0 = (H - heights[i]) / 2
        pos.append([(x, y0 + j * (bh + gy)) for j in range(len(col))])
    parts = [f'<svg class="dg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(caption)}">']
    for i in range(len(cols) - 1):
        for (ax, ay) in pos[i]:
            for (bx, by) in pos[i + 1]:
                x1, y1, x2, y2 = ax + bw, ay + bh / 2, bx - 6, by + bh / 2
                mx = (x1 + x2) / 2
                parts.append(f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}"/>')
                parts.append(f'<polygon class="head" points="{x2},{y2 - 4} {x2 + 6},{y2} {x2},{y2 + 4}"/>')
    for i, col in enumerate(cols):
        for (tag, sub, hot), (x, y) in zip(col, pos[i]):
            parts.append(f'<g class="{"hot" if hot else ""}"><rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="5"/>'
                         f'<text class="tag" x="{x + bw / 2}" y="{y + 22}" text-anchor="middle">{html.escape(tag)}</text>'
                         f'<text class="sub" x="{x + bw / 2}" y="{y + 38}" text-anchor="middle">{html.escape(sub)}</text></g>')
    parts.append("</svg>")
    return f'<figure><div class="dgw">{"".join(parts)}</div><figcaption>{caption}</figcaption></figure>'


def table(head, rows, numeric=()):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f'<td class="n">{c}</td>' if i in numeric else f"<td>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


B = lambda *n: (n[0], n[1] if len(n) > 1 else "", n[2] if len(n) > 2 else False)

POSTS = [
# ---------------------------------------------------------------------------
dict(slug="estimation", short="Estimation", title="Back-of-the-envelope estimation",
     dek="Before you draw a single box, work out how much traffic, data and bandwidth you are designing for.",
     levels=["hello", "frontpage", "flashsale"], practice="hello",
     body=f"""
<p>A design for 100 requests per second and a design for 100,000 requests per second look nothing alike. The first fits on one server. The second needs load balancers, caches, replicas and probably shards. So the first five minutes of any design should go to arithmetic, not architecture.</p>
<p>You don't need precision. You need the right order of magnitude, so you know whether a component is comfortable, close to its limit, or hopeless.</p>

<h2>From users to requests per second</h2>
<p>Start from people and work toward machines. The formula almost every estimate uses:</p>
<div class="math">average RPS = daily active users × actions per user per day ÷ 86,400
peak RPS    = average RPS × peak factor (usually 2–10×)</div>
<p>There are 86,400 seconds in a day. Round it to 100,000 and the mental math gets easy: <strong>one million requests a day is about 12 per second</strong>, and one billion a day is about 12,000 per second.</p>

<h3>A worked example</h3>
<p>Say you're designing a photo feed with 10 million daily users. Each user loads about 20 feed pages and posts 2 photos a day.</p>
{table(["Quantity", "Math", "Result"], [
    ["Reads per day", "10M × 20", "200M"],
    ["Average read RPS", "200M ÷ 86,400", "≈ 2,300/s"],
    ["Peak read RPS (×3)", "2,300 × 3", "≈ 7,000/s"],
    ["Writes per day", "10M × 2", "20M"],
    ["Peak write RPS (×3)", "20M ÷ 86,400 × 3", "≈ 700/s"],
], numeric=(2,))}
<p>Two facts fall out straight away. The system is read-heavy (10:1), so caching and read replicas will matter more than write scaling. And 700 writes per second is within reach of one well-tuned database, so you probably don't need sharding on day one.</p>

<h2>Storage and bandwidth</h2>
<p>The same arithmetic sizes your disks and your network. If each photo record is 1 KB of metadata and the image itself is 500 KB:</p>
<div class="math">metadata: 20M writes/day × 1 KB   = 20 GB/day   ≈ 7 TB/year
images:   20M writes/day × 500 KB = 10 TB/day   ≈ 3.6 PB/year
egress:   7,000 reads/s × 50 KB thumbnail ≈ 350 MB/s ≈ 2.8 Gbit/s</div>
<p>Now you know the images belong in object storage behind a CDN, not in the database, and that serving them from your own servers would need serious network capacity.</p>

<h2>Numbers worth memorising</h2>
<p>These are rounded orders of magnitude. Real hardware varies, but the ratios between rows are what matter.</p>
{table(["Operation", "Rough time"], [
    ["Read from main memory", "100 ns"],
    ["Random read from SSD", "~100 µs"],
    ["Round trip inside a data centre", "~0.5 ms"],
    ["Cache GET over the network (Redis, Memcached)", "~1 ms"],
    ["Indexed database query", "1–10 ms"],
    ["Round trip, US East ↔ Europe", "~80 ms"],
    ["Round trip, US ↔ Australia", "~150–200 ms"],
], numeric=(1,))}
<p>Memory is about 1,000 times faster than SSD, and SSD is far faster than going across the planet. That one ratio explains why caches and CDNs exist.</p>

<h2>Capacity of common building blocks</h2>
<p>Ballpark throughput for one node of each, assuming simple requests:</p>
<ul>
<li><strong>Web or app server:</strong> hundreds to a few thousand requests per second, depending on how much work each request does.</li>
<li><strong>Relational database (PostgreSQL, MySQL):</strong> thousands to tens of thousands of simple indexed queries per second. Writes are more expensive than reads.</li>
<li><strong>In-memory cache (Redis):</strong> on the order of 100,000 operations per second.</li>
<li><strong>Message broker partition (Kafka):</strong> tens of megabytes per second.</li>
</ul>

<h2>Averages lie: think in percentiles</h2>
<p>If 99 requests take 10 ms and one takes 2 seconds, the average is about 30 ms, which describes nobody's experience. Percentiles describe it better. <strong>p95</strong> is the latency 95% of requests beat, and <strong>p99</strong> is the latency 99% beat. A page that makes 20 backend calls hits the p95 of at least one of them most of the time, so the tail is what users feel.</p>

<h2>Leave headroom</h2>
<p>Never size a component to run at 100% at peak. Response time climbs steeply as utilisation approaches 1 (see <a href="load-balancing.html">load balancing</a> for the math). A common target is 60–75% at expected peak, which leaves room for spikes and for losing a machine.</p>

<div class="note"><p><strong>In the game:</strong> one app server handles 1,000 req/s and one database handles 1,500 reads/s and 600 writes/s. The level brief gives you peak traffic and the read share, so you can do the same arithmetic before placing anything. In <em>Flash Sale</em>, comparing peak writes (~950/s) with average writes (under 500/s) is the whole puzzle.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>State daily active users and actions per user, then derive average and peak RPS.</li>
<li>Split reads from writes and state the ratio.</li>
<li>Estimate storage per year and egress bandwidth.</li>
<li>Name which component the numbers stress first.</li>
<li>Round aggressively and say you're rounding.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="load-balancing", short="Load balancing", title="Load balancing and horizontal scaling",
     dek="Add machines instead of buying bigger ones, and put something in front that spreads the work and routes around failures.",
     levels=["frontpage", "nines"], practice="frontpage",
     body=f"""
<p>When one server can't keep up, you have two options. <strong>Vertical scaling</strong> means a bigger machine: more cores, more memory. It's simple and needs no code changes, but it has a ceiling, gets expensive fast, and leaves you with one machine that can take everything down.</p>
<p><strong>Horizontal scaling</strong> means more machines of the same size. It has no hard ceiling and gives you redundancy for free, but it needs two things: application servers that keep no local state, and a load balancer to spread requests between them.</p>

{diagram([[B("USERS", "clients")], [B("LB", "health checks", True)], [B("APP 1", "stateless"), B("APP 2", "stateless"), B("APP 3", "stateless")], [B("DB", "shared state")]],
         "A load balancer spreads requests across identical, stateless app servers. Shared state lives in the database.")}

<h2>Stateless first</h2>
<p>A server is stateless when it keeps nothing between requests that another server would need. Sessions go in a shared store (Redis, the database, or a signed cookie), and uploads go to object storage. If any server can answer any request, adding capacity is as simple as starting another copy.</p>
<p>The alternative, <strong>sticky sessions</strong>, pins each user to one server. It works, but load becomes uneven, and when that server dies its users lose their sessions.</p>

<h2>Layer 4 vs layer 7</h2>
{table(["", "Layer 4 (transport)", "Layer 7 (application)"], [
    ["Sees", "IP addresses and ports", "HTTP method, path, headers, cookies"],
    ["Can route by", "Connection", "URL, host, header, user"],
    ["Cost", "Very cheap, very fast", "Terminates TLS and parses HTTP"],
    ["Examples", "AWS NLB, IPVS", "NGINX, Envoy, HAProxy, AWS ALB"],
])}
<p>Most web systems use an L7 balancer because it can send <code>/api</code> and <code>/static</code> to different pools, retry idempotent requests, and terminate TLS in one place.</p>

<h2>Choosing a server</h2>
<ul>
<li><strong>Round robin:</strong> each server in turn. Fine when requests cost about the same.</li>
<li><strong>Weighted round robin:</strong> bigger servers get a bigger share.</li>
<li><strong>Least connections:</strong> pick the server with the fewest requests in flight. Better when request cost varies a lot.</li>
<li><strong>Power of two choices:</strong> pick two servers at random and send to the less busy one. Nearly as good as least connections and much cheaper to run at scale.</li>
<li><strong>Hashing (IP or key):</strong> the same client always lands on the same server. Useful for caches, but it rebalances badly unless you use <a href="sharding.html">consistent hashing</a>.</li>
</ul>

<h2>Health checks</h2>
<p>The load balancer probes each server, for example with <code>GET /healthz</code> every few seconds, and stops sending traffic after a few failures in a row. This is what turns a crashed server from an outage into a small loss of capacity. Make the check meaningful but cheap. If it calls the database, a slow database can mark every server unhealthy at once.</p>

<h2>Why 95% busy is too busy</h2>
<p>Requests don't arrive evenly. When a server is busy, new requests wait in line. Basic queueing theory (an M/M/1 queue) gives the average time in the system as:</p>
<div class="math">response time ≈ service time ÷ (1 − utilisation)</div>
{table(["Utilisation", "Response time vs idle"], [["50%", "2×"], ["75%", "4×"], ["80%", "5×"], ["90%", "10×"], ["95%", "20×"]], numeric=(0, 1))}
<p>A server at 95% is technically keeping up, but every request takes 20 times longer than it would on an idle machine. That's why capacity plans aim for 60–75% at peak. A related rule, <strong>Little's law</strong> (<code>L = λW</code>), says requests in flight equal arrival rate times time in the system. As latency climbs, so do open connections and memory use.</p>

<h2>Don't make the load balancer the new single point of failure</h2>
<p>Run load balancers in pairs with a floating IP, or use a managed service that is redundant across zones. At global scale, DNS or anycast spreads users across load balancers in several regions.</p>

<h2>Autoscaling</h2>
<p>Horizontal scaling also lets you add and remove servers automatically, based on CPU, request rate or queue depth. Scale out early and scale in slowly: a new instance takes time to boot and warm up, and scaling in too eagerly makes capacity flap up and down.</p>

<div class="note"><p><strong>In the game:</strong> without a load balancer, only APP 1 gets traffic, however many servers you add. Each app server's latency follows the 1 ÷ (1 − ρ) curve. In <em>Front Page</em>, two servers run at 75% at peak and respond four times slower than idle; three run at 50%. In <em>Four Nines</em>, the health check is what saves you when APP 1 crashes.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Say the app tier is stateless and where sessions live.</li>
<li>Pick L4 or L7 and give a reason.</li>
<li>Name the balancing algorithm and the health check.</li>
<li>Size for 60–75% utilisation at peak, plus one spare server (N+1).</li>
<li>Make the load balancer itself redundant.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="caching", short="Caching", title="Caching",
     dek="Keep the answers to popular questions in memory so the database only sees the questions nobody asked recently.",
     levels=["meltdown", "flashsale", "nines", "hypergrowth"], practice="meltdown",
     body=f"""
<p>Most systems are read-heavy, and most reads ask for the same small set of things: the front page, a popular product, a celebrity's profile. A cache keeps those answers somewhere faster than the database, usually in memory, so a repeat question costs about a millisecond and puts no load on the database.</p>

<h2>Where caches live</h2>
<p>Caching happens at every layer, from the user's device to the disk:</p>
<ul>
<li><strong>Browser cache:</strong> controlled by HTTP headers. It's free and the fastest, but you can't purge it.</li>
<li><strong>CDN:</strong> shared edge caches near users, mostly for static files. See <a href="cdn.html">CDNs</a>.</li>
<li><strong>In-process cache:</strong> a map inside each app server. No network hop, but every server has its own copy and they drift apart.</li>
<li><strong>Distributed cache:</strong> Redis or Memcached, shared by every app server. This is what people usually mean by "add a cache".</li>
<li><strong>Database buffer pool:</strong> the database caches hot pages in RAM on its own.</li>
</ul>

{diagram([[B("APP", "server")], [B("CACHE", "~1 ms · hit", True), B("DB", "~10 ms · miss")]],
         "Cache-aside: the app asks the cache first and only queries the database on a miss, then stores the result.")}

<h2>Read and write patterns</h2>
{table(["Pattern", "How it works", "Good for"], [
    ["<strong>Cache-aside</strong> (lazy loading)", "The app reads the cache. On a miss it reads the DB and writes the result into the cache.", "The default. Only caches what's actually requested."],
    ["<strong>Read-through</strong>", "The cache library loads from the DB itself on a miss.", "Same as cache-aside, with less app code."],
    ["<strong>Write-through</strong>", "Every write goes to the cache and the DB together.", "Data that's read right after it's written."],
    ["<strong>Write-behind</strong> (write-back)", "Writes go to the cache and are flushed to the DB later.", "Very high write rates, if you accept losing data when the cache dies."],
    ["<strong>Write-around</strong>", "Writes go straight to the DB. The cache fills on the next read.", "Data written once and rarely read."],
])}

<h2>Hit rate is everything</h2>
<p>If <code>h</code> is the hit rate, the share of requests reaching the database is <code>1 − h</code>. That makes the last few percent worth far more than they look:</p>
<div class="math">hit rate 80% → DB sees 20% of reads
hit rate 90% → DB sees 10%   (half the load of 80%)
hit rate 99% → DB sees 1%    (a tenth of the load of 90%)

average latency = h × t_cache + (1 − h) × t_db</div>
<p>Hit rate rises with cache size, longer TTLs and skewed popularity. Real workloads usually follow a power law, so a cache holding the top 1% of keys can serve most of the traffic.</p>

<h2>Eviction</h2>
<p>Memory runs out, so something has to go. <strong>LRU</strong> (least recently used) is the common default. <strong>LFU</strong> (least frequently used) protects items that are always popular from a burst of one-off reads. A <strong>TTL</strong> on each key bounds how stale data can get, even if you forget to invalidate it.</p>

<h2>Invalidation, the hard part</h2>
<p>A cache is a copy, and copies go stale. Common strategies:</p>
<ul>
<li><strong>TTL only:</strong> accept data up to N seconds old. Simple and often good enough.</li>
<li><strong>Delete on write:</strong> after updating the database, delete the cache key so the next read reloads it. Delete rather than update. Updating the cache from two concurrent writers can leave the older value in place.</li>
<li><strong>Versioned keys:</strong> put a version in the key (<code>user:42:v7</code>), so a change creates a new key and the old one ages out.</li>
</ul>

<h2>Failure modes to plan for</h2>
<ul>
<li><strong>Cache stampede:</strong> a hot key expires and a thousand requests miss at once, all hitting the database. Fix it with request coalescing (one request reloads while the others wait), random jitter on TTLs, or serving stale data while one request refreshes in the background.</li>
<li><strong>Hot keys:</strong> one key gets so much traffic that its cache node saturates. Replicate it to several nodes or keep a small in-process copy.</li>
<li><strong>Cold start:</strong> after a restart the hit rate is zero, and a database sized for 10% of reads suddenly sees 100%. Warm caches gradually, or keep enough database capacity to survive a cold cache.</li>
</ul>

<div class="note"><p><strong>In the game:</strong> each level sets a hit rate (85% in <em>Database Meltdown</em>). Adding the cache multiplies the reads reaching your database by 1 − hit rate. One cache costs less than one read replica and removes far more load, which is why it's the cheaper way through that level.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Say what you're caching, where, and with which pattern (usually cache-aside).</li>
<li>Estimate the hit rate and the database load that's left.</li>
<li>Choose a TTL and an invalidation strategy.</li>
<li>Mention stampede protection for hot keys.</li>
<li>Say what happens if the cache is empty or down.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="replication", short="Replication", title="Database replication",
     dek="Copies of your database give you more read capacity and a standby for when the primary dies. They cost consistency.",
     levels=["meltdown", "nines"], practice="nines",
     body=f"""
<p>Replication keeps the same data on several machines. It serves two goals that are easy to mix up: <strong>scaling reads</strong> (more machines can answer queries) and <strong>availability</strong> (if one machine dies, another has the data). It does nothing for write throughput, because every copy has to apply every write.</p>

{diagram([[B("APP", "reads + writes")], [B("PRIMARY", "all writes", True)], [B("REPLICA 1", "reads"), B("REPLICA 2", "reads")]],
         "Leader–follower replication: writes go to the primary, which streams its changes to read-only replicas.")}

<h2>Leader–follower</h2>
<p>This is the most common setup (PostgreSQL streaming replication, MySQL replication, and managed services such as RDS and Cloud SQL). One node, the <strong>primary</strong> or leader, accepts writes. It records every change in a log, and the <strong>replicas</strong> (followers) replay that log. The app sends writes to the primary and spreads reads across the replicas.</p>

<h2>Synchronous or asynchronous</h2>
{table(["Mode", "The primary confirms a write after…", "Trade-off"], [
    ["Asynchronous", "it's written locally", "Fast. A replica can be seconds behind, and failover can lose the last writes."],
    ["Synchronous", "every replica has it", "No data loss, but one slow replica slows every write."],
    ["Semi-synchronous", "at least one replica has it", "The usual compromise: one up-to-date standby, the rest async."],
])}

<h2>Replication lag and its bugs</h2>
<p>With async replication, a replica is always a little behind, usually milliseconds and sometimes seconds under load. That causes some classic bugs:</p>
<ul>
<li><strong>Not seeing your own write:</strong> a user edits their profile and refreshes. The read goes to a lagging replica and shows the old version. Fix: read from the primary for a short window after a user writes, or pin that user's reads to the primary.</li>
<li><strong>Going back in time:</strong> two refreshes hit two replicas with different lag, and a comment appears, then disappears. Fix: keep each user on the same replica.</li>
<li><strong>Effects without causes:</strong> a reader sees a reply before the message it replies to. Fix: keep related writes on one partition, or track causality.</li>
</ul>

<h2>Failover</h2>
<p>When the primary dies, a replica has to be promoted:</p>
<ol>
<li><strong>Detect</strong> the failure, usually after several missed heartbeats. Too eager and you fail over on a network blip; too slow and the outage lasts longer.</li>
<li><strong>Choose</strong> the most up-to-date replica.</li>
<li><strong>Promote</strong> it and point writers at it, through DNS, a proxy or service discovery.</li>
<li><strong>Fence</strong> the old primary so that if it comes back, it can't accept writes too. Two nodes that both think they're primary is called <strong>split brain</strong>, and it corrupts data.</li>
</ol>
<p>Two numbers describe how good your failover is. <strong>RTO</strong> (recovery time objective) is how long writes are unavailable. <strong>RPO</strong> (recovery point objective) is how much recent data you can lose. Async replication has an RPO above zero.</p>

<h2>Beyond one leader</h2>
<ul>
<li><strong>Multi-leader:</strong> several nodes, often one per region, accept writes. Writes are fast locally, but concurrent edits conflict and need resolving.</li>
<li><strong>Leaderless</strong> (Dynamo-style, as in Cassandra): write to W of N replicas and read from R of them. If <code>W + R &gt; N</code>, every read overlaps at least one replica holding the latest write.</li>
</ul>

<h2>Replicas or a cache?</h2>
<p>Both reduce load on the primary. A cache is cheaper per read served and faster, but it only helps with repeated reads and needs invalidation. Replicas handle any query, including ad-hoc and analytical ones, and double as failover standbys, but each one costs as much as a database. Many systems use both.</p>

<div class="note"><p><strong>In the game:</strong> each replica adds 1,500 reads/s. In <em>Four Nines</em>, the primary dies at 38 s. With a replica, you lose 2 seconds of writes while it's promoted. Without one, every database request fails for 12 seconds.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Say whether replication is there to scale reads, for availability, or both.</li>
<li>Choose sync, async or semi-sync and state the RPO.</li>
<li>Handle reading your own writes.</li>
<li>Describe failover detection, promotion and fencing.</li>
<li>Remember that replicas don't scale writes.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="cdn", short="CDNs", title="CDNs and edge caching",
     dek="You can't make light faster, but you can shorten the distance by serving bytes from a city near each user.",
     levels=["photowall", "hypergrowth"], practice="photowall",
     body=f"""
<p>A content delivery network is a fleet of caching servers, called points of presence (PoPs), spread across hundreds of cities. A user's request goes to a nearby PoP. If that PoP has the file, it answers in a few milliseconds. If not, it fetches the file from your <strong>origin</strong> once, stores it, and serves everyone nearby from then on.</p>

{diagram([[B("USER", "Sydney")], [B("EDGE PoP", "Sydney · ~10 ms", True)], [B("SHIELD", "regional")], [B("ORIGIN", "Virginia")]],
         "On a hit, the edge answers locally. On a miss, it asks a regional shield cache, and only then the origin.")}

<h2>Physics sets the floor</h2>
<p>Light in optical fibre travels at about 200,000 km per second, roughly two-thirds of its speed in a vacuum. That works out to about <strong>1 ms of round-trip time per 100 km</strong>, before routers and indirect cable paths add more.</p>
{table(["Route", "Distance", "Best-case RTT", "Typical RTT"], [
    ["New York ↔ London", "5,600 km", "56 ms", "70–80 ms"],
    ["San Francisco ↔ Tokyo", "8,300 km", "83 ms", "100–120 ms"],
    ["London ↔ Sydney", "17,000 km", "170 ms", "250+ ms"],
], numeric=(1, 2, 3))}
<p>A new HTTPS connection costs several round trips before the first byte arrives (TCP handshake plus TLS handshake). From Sydney to an origin in Virginia that's half a second of waiting, and no amount of server capacity fixes it. Only distance does.</p>

<h2>What CDNs serve</h2>
<ul>
<li><strong>Static assets:</strong> images, video, JavaScript, CSS and fonts. These are often 80–95% of requests and most of the bytes.</li>
<li><strong>Cacheable API responses:</strong> public, rarely changing data such as product catalogues or a public timeline, with short TTLs.</li>
<li><strong>Dynamic acceleration:</strong> even uncacheable requests get faster. TLS ends at the nearby edge, and the edge keeps warm, pooled connections back to the origin.</li>
</ul>

<h2>Controlling the cache with headers</h2>
<div class="math">Cache-Control: public, max-age=31536000, immutable      # hashed assets
Cache-Control: public, max-age=60, stale-while-revalidate=300   # semi-fresh API
Cache-Control: private, no-store                               # per-user data</div>
<ul>
<li><code>max-age</code> is the browser TTL; <code>s-maxage</code> overrides it for shared caches like CDNs.</li>
<li><code>stale-while-revalidate</code> serves the old copy instantly while fetching a fresh one in the background.</li>
<li><code>Vary</code> lists the request headers that change the response. Vary on too much and the hit rate collapses.</li>
</ul>

<h2>Cache busting beats invalidation</h2>
<p>Purging a file from hundreds of PoPs is slow and sometimes incomplete. The better pattern is <strong>content-hashed filenames</strong>: <code>app.3f9a1c.js</code> can be cached forever, because a new build produces <code>app.b72e04.js</code> and the HTML points to the new name. Only the HTML needs a short TTL.</p>

<h2>Pull vs push</h2>
<p>A <strong>pull</strong> CDN fetches from the origin on the first miss. That's the common choice, with no upload step. A <strong>push</strong> CDN has you upload content ahead of time, which suits large, predictable files like video releases. An <strong>origin shield</strong> adds one regional cache layer so that 300 PoPs missing at once send one request to your origin, not 300.</p>

<div class="note"><p><strong>In the game:</strong> the CDN serves 95% of static requests at 14 ms for everyone, including overseas users, who otherwise pay +130 ms on every request. In <em>Photo Wall</em>, 88% of traffic is static, so one CDN does more than nine app servers would.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Put static media in object storage (S3, GCS) behind a CDN.</li>
<li>Use content-hashed filenames with long TTLs, and a short TTL for the HTML.</li>
<li>Explain what happens on a miss, and add an origin shield for big fan-out.</li>
<li>Say whether any API responses are cacheable at the edge.</li>
<li>Remember that dynamic requests still benefit from TLS ending at the edge.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="queues", short="Queues", title="Message queues and backpressure",
     dek="Accept work now, do it at a pace you can sustain, and make sure you eventually catch up.",
     levels=["flashsale"], practice="flashsale",
     body=f"""
<p>In a synchronous design, the user waits while every step runs: validate, charge, write, email. If the slowest step can handle 600 operations a second and 1,000 people click "Buy" at once, 400 of them get errors.</p>
<p>A message queue splits <em>accepting</em> work from <em>doing</em> it. The API checks the request, puts a message on the queue, and immediately answers "order received". Workers pull messages off the queue and do the slow part at whatever rate the downstream system can handle.</p>

{diagram([[B("API", "validate + enqueue")], [B("QUEUE", "durable buffer", True)], [B("WORKER 1", ""), B("WORKER 2", ""), B("WORKER 3", "")], [B("DB", "600 writes/s")]],
         "The queue absorbs bursts. Workers drain it at a steady rate the database can take.")}

<h2>Load levelling: the math</h2>
<p>Let λ be the arrival rate and μ the rate your workers can process. During a burst where λ &gt; μ, the backlog grows. Afterwards it shrinks:</p>
<div class="math">backlog growth during a burst = (λ − μ) × burst duration
time to drain afterwards       = backlog ÷ (μ − λ_after)</div>
<p>The rule that matters: <strong>μ must exceed the average arrival rate</strong>, not the peak. If it doesn't, the backlog grows forever and "processed a bit later" turns into "processed tomorrow".</p>
<h3>Flash sale, worked</h3>
<p>Writes arrive at 315/s normally and 945/s during an 8-second sale. Two workers process 500/s together.</p>
<div class="math">backlog after the sale = (945 − 500) × 8 s ≈ 3,560 orders
drain time afterwards  = 3,560 ÷ (500 − 315) ≈ 19 s</div>
<p>No errors, and the database never sees more than 500 writes per second. With one worker (250/s), the drain rate is below even the normal 315/s arrival rate, so the backlog never clears.</p>

<h2>Queues vs logs</h2>
{table(["", "Message queue", "Log / stream"], [
    ["Examples", "RabbitMQ, Amazon SQS", "Apache Kafka, Kinesis, Redpanda"],
    ["After it's consumed", "The message is deleted", "The message stays for a retention period"],
    ["Consumers", "Compete for messages", "Each group reads the whole log at its own pace"],
    ["Ordering", "Best effort or FIFO queues", "Ordered within a partition"],
    ["Use for", "Task distribution, jobs", "Event streams, fan-out, replay"],
])}

<h2>Delivery guarantees</h2>
<ul>
<li><strong>At most once:</strong> fire and forget. Messages can be lost.</li>
<li><strong>At least once:</strong> the usual default. A worker that crashes before acknowledging gets the message redelivered, so <em>duplicates happen</em>.</li>
<li><strong>Exactly once:</strong> in practice, at-least-once delivery plus <strong>idempotent</strong> processing. Give each message an id (for example an idempotency key from the client), and have the worker skip ids it has already processed, using a unique constraint in the same transaction as the write.</li>
</ul>

<h2>When things go wrong</h2>
<ul>
<li><strong>Retries with exponential backoff and jitter:</strong> wait 1 s, 2 s, 4 s and so on, with randomness so retries don't arrive in synchronised waves.</li>
<li><strong>Dead-letter queue:</strong> after N failed attempts, move the message aside for a person to inspect, so one bad message can't block the queue.</li>
<li><strong>Visibility timeout:</strong> a message being processed is hidden from other workers until it's acknowledged or the timeout expires.</li>
<li><strong>Backpressure:</strong> when the queue is too deep, slow producers down or reject new work (HTTP 429 or 503) rather than buffering without limit.</li>
<li><strong>Outbox pattern:</strong> write the business row and an "outbox" row in one database transaction, then publish from the outbox. This avoids "saved but never published" and "published but never saved".</li>
</ul>

<h2>The product cost</h2>
<p>Asynchronous work changes what users see. The UI shows "processing", emails arrive a few seconds late, and you need a way to tell the user if something failed after you said "received". That's usually a good trade, but it's a product decision, not only an engineering one.</p>

<div class="note"><p><strong>In the game:</strong> with a queue, writes are acknowledged in about 4 ms whatever the database load. Workers drain 250 writes/s each, capped by database write capacity. The level checks that the queue is less than 10 seconds behind at the end, which fails if workers can't beat the average arrival rate.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Say which work becomes asynchronous and what the user sees meanwhile.</li>
<li>Size workers above the average arrival rate, and the queue for the burst.</li>
<li>State the delivery guarantee and how processing stays idempotent.</li>
<li>Cover retries, the dead-letter queue and backpressure.</li>
<li>Choose a queue or a log and explain why.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="availability", short="Availability", title="Availability, redundancy and failover",
     dek="Every component fails eventually. Design so that one failure costs you capacity, not the whole site.",
     levels=["nines", "frontpage"], practice="nines",
     body=f"""
<p>Availability is the fraction of time, or of requests, that the system works. It's usually written in "nines", and each extra nine cuts the allowed downtime by a factor of ten.</p>
{table(["Availability", "Downtime per year", "Per month"], [
    ["99% (two nines)", "3.65 days", "7.3 hours"],
    ["99.9% (three nines)", "8.77 hours", "43.8 minutes"],
    ["99.95%", "4.38 hours", "21.9 minutes"],
    ["99.99% (four nines)", "52.6 minutes", "4.4 minutes"],
    ["99.999% (five nines)", "5.26 minutes", "26 seconds"],
], numeric=(1, 2))}
<p>At four nines there isn't time for a person to notice, log in and fix anything. Recovery has to be automatic.</p>

<h2>Series and parallel</h2>
<p>When a request needs several components in a chain, their availabilities multiply, and the chain is weaker than any single link:</p>
<div class="math">series:   A = A₁ × A₂ × A₃
          99.9% × 99.9% × 99.9% ≈ 99.7%

parallel: A = 1 − (1 − A₁) × (1 − A₂)
          two independent 99% servers → 1 − 0.01 × 0.01 = 99.99%</div>
<p>Redundancy is the parallel formula at work: two mediocre components in parallel beat one excellent one. The catch is the word <em>independent</em>. Two servers in the same rack, on the same power supply, running the same buggy deploy, fail together.</p>

{diagram([[B("USERS", "")], [B("LB", "pair · health checks")], [B("APP 1", "zone a"), B("APP 2", "zone b"), B("APP 3", "zone c")], [B("PRIMARY", "zone a", True), B("STANDBY", "zone b")]],
         "Redundancy at every tier: spare app servers across zones and a standby database that can be promoted.")}

<h2>Remove single points of failure</h2>
<p>Go through the diagram box by box and ask: <em>what happens when this one dies?</em></p>
<ul>
<li><strong>Stateless tiers:</strong> run N+1 (or N+2) instances behind a load balancer with health checks. Losing one costs capacity, not availability.</li>
<li><strong>Stateful tiers:</strong> keep a replica or standby that can be promoted. See <a href="replication.html">replication</a>.</li>
<li><strong>The load balancer, DNS, config and secrets services:</strong> these are easy to forget, and they're single points of failure too.</li>
<li><strong>The data centre:</strong> spread across availability zones. For the highest targets, spread across regions.</li>
</ul>

<h2>Active-passive vs active-active</h2>
<p><strong>Active-passive</strong> keeps a standby idle until it's needed. It's simpler, but failover takes time and the standby might not work when you finally use it. <strong>Active-active</strong> serves traffic from every copy all the time, so you know every copy works, and failure only means redistributing load. You have to keep enough headroom that the survivors can carry the whole load.</p>

<h2>RTO and RPO</h2>
<p><strong>RTO</strong> (recovery time objective) is how long recovery may take. <strong>RPO</strong> (recovery point objective) is how much data you can afford to lose. A nightly backup gives you an RPO of 24 hours. Async replication gives seconds. Synchronous replication gives zero, at the cost of slower writes.</p>

<h2>Stop failures from spreading</h2>
<ul>
<li><strong>Timeouts</strong> on every network call. A call with no timeout ties up a thread forever when the other side hangs.</li>
<li><strong>Retries with backoff and jitter</strong>, only for idempotent operations, and with a retry budget. Unlimited retries turn a slow service into a dead one.</li>
<li><strong>Circuit breakers:</strong> after repeated failures, stop calling a dependency for a while and fail fast instead.</li>
<li><strong>Bulkheads:</strong> separate thread or connection pools per dependency, so one slow dependency can't use them all up.</li>
<li><strong>Graceful degradation:</strong> if the recommendations service is down, show the page without recommendations.</li>
</ul>

<h2>Practise failing</h2>
<p>Failover paths that never run tend to be broken when you need them. <strong>Chaos engineering</strong> kills instances, adds latency and cuts off zones on purpose, in a controlled way, to prove recovery works. That's what the <em>Four Nines</em> level does to your design.</p>

<div class="note"><p><strong>In the game:</strong> APP 1 crashes from 18 s to 34 s and the database primary dies from 38 s to 50 s. To stay under 0.5% errors, the remaining app servers must carry peak traffic (N+1), and a replica must be there to promote.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>State an availability target and translate it into downtime.</li>
<li>Walk every component and say what happens when it fails.</li>
<li>Run N+1 for stateless tiers and replicas with failover for stateful ones.</li>
<li>Give RTO and RPO numbers.</li>
<li>Add timeouts, retries with backoff and circuit breakers so failures don't spread.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="sharding", short="Sharding", title="Sharding and consistent hashing",
     dek="When one primary can't absorb your writes, split the data so each database owns a slice.",
     levels=["hypergrowth"], practice="hypergrowth",
     body=f"""
<p>Caches and replicas scale reads. Writes are different: every replica still applies every write, so a single primary is a hard ceiling on write throughput and on how much data fits on one machine. <strong>Sharding</strong> (horizontal partitioning) breaks that ceiling. Each shard is a full, independent database that owns a subset of the rows.</p>

{diagram([[B("APP", "")], [B("ROUTER", "key → shard", True)], [B("SHARD A", "users 0–3"), B("SHARD B", "users 4–7"), B("SHARD C", "users 8–b"), B("SHARD D", "users c–f")]],
         "A router (in the app, a proxy, or the database itself) maps each key to the shard that owns it.")}

<h2>Try everything else first</h2>
<p>Sharding is hard to undo and makes every later feature more complicated. Before you shard, check that you have tried indexes and query tuning, a bigger machine, a <a href="caching.html">cache</a>, <a href="replication.html">read replicas</a>, moving old data to cheaper storage, and splitting unrelated tables into separate databases.</p>

<h2>Partitioning strategies</h2>
{table(["Strategy", "How", "Strength", "Weakness"], [
    ["Range", "Shard A holds ids 1–1M, B holds 1M–2M…", "Range scans stay on one shard", "Hot spots: new ids all land on the last shard"],
    ["Hash", "shard = hash(key) mod N", "Even spread", "Range queries hit every shard; changing N moves most keys"],
    ["Consistent hash", "Keys and shards placed on a ring", "Adding a shard moves only ~1/N of keys", "More complex routing"],
    ["Directory", "A lookup table maps key → shard", "Full control, easy to move tenants", "The directory is another critical service"],
])}

<h2>Choosing the shard key</h2>
<p>The shard key is the most important decision. A good key:</p>
<ul>
<li><strong>Spreads load evenly:</strong> it has many distinct values and no single value dominates.</li>
<li><strong>Keeps queries local:</strong> the common queries include the key, so they touch one shard. For a social app, <code>user_id</code> keeps a user's posts, likes and settings together.</li>
<li><strong>Never changes:</strong> moving a row between shards because its key changed is painful.</li>
</ul>
<p>Bad keys create <strong>hot spots</strong>. A celebrity's account or a timestamp-based key can send most of the traffic to one shard. Mitigations include splitting a hot key into <code>key#0…key#9</code> (and merging on read), or giving very large tenants their own shards.</p>

<h2>Why mod-N hurts, and consistent hashing</h2>
<p>With <code>hash(key) mod N</code>, going from 4 to 5 shards changes the shard for about 80% of keys, because a key only stays put if <code>h mod 4 = h mod 5</code>. That's a huge data migration for one new shard.</p>
<p><strong>Consistent hashing</strong> places both shards and keys on a ring of hash values. Each key belongs to the next shard clockwise. Adding a shard only takes keys from its immediate neighbour, about <code>1/N</code> of the data. Giving each physical shard many <strong>virtual nodes</strong> on the ring smooths out uneven ranges and spreads a failed node's load across all the others. Dynamo, Cassandra and many caches use this approach.</p>

<h2>The costs you take on</h2>
<ul>
<li><strong>Cross-shard queries</strong> become scatter-gather: ask every shard and merge the results. They're slower, and as slow as the slowest shard.</li>
<li><strong>Cross-shard transactions</strong> need two-phase commit (slow, and it blocks if the coordinator fails) or a <strong>saga</strong> (a sequence of local transactions, each with an undo step).</li>
<li><strong>Unique constraints and auto-increment ids</strong> stop working globally. Use UUIDs, ULIDs or Snowflake-style ids.</li>
<li><strong>Operations multiply:</strong> backups, migrations and monitoring now cover N databases. Each shard still needs its own replicas for availability.</li>
<li><strong>Re-sharding</strong> is a project. Starting with more logical shards than machines (say 256 logical shards on 8 servers) lets you move whole logical shards later rather than splitting them.</li>
</ul>

<div class="note"><p><strong>In the game:</strong> each database you add in <em>Hypergrowth</em> is another shard with 600 writes/s of capacity. About 2,500 writes/s at peak means at least five shards, and six keeps write latency comfortable. The CDN and cache keep reads off the shards, so the budget goes on write capacity.</p></div>

<h2>Interview checklist</h2>
<ul class="check">
<li>Show that writes or data size have outgrown a single primary.</li>
<li>Name the shard key and explain why it spreads load and keeps queries local.</li>
<li>Choose the partitioning strategy (usually hash or consistent hash).</li>
<li>Handle hot keys and cross-shard queries.</li>
<li>Plan id generation, per-shard replication and future re-sharding.</li>
</ul>
"""),
]

READING = """
<h2>Further reading</h2>
<ul>
<li>Martin Kleppmann, <em>Designing Data-Intensive Applications</em> (O'Reilly). The standard book on replication, partitioning and consistency.</li>
<li><a href="https://sre.google/sre-book/table-of-contents/">Site Reliability Engineering</a>, Google's free book on running reliable systems.</li>
<li><a href="https://aws.amazon.com/builders-library/">The Amazon Builders' Library</a>: practical articles on timeouts, retries, caching and load shedding.</li>
<li><a href="https://github.com/donnemartin/system-design-primer">The System Design Primer</a>: a broad, community-maintained overview.</li>
</ul>
"""


def words(s):
    return len(re.sub(r"<[^>]+>", " ", s).split())


def shell(title, desc, body, current=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{FONTS}
<link rel="stylesheet" href="blog.css">
</head>
<body>
<div class="bar"><div class="wrap">
  <a class="brand" href="../index.html">Load<span>/</span>Bearing</a>
  <nav aria-label="Site"><a href="../index.html">Play</a><a href="index.html"{' aria-current="page"' if current == "index" else ""}>Field notes</a></nav>
</div></div>
{body}
</body>
</html>
"""


def level_links(ids):
    return ", ".join(f'<a href="../index.html#{i}">{LEVELS[i][0]} · {LEVELS[i][1]}</a>' for i in ids)


def build():
    OUT.mkdir(exist_ok=True)
    for i, p in enumerate(POSTS):
        mins = max(1, round(words(p["body"]) / 230))
        prev = POSTS[i - 1] if i > 0 else None
        nxt = POSTS[i + 1] if i + 1 < len(POSTS) else None
        lv = LEVELS[p["practice"]]
        pager = '<nav class="pager wrap" aria-label="More topics">'
        if prev:
            pager += f'<a href="{prev["slug"]}.html"><span class="label">Previous</span><b>{prev["title"]}</b></a>'
        if nxt:
            pager += f'<a class="next" href="{nxt["slug"]}.html"><span class="label">Next</span><b>{nxt["title"]}</b></a>'
        pager += "</nav>"
        body = f"""<main>
<header class="post wrap">
  <span class="label">Topic {i + 1:02d} of {len(POSTS)}</span>
  <h1>{p["title"]}</h1>
  <p class="dek">{p["dek"]}</p>
  <div class="meta"><span>{mins} min read</span><span>Used in: {level_links(p["levels"])}</span></div>
</header>
<article class="wrap">
{p["body"]}
<section class="game">
  <span class="label">Practise it</span>
  <h2>Level {lv[0]}: {lv[1]}</h2>
  <p>Put this into practice against live traffic. Your progress in the game is saved in your browser.</p>
  <a class="cta" href="../index.html#{p["practice"]}">Play level {lv[0]}</a>
</section>
{READING}
</article>
{pager}
</main>"""
        (OUT / f'{p["slug"]}.html').write_text(shell(f'{p["title"]} | Load/Bearing', p["dek"], body))

    items = "".join(
        f'<li><a href="{p["slug"]}.html"><span class="num">{i + 1:02d}</span><h2>{p["title"]}</h2>'
        f'<span class="lv">Level {", ".join(str(LEVELS[l][0]) for l in p["levels"])}</span><p>{p["dek"]}</p></a></li>'
        for i, p in enumerate(POSTS))
    body = f"""<main class="wrap">
<section class="intro">
  <span class="label">Field notes</span>
  <h1>The ideas behind every box</h1>
  <p>One article per building block you place in the game, in the order the levels need them. Read one before a level, or after it to see what the simulation was modelling.</p>
</section>
<ol class="list">{items}</ol>
</main>"""
    (OUT / "index.html").write_text(shell("Field Notes | Load/Bearing", "Articles on the system design concepts behind each level of Load/Bearing.", body, "index"))
    print(f"wrote {len(POSTS) + 1} pages to {OUT}")


if __name__ == "__main__":
    build()
