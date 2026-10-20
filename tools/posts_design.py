"""High-level design case studies and low-level design articles for the Field Notes blog.

build_blog.py calls design_posts() with its rendering helpers. Java snippets are plain
module-level strings so their braces don't clash with the f-string article bodies.
"""

# --------------------------------------------------------------------------- LLD snippets

SRP = """
// Before: three reasons to change in one class (format, pricing rules, email provider).
class InvoiceService {
    Invoice parse(String csv) { /* ... */ }
    long totalCents(Invoice invoice) { /* ... */ }
    void email(Invoice invoice) { /* ... */ }
}

// After: each class changes for one reason.
class InvoiceParser { Invoice parse(String csv) { /* ... */ } }
class InvoicePricer { long totalCents(Invoice invoice) { /* ... */ } }
class InvoiceMailer { void send(Invoice invoice) { /* ... */ } }
"""

OCP = """
interface Discount { long apply(long cents); }

record PercentOff(int percent) implements Discount {
    public long apply(long cents) { return cents * (100 - percent) / 100; }
}
record FlatOff(long off) implements Discount {
    public long apply(long cents) { return Math.max(0, cents - off); }
}

// Checkout never changes when marketing invents a new discount type.
long checkout(long cents, List<Discount> discounts) {
    for (Discount d : discounts) cents = d.apply(cents);
    return cents;
}
"""

LSP = """
// Violates LSP: code written against List expects add() to work.
class ReadOnlyList<T> extends ArrayList<T> {
    @Override public boolean add(T t) { throw new UnsupportedOperationException(); }
}

// Honest types instead: expose only what the object can actually do.
interface ReadableList<T> { T get(int i); int size(); }
"""

ISP = """
// A fat interface forces a basic printer to fake scan() and fax().
interface MultiFunctionDevice { void print(Doc d); void scan(Doc d); void fax(Doc d); }

// Small interfaces, combined only where needed.
interface Printer { void print(Doc d); }
interface Scanner { void scan(Doc d); }
class OfficeCopier implements Printer, Scanner { /* ... */ }
class HomePrinter implements Printer { /* ... */ }
"""

DIP = """
interface PaymentGateway { Receipt charge(String customerId, long cents); }

class OrderService {
    private final PaymentGateway payments;            // depends on the abstraction
    OrderService(PaymentGateway payments) { this.payments = payments; }

    Receipt place(Order order) { return payments.charge(order.customerId(), order.totalCents()); }
}

// Production: new OrderService(new StripeGateway(apiKey))
// Tests:      new OrderService(new FakeGateway())
"""

PATTERNS = {
"strategy": """
interface RoutingStrategy { Route route(Point from, Point to); }
class FastestRoute implements RoutingStrategy { /* ... */ }
class AvoidTolls  implements RoutingStrategy { /* ... */ }

class Navigator {
    private RoutingStrategy strategy;
    void setStrategy(RoutingStrategy s) { this.strategy = s; }   // swap at runtime
    Route navigate(Point a, Point b) { return strategy.route(a, b); }
}
""",
"factory": """
interface Sender { void send(String userId, String message); }

final class Senders {
    static Sender forChannel(Channel channel) {
        return switch (channel) {
            case EMAIL -> new EmailSender();
            case SMS   -> new SmsSender();
            case PUSH  -> new PushSender();
        };
    }
}
""",
"observer": """
interface OrderListener { void onPlaced(Order order); }

class OrderEvents {
    private final List<OrderListener> listeners = new CopyOnWriteArrayList<>();
    void subscribe(OrderListener l) { listeners.add(l); }
    void placed(Order o) { listeners.forEach(l -> l.onPlaced(o)); }
}

// events.subscribe(inventory::reserve); events.subscribe(mailer::sendConfirmation);
""",
"builder": """
Alert alert = Alert.builder()
        .service("payments")
        .severity(Severity.CRITICAL)
        .label("region", "ap-south-1")
        .dedupeWindow(Duration.ofMinutes(5))
        .build();                        // build() validates, then returns an immutable Alert
""",
"decorator": """
interface Store { byte[] get(String key); }

class CachingStore implements Store {
    private final Store inner;
    private final Map<String, byte[]> cache = new ConcurrentHashMap<>();
    CachingStore(Store inner) { this.inner = inner; }
    public byte[] get(String key) { return cache.computeIfAbsent(key, inner::get); }
}

// Same interface, layered behaviour: new MetricsStore(new CachingStore(new S3Store()))
""",
"adapter": """
// Third-party SDK with its own shape.
class TwilioClient { MessageResult create(String to, String from, String body) { /* ... */ } }

// Our interface; the rest of the code never sees Twilio.
class TwilioSmsSender implements SmsSender {
    private final TwilioClient client;
    private final String fromNumber;
    TwilioSmsSender(TwilioClient client, String fromNumber) { this.client = client; this.fromNumber = fromNumber; }
    public void send(String phone, String text) { client.create(phone, fromNumber, text); }
}
""",
}

COMPOSITION = """
// Inheritance: one subclass per combination, and it multiplies with every new channel.
class EmailNotifier { void notify(User u, String msg) { /* ... */ } }
class EmailAndSmsNotifier extends EmailNotifier { /* ... */ }
class EmailSmsAndPushNotifier extends EmailAndSmsNotifier { /* ... */ }

// Composition: a notifier has channels; combinations are just lists.
interface Channel { void send(User u, String msg); }

class Notifier {
    private final List<Channel> channels;
    Notifier(List<Channel> channels) { this.channels = List.copyOf(channels); }
    void notify(User u, String msg) { channels.forEach(c -> c.send(u, msg)); }
}

// new Notifier(List.of(new Email(), new Push()))
"""

LRU = """
public final class LruCache<K, V> {
    private final class Node {
        final K key;
        V value;
        Node prev, next;
        Node(K key, V value) { this.key = key; this.value = value; }
    }

    private final int capacity;
    private final Map<K, Node> map = new HashMap<>();
    private final Node head = new Node(null, null);   // most recently used end
    private final Node tail = new Node(null, null);   // least recently used end

    public LruCache(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity must be positive");
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    public synchronized Optional<V> get(K key) {
        Node n = map.get(key);
        if (n == null) return Optional.empty();
        moveToFront(n);
        return Optional.of(n.value);
    }

    public synchronized void put(K key, V value) {
        Node n = map.get(key);
        if (n != null) {
            n.value = value;
            moveToFront(n);
            return;
        }
        if (map.size() == capacity) {
            Node lru = tail.prev;
            unlink(lru);
            map.remove(lru.key);
        }
        n = new Node(key, value);
        map.put(key, n);
        addFront(n);
    }

    private void moveToFront(Node n) { unlink(n); addFront(n); }
    private void unlink(Node n) { n.prev.next = n.next; n.next.prev = n.prev; }
    private void addFront(Node n) {
        n.next = head.next;
        n.prev = head;
        head.next.prev = n;
        head.next = n;
    }
}
"""

LRU_LHM = """
class LruMap<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;
    LruMap(int capacity) { super(16, 0.75f, true); this.capacity = capacity; }   // true = access order
    @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) { return size() > capacity; }
}
"""

BUCKET = """
public final class TokenBucket {
    private final long capacity;
    private final double refillPerNano;
    private final LongSupplier clock;      // System::nanoTime in production, a fake in tests
    private double tokens;
    private long last;

    public TokenBucket(long capacity, double refillPerSecond, LongSupplier clock) {
        if (capacity <= 0 || refillPerSecond < 0) throw new IllegalArgumentException();
        this.capacity = capacity;
        this.refillPerNano = refillPerSecond / 1_000_000_000.0;
        this.clock = clock;
        this.tokens = capacity;
        this.last = clock.getAsLong();
    }

    public synchronized boolean tryAcquire() {
        long now = clock.getAsLong();
        tokens = Math.min(capacity, tokens + (now - last) * refillPerNano);   // lazy refill, no timer
        last = now;
        if (tokens < 1) return false;
        tokens -= 1;
        return true;
    }
}
"""

PER_USER = """
public final class PerUserLimiter {
    private final Map<String, TokenBucket> buckets;
    private final Supplier<TokenBucket> newBucket;

    public PerUserLimiter(int maxUsers, Supplier<TokenBucket> newBucket) {
        this.newBucket = newBucket;
        // Access-ordered LinkedHashMap: the least recently seen user is evicted first.
        this.buckets = Collections.synchronizedMap(new LinkedHashMap<String, TokenBucket>(16, 0.75f, true) {
            @Override protected boolean removeEldestEntry(Map.Entry<String, TokenBucket> eldest) {
                return size() > maxUsers;
            }
        });
    }

    public boolean allow(String userId) {
        return buckets.computeIfAbsent(userId, id -> newBucket.get()).tryAcquire();
    }
}
"""

BUCKET_TEST = """
class TokenBucketTest {
    private long now = 0;                                   // fake clock, in nanoseconds

    @Test
    void allowsBurstThenRefillsAtRate() {
        TokenBucket bucket = new TokenBucket(3, 1.0, () -> now);
        assertTrue(bucket.tryAcquire());
        assertTrue(bucket.tryAcquire());
        assertTrue(bucket.tryAcquire());
        assertFalse(bucket.tryAcquire());                   // burst used up

        now += 1_000_000_000L;                              // one second later
        assertTrue(bucket.tryAcquire());
        assertFalse(bucket.tryAcquire());
    }

    @Test
    void neverGrantsMoreThanCapacityUnderContention() throws Exception {
        TokenBucket bucket = new TokenBucket(100, 0.0, () -> 0L);
        AtomicInteger granted = new AtomicInteger();
        List<Callable<Void>> calls = new ArrayList<>();
        for (int i = 0; i < 1_000; i++) {
            calls.add(() -> { if (bucket.tryAcquire()) granted.incrementAndGet(); return null; });
        }
        ExecutorService pool = Executors.newFixedThreadPool(8);
        pool.invokeAll(calls);
        pool.shutdown();
        assertEquals(100, granted.get());
    }
}
"""

PARKING_MODEL = """
enum VehicleType { MOTORCYCLE, CAR, TRUCK }
enum SpotSize { SMALL, MEDIUM, LARGE }

record Vehicle(String plate, VehicleType type) {}
record Spot(String id, int floor, SpotSize size) {}
record Ticket(String id, Vehicle vehicle, Spot spot, Instant entry) {}

interface SpotAllocationStrategy { Optional<Spot> claim(Vehicle vehicle, SpotInventory inventory); }
interface FeePolicy { long feeCents(Ticket ticket, Instant exit); }
"""

PARKING_INVENTORY = """
final class SpotInventory {
    private final Map<SpotSize, Queue<Spot>> free = new EnumMap<>(SpotSize.class);

    SpotInventory(Collection<Spot> spots) {
        for (SpotSize size : SpotSize.values()) free.put(size, new ConcurrentLinkedQueue<>());
        spots.forEach(this::release);
    }

    /** Atomically takes a free spot of this size. Two callers can never get the same spot. */
    Optional<Spot> claim(SpotSize size) { return Optional.ofNullable(free.get(size).poll()); }

    void release(Spot spot) { free.get(spot.size()).offer(spot); }
}
"""

PARKING_LOT = """
final class SmallestFit implements SpotAllocationStrategy {
    public Optional<Spot> claim(Vehicle vehicle, SpotInventory inventory) {
        for (SpotSize size : sizesThatFit(vehicle.type())) {
            Optional<Spot> spot = inventory.claim(size);
            if (spot.isPresent()) return spot;
        }
        return Optional.empty();
    }

    private static List<SpotSize> sizesThatFit(VehicleType type) {
        return switch (type) {
            case MOTORCYCLE -> List.of(SpotSize.SMALL, SpotSize.MEDIUM, SpotSize.LARGE);
            case CAR        -> List.of(SpotSize.MEDIUM, SpotSize.LARGE);
            case TRUCK      -> List.of(SpotSize.LARGE);
        };
    }
}

record HourlyFee(Map<SpotSize, Long> centsPerHour) implements FeePolicy {
    public long feeCents(Ticket ticket, Instant exit) {
        long minutes = Duration.between(ticket.entry(), exit).toMinutes();
        long hours = Math.max(1, (minutes + 59) / 60);           // round up, minimum one hour
        return hours * centsPerHour.get(ticket.spot().size());
    }
}

final class ParkingLot {
    private final SpotInventory inventory;
    private final SpotAllocationStrategy allocation;
    private final FeePolicy fees;
    private final Clock clock;
    private final Map<String, Ticket> active = new ConcurrentHashMap<>();

    ParkingLot(SpotInventory inventory, SpotAllocationStrategy allocation, FeePolicy fees, Clock clock) {
        this.inventory = inventory; this.allocation = allocation; this.fees = fees; this.clock = clock;
    }

    Optional<Ticket> enter(Vehicle vehicle) {
        return allocation.claim(vehicle, inventory).map(spot -> {
            Ticket ticket = new Ticket(UUID.randomUUID().toString(), vehicle, spot, clock.instant());
            active.put(ticket.id(), ticket);
            return ticket;
        });
    }

    long exit(String ticketId) {
        Ticket ticket = active.remove(ticketId);                // remove() is atomic: a ticket exits once
        if (ticket == null) throw new IllegalArgumentException("Unknown or already used ticket " + ticketId);
        inventory.release(ticket.spot());
        return fees.feeCents(ticket, clock.instant());
    }
}
"""

PARKING_SQL = """
-- Claim one free medium spot; concurrent transactions skip rows already locked by others.
UPDATE spots SET occupied = true, ticket_id = :ticket
WHERE id = (
    SELECT id FROM spots
    WHERE size = 'MEDIUM' AND NOT occupied
    ORDER BY floor, id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id;          -- no row returned means the lot is full
"""

SPLIT = """
final class Splits {
    /** Splits totalCents in proportion to weights. Leftover cents go to the largest remainders,
     *  so the parts always add up exactly to the total. */
    static Map<String, Long> byWeight(long totalCents, Map<String, Long> weights) {
        long sum = weights.values().stream().mapToLong(Long::longValue).sum();
        if (sum <= 0) throw new IllegalArgumentException("weights must add up to more than zero");
        Map<String, Long> parts = new LinkedHashMap<>();
        List<Map.Entry<String, Long>> remainders = new ArrayList<>();
        long assigned = 0;
        for (Map.Entry<String, Long> w : weights.entrySet()) {
            long scaled = totalCents * w.getValue();
            parts.put(w.getKey(), scaled / sum);
            assigned += scaled / sum;
            remainders.add(Map.entry(w.getKey(), scaled % sum));
        }
        remainders.sort(Map.Entry.<String, Long>comparingByValue().reversed());
        for (int i = 0; i < totalCents - assigned; i++) {
            parts.merge(remainders.get(i).getKey(), 1L, Long::sum);
        }
        return parts;
    }

    // Each split type is only validation plus weights. There is one code path for the arithmetic.
    static Map<String, Long> equal(long totalCents, List<String> people) {
        Map<String, Long> weights = new LinkedHashMap<>();
        people.forEach(p -> weights.put(p, 1L));
        return byWeight(totalCents, weights);
    }

    static Map<String, Long> percent(long totalCents, Map<String, Long> basisPoints) {
        require(sum(basisPoints) == 10_000, "percentages must add up to 100%");
        return byWeight(totalCents, basisPoints);
    }

    static Map<String, Long> exact(long totalCents, Map<String, Long> cents) {
        require(sum(cents) == totalCents, "amounts must add up to the total");
        return byWeight(totalCents, cents);          // weights equal to the amounts reproduce them exactly
    }

    private static long sum(Map<String, Long> m) { return m.values().stream().mapToLong(Long::longValue).sum(); }
    private static void require(boolean ok, String message) { if (!ok) throw new IllegalArgumentException(message); }
}
"""

LEDGER = """
record Expense(String id, String paidBy, long totalCents, Map<String, Long> owed) {}
record Transfer(String from, String to, long cents) {}

final class Group {
    private final Map<String, Long> net = new HashMap<>();   // positive: is owed; negative: owes

    void add(Expense e) {
        net.merge(e.paidBy(), e.totalCents(), Long::sum);
        e.owed().forEach((person, cents) -> net.merge(person, -cents, Long::sum));
    }

    Map<String, Long> balances() { return Map.copyOf(net); }

    /** Greedy settlement: largest debtor pays largest creditor. At most n - 1 transfers, O(n log n). */
    List<Transfer> settle() {
        Comparator<Map.Entry<String, Long>> bySize = Comparator.comparingLong(e -> Math.abs(e.getValue()));
        PriorityQueue<Map.Entry<String, Long>> creditors = new PriorityQueue<>(bySize.reversed());
        PriorityQueue<Map.Entry<String, Long>> debtors = new PriorityQueue<>(bySize.reversed());
        net.forEach((person, cents) -> {
            if (cents > 0) creditors.add(Map.entry(person, cents));
            else if (cents < 0) debtors.add(Map.entry(person, cents));
        });

        List<Transfer> transfers = new ArrayList<>();
        while (!creditors.isEmpty()) {
            Map.Entry<String, Long> c = creditors.poll(), d = debtors.poll();
            long pay = Math.min(c.getValue(), -d.getValue());
            transfers.add(new Transfer(d.getKey(), c.getKey(), pay));
            if (c.getValue() > pay) creditors.add(Map.entry(c.getKey(), c.getValue() - pay));
            if (-d.getValue() > pay) debtors.add(Map.entry(d.getKey(), d.getValue() + pay));
        }
        return transfers;
    }
}
"""

ELEVATOR_STATE = """
enum State {
    IDLE, MOVING_UP, MOVING_DOWN, DOORS_OPEN, DOORS_CLOSING, OUT_OF_SERVICE;

    private static final Map<State, Set<State>> NEXT = new EnumMap<>(State.class);
    static {
        NEXT.put(IDLE,           EnumSet.of(MOVING_UP, MOVING_DOWN, DOORS_OPEN, OUT_OF_SERVICE));
        NEXT.put(MOVING_UP,      EnumSet.of(DOORS_OPEN, OUT_OF_SERVICE));
        NEXT.put(MOVING_DOWN,    EnumSet.of(DOORS_OPEN, OUT_OF_SERVICE));
        NEXT.put(DOORS_OPEN,     EnumSet.of(DOORS_CLOSING));
        NEXT.put(DOORS_CLOSING,  EnumSet.of(DOORS_OPEN, IDLE, MOVING_UP, MOVING_DOWN));
        NEXT.put(OUT_OF_SERVICE, EnumSet.of(IDLE));
    }

    boolean canGoTo(State next) { return NEXT.get(this).contains(next); }
}
"""

ELEVATOR_CAR = """
final class Elevator {
    private int floor;
    private State state = State.IDLE;
    private final TreeSet<Integer> stopsAbove = new TreeSet<>();
    private final TreeSet<Integer> stopsBelow = new TreeSet<>();

    synchronized void addStop(int target) {
        if (target > floor) stopsAbove.add(target);
        else if (target < floor) stopsBelow.add(target);
        // target == floor: open the doors (omitted)
    }

    /** LOOK: keep going while there are stops ahead in this direction, then reverse. */
    synchronized OptionalInt nextStop() {
        boolean down = state == State.MOVING_DOWN;
        Integer next = down ? stopsBelow.floor(floor) : stopsAbove.ceiling(floor);
        if (next == null) next = down ? stopsAbove.ceiling(floor) : stopsBelow.floor(floor);
        return next == null ? OptionalInt.empty() : OptionalInt.of(next);
    }

    synchronized void transition(State to) {
        if (!state.canGoTo(to)) throw new IllegalStateException(state + " -> " + to + " is not allowed");
        state = to;
    }
}
"""

ELEVATOR_DISPATCH = """
enum Direction { UP, DOWN }
record HallCall(int floor, Direction direction) {}
// Elevator also exposes floor(), isIdle(), inService() and isHeadingTowards(call); omitted above.

interface DispatchStrategy { Elevator choose(HallCall call, List<Elevator> cars); }

final class NearestCompatible implements DispatchStrategy {
    private static final int TURNAROUND_PENALTY = 100;

    public Elevator choose(HallCall call, List<Elevator> cars) {
        return cars.stream()
                .filter(Elevator::inService)
                .min(Comparator.comparingInt(car -> cost(car, call)))
                .orElseThrow(() -> new IllegalStateException("no elevator in service"));
    }

    // Idle cars, or cars already heading to the caller in the caller's direction, are cheapest.
    private int cost(Elevator car, HallCall call) {
        int distance = Math.abs(car.floor() - call.floor());
        return car.isIdle() || car.isHeadingTowards(call) ? distance : distance + TURNAROUND_PENALTY;
    }
}

// Swap the policy without touching the cars:
// building.setDispatch(isMorningPeak ? new LobbyFirst() : new NearestCompatible());
"""


def design_posts(diagram, table, B, code):
    hld = [
# ---------------------------------------------------------------------------
dict(slug="url-shortener", short="URL shortener", title="URL shortener and ID generation",
     dek="A tiny product with a real design question: how do you hand out billions of short, unique keys without a bottleneck?",
     practice="sandbox",
     body=f"""
<p>A URL shortener turns <code>https://example.com/some/very/long/path?with=params</code> into <code>sho.rt/aZ3kQ9x</code> and redirects anyone who visits the short link. The redirect has to be fast and almost never fail, which makes it a good exercise in caching and availability. The interesting part is generating the keys.</p>

<h2>Requirements and numbers</h2>
<ul>
<li><strong>Functional:</strong> create a short link (optionally with a custom alias and an expiry), redirect, and count clicks.</li>
<li><strong>Non-functional:</strong> redirects in a few milliseconds, very high availability, no two long URLs ever sharing a key, and keys that aren't easy to guess.</li>
</ul>
{table(["Quantity", "Math", "Result"], [
    ["New links per second", "100M per month ÷ 2.6M seconds", "≈ 40/s average, ~120/s peak"],
    ["Redirects per second", "100 reads per write", "≈ 4,000/s average, ~12,000/s peak"],
    ["Rows after 5 years", "100M × 12 × 5", "6 billion"],
    ["Storage", "6B × ~500 bytes", "≈ 3 TB"],
    ["Key space with 7 base62 characters", "62⁷", "≈ 3.5 trillion"],
], numeric=(2,))}
<p>Writes are tiny. Reads are 100 times larger and very skewed, since a few links go viral. Seven characters of <code>[0-9a-zA-Z]</code> give about 580 keys for every link you'll ever store.</p>

{diagram([[B("CLIENT", "")], [B("LB", "")], [B("API 1", "stateless"), B("API 2", "stateless")], [B("REDIS", "key → URL", True), B("URL DB", "key-value"), B("KEY POOL", "pre-generated")]],
         "Writes take a key from the pool and store the mapping. Redirects read Redis first and fall back to the database.")}

<h2>Generating keys</h2>
{table(["Approach", "How", "Good", "Bad"], [
    ["Hash the URL", "Take the first 7 base62 characters of MD5 or SHA-256 of the long URL.", "The same URL always gets the same key, so no duplicates.", "Collisions: check, and on a clash re-hash with a salt and retry."],
    ["Counter + base62", "A global counter; encode each new number in base62.", "No collisions; keys are as short as possible.", "One counter is a bottleneck and a single point of failure, and sequential keys can be enumerated."],
    ["Counter ranges", "Each server leases a block (say 1,000 numbers) from a coordinator.", "No per-request coordination.", "A crashed server wastes its block, which is fine. Keys are still guessable unless scrambled."],
    ["Pre-generated pool", "A key generation service creates random unused keys offline; servers take batches.", "No collision check at write time; random, unguessable keys.", "An extra service, and the pool must not run dry."],
])}
<p>Collision odds for the hash approach: with 6 billion keys in a space of 3.5 trillion, each new key has about a 0.17% chance of hitting an existing one. One retry fixes nearly all of them, so hashing works fine. A common interview answer is <strong>counter ranges with the numbers scrambled</strong> (for example by a reversible bit shuffle) so the keys look random, or a <strong>pre-generated pool</strong>.</p>

<h2>General-purpose IDs</h2>
<p>The same problem shows up everywhere you need unique IDs without a central database sequence:</p>
<ul>
<li><strong>UUID v4:</strong> 128 random bits, no coordination at all. But it's long, and random inserts scatter across a B-tree index and slow down writes.</li>
<li><strong>UUID v7 / ULID:</strong> a timestamp prefix plus randomness, so IDs sort roughly by creation time and insert at the "end" of the index.</li>
<li><strong>Snowflake</strong> (Twitter's scheme): a 64-bit integer made of 41 bits of milliseconds, 10 bits of machine ID and 12 bits of sequence. That's 4,096 IDs per millisecond per machine, time-ordered, with no coordination beyond assigning machine IDs. In base62 it's 11 characters, too long for short links but ideal for posts and messages.</li>
</ul>

<h2>The redirect path</h2>
<ul>
<li><strong>301 or 302?</strong> A <code>301 Moved Permanently</code> lets browsers and CDNs cache the redirect, which saves load but hides repeat clicks from you. A <code>302 Found</code> sends every click through your servers, so you can count them. Use 302 if analytics matter.</li>
<li><strong>Cache:</strong> cache-aside in Redis keyed by the short key. Traffic follows a power law, so a cache holding the hottest few percent of links serves 90%+ of redirects, and the database sees roughly 1,200 reads per second at peak.</li>
<li><strong>Analytics off the hot path:</strong> don't write a row per click. Publish a click event to a log (Kafka) and aggregate counts asynchronously.</li>
</ul>

<h2>Storage</h2>
<p>The data is a simple mapping looked up by primary key, with no joins, so a key-value store (DynamoDB, Cassandra) fits naturally and partitions by key. PostgreSQL works too at this size: 3 TB over five years is manageable with a few shards. Store <code>short_key</code> (primary key), <code>long_url</code>, <code>owner_id</code>, <code>created_at</code> and <code>expires_at</code>. Expired links can be deleted lazily on read and by a periodic cleanup job.</p>

<h2>Abuse</h2>
<p>Shorteners attract spam and phishing. Rate-limit link creation per user and per IP (see <a href="rate-limiting.html">rate limiting</a>, including how to keep counters consistent across N servers), check new URLs against a malware blocklist, and make custom aliases a logged-in feature.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Estimate QPS and storage, and size the key space.</li>
<li>Compare at least two key-generation schemes and pick one.</li>
<li>Choose 301 or 302 and explain the analytics trade-off.</li>
<li>Cache the redirect path and estimate the hit rate.</li>
<li>Rate-limit creation, and move analytics off the hot path.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="news-feed", short="News feed", title="News feed and fan-out",
     dek="Precompute every user's feed when someone posts, or assemble it when they open the app? The answer is both.",
     practice="sandbox",
     body=f"""
<p>A news feed shows each user recent posts from the accounts they follow. Users read their feed far more often than anyone posts, and some accounts have millions of followers. The core decision is when to do the work of matching posts to readers.</p>

<h2>Numbers</h2>
{table(["Quantity", "Math", "Result"], [
    ["Daily active users", "", "200M"],
    ["New posts", "200M × 1 per day ÷ 86,400", "≈ 2,300/s"],
    ["Feed loads", "200M × 10 per day ÷ 86,400", "≈ 23,000/s"],
    ["Feed inserts if every post is pushed", "2,300 × 200 average followers", "≈ 460,000/s"],
], numeric=(2,))}

<h2>Fan-out on write (push)</h2>
<p>When someone posts, a worker looks up their followers and adds the post ID to each follower's precomputed feed, typically a capped Redis sorted set of the newest few hundred IDs. Reading a feed is then a single cheap lookup.</p>
{diagram([[B("POST API", "")], [B("POSTS DB", "post rows"), B("FANOUT QUEUE", "post id", True)], [B("FANOUT WORKERS", "batch by follower")], [B("FEED CACHE", "user → [post ids]")]],
         "Push: the post is stored once, and its ID is copied into every follower's feed in the background.",
         edges=[[(0, 0), (0, 1)], [(1, 0)], None])}
<p><strong>Where it breaks:</strong> a celebrity with 10 million followers creates 10 million feed writes per post, and each of those followers' feeds updates late. Most of that work is wasted on followers who won't open the app today. Deletes and edits have to be fanned out too.</p>

<h2>Fan-out on read (pull)</h2>
<p>Store only each author's own posts. When a user opens the feed, fetch recent posts from everyone they follow and merge them, a k-way merge by time or score.</p>
<p><strong>Where it breaks:</strong> a user who follows 2,000 accounts triggers 2,000 lookups per feed load, at 23,000 loads per second. Reads become slow and expensive, and that's the operation users do most.</p>

<h2>The hybrid most systems use</h2>
<ul>
<li><strong>Push</strong> for ordinary authors, who have hundreds or thousands of followers.</li>
<li><strong>Pull</strong> for celebrities above a threshold (say 100,000 followers). Their recent posts are cached hot, because millions of readers want the same few posts.</li>
<li>At read time, merge the precomputed feed with recent posts from the celebrities that user follows.</li>
<li>Skip pushing to inactive users, and build their feed on demand when they return.</li>
</ul>
<p>That answers the celebrity question: a post by an account with 10M followers costs one write, plus a cache entry that millions of feed reads share.</p>

<h2>Storage</h2>
<ul>
<li><strong>Posts:</strong> sharded by post ID or author ID. Feed caches hold only IDs, and posts are fetched in bulk (multi-get) from a post cache, so an edit updates one place.</li>
<li><strong>Follow graph:</strong> store both directions, <code>followers(author)</code> for fan-out and <code>following(user)</code> for pull, because each is queried by a different key.</li>
<li><strong>Feed cache:</strong> keep only the last few hundred IDs per user. Older pages come from a slower path.</li>
</ul>

<h2>Ranking and pagination</h2>
<p>Chronological feeds sort by time. Ranked feeds first gather candidates (pushed IDs plus pulled celebrity posts), then score them with a model and keep the best. Paginate with a <strong>cursor</strong> (the last ID or score seen), not an offset: new posts arriving at the top would make offset pages shift and repeat.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Estimate posts per second, feed reads per second and average followers.</li>
<li>Explain push and pull, and where each breaks.</li>
<li>Propose the hybrid with a celebrity threshold.</li>
<li>Store IDs in feeds and fetch post bodies in bulk.</li>
<li>Use cursor pagination, and say how ranking fits in.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="notifications", short="Notifications", title="Notification service",
     dek="Deliver each message once, on the right channel, at the right time, even though every provider and network in the path can fail.",
     practice="sandbox",
     body=f"""
<p>Every product grows a notification system: order updates by push, receipts by email, one-time passwords by SMS. Dozens of services want to notify users, so it pays to build one shared service that handles preferences, templates, retries and provider quirks in one place.</p>

{diagram([[B("SERVICES", "order, auth, social")], [B("NOTIFY API", "validate + dedupe", True)], [B("EVENT LOG", "Kafka")], [B("ROUTER", "prefs, templates")], [B("PUSH Q", "APNs / FCM"), B("EMAIL Q", "SES / SendGrid"), B("SMS Q", "Twilio")]],
         "Producers call one API. A router applies preferences and templates, then each channel has its own queue and workers.")}

<h2>The pipeline</h2>
<ol>
<li><strong>API:</strong> producers send an event, not a finished message: "order 812 shipped for user 42", with an <strong>idempotency key</strong>. The API stores the key and rejects repeats.</li>
<li><strong>Durable log:</strong> accepted events go to Kafka, so a slow provider never blocks the services calling the API.</li>
<li><strong>Router:</strong> loads the user's preferences and contact details, chooses channels, renders templates, and applies quiet hours and frequency caps.</li>
<li><strong>Channel queues and workers:</strong> one queue per channel, so a slow SMS provider can't delay push notifications. Workers call providers within each provider's rate limits.</li>
<li><strong>Status store:</strong> one record per notification and channel attempt: queued, sent, delivered, opened, failed.</li>
</ol>
<p>Give one-time passwords and security alerts their own high-priority queue. Marketing can wait; a login code can't.</p>

<h2>Deduplicating across channels</h2>
<p>Duplicates come from two places: producers sending the same event twice, and the router choosing several channels for one event.</p>
<ul>
<li><strong>Producer duplicates:</strong> dedupe on the idempotency key (or on <code>user_id + event_type + entity_id</code>) with a unique constraint or a Redis <code>SET NX</code> with a TTL.</li>
<li><strong>Channel policy:</strong> decide per event type, not per channel. For example: send push first; if it isn't opened within 10 minutes, send email; never send SMS for the same event. One notification record per event, with its channel attempts underneath, makes that easy to enforce.</li>
<li><strong>Per-channel key:</strong> <code>(notification_id, channel)</code> is unique in the status store, so a worker that picks up the same job twice finds it already sent.</li>
</ul>

<h2>Retries without double notifying</h2>
<ul>
<li>Record the attempt as <em>sending</em> before calling the provider and <em>sent</em> afterwards. A retry checks that state first.</li>
<li>Retry only errors that can succeed later: timeouts, HTTP 5xx and 429. Don't retry 4xx errors like an invalid phone number or an unregistered device token. Use exponential backoff with jitter, cap the attempts, then send the job to a dead-letter queue.</li>
<li>The hard case is a timeout after the provider has already accepted the message. You can't know whether it was sent. Where providers support it, a collapse key (APNs <code>apns-collapse-id</code>, FCM <code>collapse_key</code>) makes the device replace duplicates instead of showing two. For the rest, accept a rare duplicate rather than risk never sending.</li>
<li>Producers should publish through a <strong>transactional outbox</strong> so "order shipped" is only announced if the order update committed.</li>
</ul>

<h2>The 10-million-follower broadcast</h2>
<p>"Notify everyone who follows this account" must not become one request with 10 million recipients. A broadcast job pages through followers in batches of a few thousand and enqueues those batches at a rate the providers allow, often spread over minutes. Low-priority queues absorb it without delaying transactional messages. Collapse repeated broadcasts ("12 people liked your post") rather than sending one notification each.</p>

<h2>Preferences and the law</h2>
<p>Every channel needs per-category opt-outs, an unsubscribe link in marketing email, quiet hours in the user's time zone, and a cap on messages per day. These belong in the router, so no producing service can bypass them.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>One API taking events plus idempotency keys, then a durable log.</li>
<li>Separate queues per channel and per priority.</li>
<li>A channel policy and unique keys to prevent duplicates.</li>
<li>Retry rules: what's retryable, backoff, dead-letter queue, collapse keys.</li>
<li>Batch big broadcasts, and enforce preferences centrally.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="chat", short="Chat", title="Chat systems and real-time connections",
     dek="Millions of open connections, messages that must arrive in order, and users who are offline half the time.",
     practice="sandbox",
     body=f"""
<p>A chat system looks simple: send a message, the other person sees it. Under the hood it needs persistent connections to millions of devices, a way to find which server holds each user's connection, ordering within each conversation, and a plan for everyone who is offline.</p>

<h2>Getting messages to the device</h2>
{table(["Transport", "How", "Fits"], [
    ["Short polling", "The client asks for new messages every few seconds.", "Simple, but slow and wasteful."],
    ["Long polling", "The server holds the request open until a message arrives or it times out.", "Works everywhere, but reconnects after every message."],
    ["Server-sent events", "One long HTTP response streams events, server to client only.", "Live feeds and notifications."],
    ["WebSocket", "One persistent, two-way connection.", "Chat, multiplayer, collaborative editing."],
])}
<p>Chat uses WebSockets. Mobile apps also use push notifications (APNs, FCM) to wake the app when it's in the background.</p>

{diagram([[B("CLIENT A", "")], [B("GATEWAY 1", "holds A's socket")], [B("CHAT SERVICE", "persist + route", True)], [B("GATEWAY 7", "holds B's socket")], [B("CLIENT B", "")]],
         "The chat service saves the message, looks up which gateway holds the recipient's connection in the session registry, and forwards it there.")}

<h2>Where connection state lives</h2>
<p>A WebSocket is attached to one gateway server, so the gateways are stateful and everything behind them stays stateless:</p>
<ul>
<li><strong>Session registry:</strong> when a client connects, its gateway writes <code>user_id → gateway_id</code> to Redis with a TTL that heartbeats refresh. A user on three devices has three entries.</li>
<li><strong>Routing:</strong> the chat service stores the message, looks up each recipient's gateways, and publishes to those gateways, through a per-gateway channel in Redis pub/sub, an internal RPC, or a message broker.</li>
<li><strong>Capacity:</strong> a tuned gateway holds hundreds of thousands of mostly idle connections, so 50M concurrent users need a few hundred gateways. Memory per connection is the limit.</li>
<li><strong>Deploys and failures:</strong> when a gateway dies, its clients reconnect (with backoff and jitter, so they don't all return at once) to another gateway, which re-registers them. Clients then resync anything they missed (below).</li>
</ul>

<h2>Ordering within a conversation</h2>
<p>You don't need global ordering, only ordering within each conversation, and client clocks can't be trusted for that.</p>
<ul>
<li>Give each conversation a single writer: partition by <code>conversation_id</code> (a Kafka partition or a database shard owns each conversation). That writer assigns a <strong>monotonically increasing sequence number</strong> to every message.</li>
<li>Clients sort by sequence number and spot gaps ("I have 41 and 43, fetch 42").</li>
<li>Clients attach a <code>client_msg_id</code> to every send, so a retry after a dropped connection doesn't post the message twice.</li>
</ul>

<h2>Storage and receipts</h2>
<p>Messages are written constantly and read by conversation, newest first, which fits a wide-column store partitioned by <code>conversation_id</code> and sorted by sequence number (see <a href="sql-nosql.html">SQL vs NoSQL</a>). For receipts, don't store a row per message per reader. Store <strong>watermarks</strong> per member:</p>
<div class="math">messages:  (conversation_id, seq) → sender_id, body, sent_at, client_msg_id
receipts:  (conversation_id, user_id) → last_delivered_seq, last_read_seq

message 120 is "read by everyone" when min(last_read_seq over members) ≥ 120</div>
<p>One small write per member updates every receipt at once, and "seen by 4 of 7" in a group is a simple count.</p>

<h2>Offline users</h2>
<p>Messages are saved before delivery, so "offline" just means "not delivered yet". When a client reconnects, it sends its last seen sequence number per conversation, and the server returns everything newer. While the user has no live connection, the chat service also asks the <a href="notifications.html">notification service</a> to send a push. A per-user list of conversations with unread messages makes the inbox view cheap to load.</p>

<h2>Presence and groups</h2>
<ul>
<li><strong>Presence</strong> ("online", "last seen") comes from heartbeats with a TTL. Broadcasting every change to every contact is expensive, so send presence only to contacts who currently have that conversation open, and fetch it on demand otherwise.</li>
<li><strong>Small groups</strong> fan out each message to every member's gateway. <strong>Huge channels</strong> (100,000 members) switch to pull: clients fetch new messages for the channels they're viewing. It's the same trade-off as the <a href="news-feed.html">news feed</a>.</li>
</ul>

<h2>Interview checklist</h2>
<ul class="check">
<li>Choose WebSockets, and say where connection state lives (a session registry).</li>
<li>Route messages through stateless services to the right gateway.</li>
<li>Order with per-conversation sequence numbers and a single writer; dedupe with client message IDs.</li>
<li>Model receipts as per-member watermarks.</li>
<li>Persist first, sync on reconnect, push to offline devices.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="monitoring", short="Monitoring", title="Monitoring and alerting systems",
     dek="Take in a flood of alerts without dropping one, collapse them into incidents a person can act on, and keep working when everything else is on fire.",
     practice="sandbox",
     body=f"""
<p>An alerting system receives alerts from monitoring tools, deduplicates and groups them, decides who to page, and keeps a history. Its hardest requirement is that it must work best exactly when everything else is failing, because that's when alert volume spikes.</p>

{diagram([[B("SOURCES", "Prometheus, apps")], [B("RECEIVERS", "stateless")], [B("KAFKA", "acks=all · RF 3", True)], [B("DEDUPE", "by fingerprint")], [B("CORRELATE", "service graph")], [B("ROUTER", "on-call, escalation")]],
         "Receivers acknowledge only after a durable write. Partitioning by fingerprint gives each alert's state a single owner.")}

<h2>Ingest: 100,000 alerts a minute, none lost</h2>
<p>100,000 a minute is about 1,700 per second on average, and incidents produce storms ten times that. "Without losing any" means three things:</p>
<ul>
<li><strong>Acknowledge only after a durable write.</strong> Receivers are stateless and horizontally scaled. They return success only after Kafka has written the alert to all in-sync replicas (<code>acks=all</code>, replication factor 3).</li>
<li><strong>Senders retry.</strong> Sources keep a local buffer and retry until they get an acknowledgement. That's at-least-once delivery, so the next stage must be idempotent: dedupe on the alert's fingerprint and timestamp.</li>
<li><strong>Absorb storms.</strong> Kafka is the buffer, and processing can fall behind briefly without loss. Track consumer lag, because if it grows, pages arrive late.</li>
</ul>

<h2>Deduplication: key, window, state</h2>
<ul>
<li><strong>Key:</strong> a <strong>fingerprint</strong>, a hash of the alert's identifying labels, for example <code>alertname</code>, <code>service</code>, <code>instance</code> and <code>severity</code>, sorted. This is how Prometheus Alertmanager identifies alerts. Exclude labels that change on every firing, like a current value.</li>
<li><strong>Window:</strong> an alert stays "open" while it keeps firing. A repeat within the window updates <code>last_seen</code> and a count instead of paging again. The alert closes when the source sends "resolved", or when it hasn't been seen for a timeout. A <em>repeat interval</em> (say 4 hours) re-notifies for alerts still open.</li>
<li><strong>State:</strong> partition the Kafka topic by fingerprint, so one consumer owns each fingerprint and keeps its state in memory without distributed locks. Checkpoint that state to a compacted topic or Redis, so a replacement consumer can take over after a rebalance.</li>
</ul>

<h2>Correlation: from alerts to incidents</h2>
<ul>
<li><strong>Group by labels:</strong> alerts with the same <code>service</code> and <code>cluster</code> within a short window become one notification. Alertmanager waits briefly (<code>group_wait</code>) to collect a group before sending it.</li>
<li><strong>Use the dependency graph:</strong> load service dependencies from tracing or a service catalog. When the database and the six APIs that call it all alert within a minute, the upstream-most failing node is the probable cause, and the rest are symptoms.</li>
<li><strong>Inhibit symptoms:</strong> while "database down" is open, suppress "API error rate high" for its dependants (Alertmanager calls these inhibition rules). One page instead of seven.</li>
</ul>

<h2>Storage: hot, cold, retention</h2>
{table(["Data", "Hot (fast, expensive)", "Cold (cheap)", "Retention"], [
    ["Open alerts and incidents", "In memory + PostgreSQL", "", "Until resolved"],
    ["Alert history", "PostgreSQL or Elasticsearch, indexed by service and time", "Parquet files in object storage", "30 days hot, 1–2 years cold"],
    ["Metrics", "Time-series DB at full resolution", "Downsampled rollups (5 min, 1 h)", "15 days raw, a year of rollups"],
])}
<p>Partition history tables by day, so retention means dropping whole partitions, which is much cheaper than <code>DELETE</code> on a large table.</p>

<h2>Monitoring the monitor</h2>
<ul>
<li><strong>Dead man's switch:</strong> an alert that always fires (the "Watchdog" alert in common Prometheus setups) is sent to an external service. If the heartbeat stops arriving, that service pages you through a separate path. Silence is treated as failure.</li>
<li><strong>Independent infrastructure:</strong> run the meta-monitoring in a different region, account or provider, so it doesn't fail together with the system it watches.</li>
<li><strong>Synthetic alerts:</strong> inject a test alert every minute and measure time from ingest to notification. That's your end-to-end health check.</li>
<li><strong>Degrade loudly, once:</strong> when ingest lag is high, mark data as incomplete, suppress "no data" alerts that the lag itself would cause, and send one page about the alerting system rather than hundreds of false ones.</li>
</ul>

<h2>Writing it up</h2>
<p>For a formal design document or a design-round answer, use this order: problem and users; functional and non-functional requirements; numbers; API and data model; architecture diagram; deep dives (ingest durability, dedupe state, correlation); failure modes; trade-offs and what you'd do next. See <a href="design-interview.html">running a design interview</a> for the timing.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Acknowledge only after a durable, replicated write; senders retry; consumers are idempotent.</li>
<li>Define the dedupe fingerprint, the window and who owns the state.</li>
<li>Correlate by labels and the dependency graph; inhibit symptoms.</li>
<li>Split hot and cold storage, with explicit retention.</li>
<li>Monitor the monitor: dead man's switch on independent infrastructure.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="design-interview", short="The interview", title="Running a design interview",
     dek="A system design round is graded on how you get to an answer. Here's a sequence and a clock that keep you in control.",
     practice="sandbox",
     body=f"""
<p>Interviewers rarely have one right design in mind. They're watching whether you clarify the problem, put numbers on it, make reasonable choices, and explain the trade-offs. A fixed sequence keeps you from drawing boxes too early or running out of time in a deep dive.</p>

<h2>The 45-minute clock</h2>
{table(["Minutes", "Step", "What you produce"], [
    ["0–5", "Requirements", "3–5 functional requirements, the non-functional ones (latency, availability, consistency), and what's out of scope"],
    ["5–10", "Estimates", "Users, read and write QPS, storage, bandwidth. See <a href=\"estimation.html\">estimation</a>"],
    ["10–15", "API and data model", "The main endpoints, and the key tables or collections with their keys"],
    ["15–25", "High-level design", "One diagram covering the whole read path and write path"],
    ["25–40", "Deep dives", "Two or three hard parts: scaling the bottleneck, consistency, failure handling"],
    ["40–45", "Wrap-up", "Trade-offs, bottlenecks left, what you'd build next"],
], numeric=(0,))}

<h2>Each step, in practice</h2>
<h3>Requirements</h3>
<p>Ask, then write down what you agreed. "Do we need custom aliases? Analytics? How long do links live?" Then say which requirement dominates: "Redirects must be fast and almost never fail; creation can be slower."</p>
<h3>Estimates</h3>
<p>Round aggressively and say so. The aim is to learn which component is stressed. Finish with a conclusion: "So reads are 100 times writes, and the database can't serve 12,000 lookups a second alone. That means a cache."</p>
<h3>API and data model</h3>
<p>Two or three endpoints with their inputs and outputs, and the main entities with their primary keys. Choose the database here and say why (see <a href="sql-nosql.html">SQL vs NoSQL</a>).</p>
<h3>High-level design</h3>
<p>Draw the simplest design that meets the requirements, then walk one request through it end to end, once for a read and once for a write. Don't add Kafka, sharding or microservices until the numbers ask for them.</p>
<h3>Deep dives</h3>
<p>Pick the parts that are actually hard for this problem: key generation for a shortener, fan-out for a feed, connection state for chat. Interviewers often steer here, so follow their lead. For each part, give two options, choose one, and say what it costs.</p>
<h3>Wrap-up</h3>
<p>Name the next bottleneck and the failure you'd worry about most. That shows you know the design isn't finished.</p>

<h2>Saying trade-offs well</h2>
<div class="math">"I chose X over Y because Z.
 It costs us W.
 I'd revisit it if V changes."</div>
<p>Example: "I chose fan-out on write for most users because feed reads outnumber posts ten to one. It costs us heavy write amplification for big accounts, so I pull those at read time. I'd revisit the threshold if the celebrity share of reads grows."</p>

<h2>Your own project as a design answer</h2>
<p>A system you built and can draw from memory is your strongest answer. Prepare it at two lengths:</p>
<ul>
<li><strong>Two minutes:</strong> the problem, the architecture in one sentence, the one hard thing you solved, and one number that shows scale or impact.</li>
<li><strong>Ten minutes:</strong> the diagram, the request paths, three trade-offs you can defend, and three things you'd do differently now.</li>
</ul>
<p>Rehearse both aloud, timed, at least twice. Recording yourself once is uncomfortable and very effective.</p>

<h2>Common ways to lose points</h2>
<ul>
<li>Drawing boxes before agreeing on requirements and numbers.</li>
<li>Naming technologies without saying what they do for this design ("we'll use Kafka").</li>
<li>Designing for a scale that the estimates don't support.</li>
<li>Spending 20 minutes on one component and never covering the write path.</li>
<li>Never mentioning failure: what happens when this box dies?</li>
</ul>

<h2>Interview checklist</h2>
<ul class="check">
<li>Write down requirements and what's out of scope.</li>
<li>State estimates and the conclusion they lead to.</li>
<li>Walk a read and a write through the diagram.</li>
<li>Deep-dive two hard parts, with options and costs.</li>
<li>End with trade-offs, bottlenecks and next steps.</li>
</ul>
"""),
    ]
    for p in hld:
        p["section"] = "HLD"

    patterns_html = "".join(
        f"<h3>{name}</h3><p>{why}</p>{code(PATTERNS[key])}"
        for key, name, why in [
            ("strategy", "Strategy", "Swap an algorithm without changing its caller. <strong>Use it for</strong> pricing rules, routing, retry policies, parking-spot allocation, elevator dispatch."),
            ("factory", "Factory", "Put the decision of <em>which</em> class to create in one place. <strong>Use it for</strong> picking an implementation by configuration or input type."),
            ("observer", "Observer", "Let many listeners react to an event without the source knowing them. <strong>Use it for</strong> domain events (order placed → reserve stock, send email), UI updates."),
            ("builder", "Builder", "Construct an object with many optional fields readably, and validate it once at the end. <strong>Use it for</strong> requests, configs, immutable value objects."),
            ("decorator", "Decorator", "Add behaviour by wrapping an object in another with the same interface. <strong>Use it for</strong> caching, logging, metrics, retries. Java's <code>BufferedInputStream</code> is one."),
            ("adapter", "Adapter", "Make a class with the wrong interface fit the one your code expects. <strong>Use it for</strong> wrapping third-party SDKs so they can be swapped and faked in tests."),
        ])

    lld = [
# ---------------------------------------------------------------------------
dict(slug="solid-patterns", short="SOLID", title="SOLID and the six patterns worth knowing",
     dek="Principles that keep classes easy to change, and the handful of patterns that come up in almost every low-level design round.",
     exercise="<p>Take a class you've written that does too much. Split it along SRP lines, inject its dependencies (DIP), and replace one <code>switch</code> on a type with a strategy (OCP). Then write down which of the six patterns your result uses.</p>",
     body=f"""
<p>Low-level design rounds ask you to model a small system in classes and write working code. Interviewers look for code that is easy to extend and test. SOLID names the habits that make that true. Use them as a checklist, not a religion.</p>

<h2>S: single responsibility</h2>
<p>A class should have <strong>one reason to change</strong>. If a new CSV format, a new tax rule and a new email provider would all edit the same class, split it.</p>
{code(SRP)}

<h2>O: open for extension, closed for modification</h2>
<p>Add behaviour by adding code, not by editing working code. A <code>switch</code> over types that grows with every feature is the usual warning sign.</p>
{code(OCP)}

<h2>L: Liskov substitution</h2>
<p>A subtype must work anywhere its parent type is expected, without surprises. If a subclass throws on a method its parent supports, or quietly ignores it, the inheritance is wrong.</p>
{code(LSP)}

<h2>I: interface segregation</h2>
<p>Don't make classes implement methods they don't need. Several small interfaces beat one large one.</p>
{code(ISP)}

<h2>D: dependency inversion</h2>
<p>High-level code depends on interfaces, and the concrete classes are passed in (dependency injection). This is the principle that makes code testable: in tests you pass a fake.</p>
{code(DIP)}

<h2>The six patterns worth knowing</h2>
<p>Most LLD problems need only these. Name the pattern when you use it, and say what it buys you.</p>
{patterns_html}

<h2>Why Singleton is usually a mistake</h2>
<p>A classic Singleton (<code>Config.getInstance()</code>) is global state in disguise. Callers hide their dependency on it, tests can't replace it, and its state leaks between tests. Lazy initialisation adds threading bugs on top. It's reasonable for something that really is one per process and holds no state that matters to behaviour, such as a logger or immutable configuration loaded once at startup. Even then, it's better to create one instance at startup and inject it, so you get "only one" without the global access.</p>

<h2>Composition over inheritance</h2>
<p>Inheritance fixes a combination of behaviours at compile time, and the number of subclasses multiplies. Composition builds combinations at runtime from small parts that each do one thing.</p>
{code(COMPOSITION)}
<p>Use inheritance for a true "is a" relationship with a stable parent. Use composition when you're combining behaviours.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Have a real example of each SOLID principle from code you've written.</li>
<li>Have one use case for each of the six patterns.</li>
<li>Explain why Singleton is usually a mistake, and the exception.</li>
<li>Show the same design with inheritance and with composition.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="lru-rate-limiter", short="LRU + rate limiter", title="Coding an LRU cache and a rate limiter",
     dek="Two classics you should be able to write from memory in Java: O(1) LRU eviction and a thread-safe token bucket, with tests.",
     exercise="<p>Close this page and write both classes from scratch in under 40 minutes, then the two tests. If you get stuck, write down exactly where. That's the part to re-derive tomorrow.</p>",
     body=f"""
<p>These two come up constantly, alone or as the first step of a bigger problem. Both reward the same habits: pick the right data structures, make the operations O(1), make them thread-safe, and prove they work with tests. For the theory, see <a href="caching.html">caching</a> and <a href="rate-limiting.html">rate limiting</a>.</p>

<h2>LRU cache in O(1)</h2>
<p>You need two things at once: find any key in O(1), and know which key was used least recently, also in O(1). A <strong>HashMap</strong> gives the first. A <strong>doubly linked list</strong> ordered by use gives the second, because a node can be removed from the middle in O(1) when you already hold a reference to it. The map stores those references.</p>
<ul>
<li><code>get</code>: look up the node, move it to the front, return its value.</li>
<li><code>put</code>: update and move to the front if present. Otherwise, if full, remove the node at the back from both the list and the map, then insert the new node at the front.</li>
<li>Two <strong>sentinel</strong> nodes (head and tail) remove every null check at the ends.</li>
</ul>
{code(LRU)}
<p>Notes for the interview:</p>
<ul>
<li>The node stores its key, so eviction can remove it from the map.</li>
<li><code>synchronized</code> on both methods is correct and simple. <code>ConcurrentHashMap</code> alone wouldn't be enough, because each operation changes the map and the list together. For more throughput, stripe the cache into several independently locked segments by key hash.</li>
<li>In real code, <code>LinkedHashMap</code> does all of this. Mention it, but expect to be asked for the manual version:</li>
</ul>
{code(LRU_LHM)}

<h2>Token bucket rate limiter</h2>
<p>Store the token count and the time of the last refill. On each request, add the tokens earned since then (capped at capacity), then spend one if there is one. No background thread is needed. Pass the clock in, so tests can control time.</p>
{code(BUCKET)}
<ul>
<li>The read-update-write must be atomic, hence <code>synchronized</code>. Without it, two threads could both see one token and both pass.</li>
<li>Use <code>System.nanoTime()</code>, not wall-clock time, which can jump backwards when the clock is adjusted.</li>
</ul>

<h2>Per-user limits without unbounded memory</h2>
<p>One bucket per user ID, created on first use. To stop the map growing forever, cap it and evict the least recently seen user, which is the LRU idea again:</p>
{code(PER_USER)}
<p>Evicting a user is nearly harmless. A bucket idle for longer than capacity ÷ rate seconds would be full anyway, so recreating it changes nothing. Only a recently active user who gets evicted early receives a fresh burst, so size the cap well above the number of active users. In production, a cache library with <code>expireAfterAccess</code> (such as Caffeine) does the same thing, and across many servers the bucket moves to Redis.</p>

<h2>Tests</h2>
<p>Test the behaviour with a fake clock, and test thread safety by hammering a bucket that never refills from several threads:</p>
{code(BUCKET_TEST)}
<p>For the LRU cache, test that a <code>get</code> protects a key from eviction, that updating an existing key doesn't grow the size, and that capacity 1 works.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Explain why the cache needs both a map and a linked list.</li>
<li>Use sentinel nodes, and store the key in the node.</li>
<li>Refill tokens lazily from a monotonic clock.</li>
<li>Make each operation atomic, and say how you'd scale past one lock.</li>
<li>Bound per-user memory, and write tests with a fake clock.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="parking-lot", short="Parking lot", title="Parking lot in 90 minutes",
     dek="The classic LLD problem: clarify, model the entities, leave an extension point, and handle two cars racing for the last spot.",
     exercise="<p>Set a 90-minute timer and build it with no reference material: entities, allocation strategy, fee policy, and a test where 50 threads race for 10 spots. Then add an electric-vehicle spot type and count how many existing classes you had to edit.</p>",
     body=f"""
<p>The parking lot tests whether you can turn a vague prompt into a clean object model and working code within the time limit. Spend the first 10 minutes on questions. They save the next 80.</p>

<h2>A 90-minute plan</h2>
{table(["Minutes", "Do"], [
    ["0–10", "Clarify requirements and agree what's out of scope"],
    ["10–20", "List entities and interfaces; sketch their relationships"],
    ["20–70", "Write the code: model, inventory, allocation, entry and exit, fees"],
    ["70–85", "Write tests, including the concurrency case"],
    ["85–90", "Walk through an extension, such as electric-vehicle spots"],
], numeric=(0,))}

<h2>Questions to ask</h2>
<ul>
<li>Several floors? Which spot sizes, and which vehicles fit which sizes?</li>
<li>Multiple entry and exit gates working at the same time? (Yes, which is the concurrency question.)</li>
<li>How is the fee calculated: hourly, flat, different by spot size?</li>
<li>Do we show free spots per floor? Payments, reservations, lost tickets? Usually out of scope, so say so.</li>
</ul>

<h2>Entities and interfaces</h2>
{code(PARKING_MODEL)}
<p>Two interfaces carry the design. <code>SpotAllocationStrategy</code> decides which spot a vehicle gets, and <code>FeePolicy</code> decides what it pays. Both change often, and both are <a href="solid-patterns.html">strategies</a>, so adding "nearest to the lift" allocation or weekend pricing is a new class, not an edit.</p>

<h2>Two cars, one spot</h2>
<p>If two gates read "spot 17 is free" and then both mark it taken, two cars get the same spot. The fix is to make finding and claiming a spot <strong>one atomic step</strong>. Keep a concurrent queue of free spots per size: <code>poll()</code> removes and returns one element atomically, so two threads can never receive the same spot.</p>
{code(PARKING_INVENTORY)}

<h2>Allocation, fees and the lot</h2>
{code(PARKING_LOT)}
<p>Things worth pointing out as you write it:</p>
<ul>
<li>The lot depends only on interfaces, and the clock is injected, so tests control time.</li>
<li><code>active.remove(ticketId)</code> is atomic, so a ticket can only be used to exit once.</li>
<li>Fees are in <code>long</code> cents. Never use <code>double</code> for money.</li>
</ul>

<h2>If the state lives in a database</h2>
<p>With several servers, the in-memory queue becomes a table, and the atomic claim becomes one SQL statement. <code>FOR UPDATE SKIP LOCKED</code> lets concurrent transactions each grab a different free row rather than queueing on the same one:</p>
{code(PARKING_SQL, lang="sql")}

<h2>The extension point</h2>
<p>Interviewers often end with "now add electric-vehicle charging spots". With this design that means: add <code>EV</code> to the size enum (or a separate feature flag on <code>Spot</code>), an allocation strategy that prefers EV spots for EVs, and perhaps a fee policy that adds charging. Nothing in <code>ParkingLot</code> changes. Say that out loud. It's the point of the exercise.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Spend the first 10 minutes on requirements and scope.</li>
<li>Use strategy interfaces for allocation and pricing.</li>
<li>Make claiming a spot atomic, in memory or in SQL.</li>
<li>Use integer cents and an injected clock.</li>
<li>Test the race, and show one extension.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="splitwise", short="Splitwise", title="Splitwise: expenses, splits and settling up",
     dek="Model shared expenses so equal, exact and percentage splits share one code path, then settle the group in as few payments as practical.",
     exercise="<p>Implement <code>Splits</code> and <code>Group</code>, then test: ₹100 split three ways sums to exactly ₹100; percentages that don't add to 100% are rejected; and after <code>settle()</code>, applying the transfers leaves every balance at zero.</p>",
     body=f"""
<p>Splitwise tracks who paid for what in a group and who owes whom. It's a good LLD problem because it has a real model, a real algorithm, and one classic trap: rounding money.</p>

<h2>The model</h2>
<ul>
<li><strong>User</strong> and <strong>Group</strong> (a set of users).</li>
<li><strong>Expense:</strong> who paid, the total, and how much each participant owes. The owed amounts must add up exactly to the total.</li>
<li><strong>Balance:</strong> for each person, the net amount: what they paid minus what they owe, across all expenses. Positive means others owe them.</li>
<li><strong>Transfer:</strong> a suggested payment from one person to another that settles debts.</li>
</ul>
<p>Store money as <code>long</code> cents (or paise). A ₹100 bill split three ways is 3,334 + 3,333 + 3,333 paise, and someone has to get the extra paisa.</p>

<h2>Three split types, one code path</h2>
<p>The trick: <strong>every split is a weighted split</strong>. Equal is weight 1 each. Percentage is weights in basis points that must add up to 10,000. Exact amounts are weights equal to the amounts, which must add up to the total. So there's one function for the arithmetic, and each split type only validates its input and builds weights.</p>
{code(SPLIT)}
<p>Leftover cents go to the people with the largest remainders (the "largest remainder method"), so every split adds up to the exact total and the extra cent lands where the rounding error was biggest. New types, such as "by shares" (2 shares for an adult, 1 for a child), are just more weights.</p>

<h2>Balances and settling up</h2>
<p>Don't track who owes whom pair by pair. Each expense just adjusts every participant's <strong>net balance</strong>. To settle up, match people who owe with people who are owed:</p>
{code(LEDGER)}
<p>The greedy algorithm always pays the largest debt to the largest credit. Each transfer settles at least one person completely, so a group of n people needs <strong>at most n − 1 transfers</strong>, and with two heaps it runs in <strong>O(n log n)</strong>.</p>
<div class="note"><p><strong>Is it optimal?</strong> Not always. Finding the true minimum number of transfers is NP-hard: it's equivalent to splitting the balances into as many groups that sum to zero as possible. For small groups you can solve it exactly with a search over subsets in O(2ⁿ) (LeetCode 465, "Optimal Account Balancing"). In an interview, say that greedy is the practical answer, give its bound, and mention the exact version.</p></div>

<h2>Things to mention</h2>
<ul>
<li><strong>Who can edit:</strong> editing or deleting an expense reverses its old balance changes, then applies the new ones. Keep expenses append-only with a history, so balances can always be recomputed.</li>
<li><strong>Currencies:</strong> balances per currency, or convert at the expense date's rate and store that rate.</li>
<li><strong>Concurrency:</strong> two people adding expenses at once. Updating balances inside a transaction (or recomputing from expenses) keeps them consistent.</li>
</ul>

<h2>Interview checklist</h2>
<ul class="check">
<li>Model users, groups, expenses, owed amounts and net balances.</li>
<li>Use integer money, and say how leftover cents are distributed.</li>
<li>One weighted-split code path, with validation per split type.</li>
<li>Greedy settlement with two heaps: at most n − 1 transfers, O(n log n).</li>
<li>Know that the true minimum is NP-hard, and the subset-search alternative.</li>
</ul>
"""),
# ---------------------------------------------------------------------------
dict(slug="elevator", short="Elevator", title="Elevator system: state machine and scheduling",
     dek="Model each car as a state machine that refuses illegal moves, and keep the dispatch policy swappable.",
     exercise="<p>Write the <code>State</code> enum and a test that every illegal transition throws. Then simulate one car with stops at floors 5, 2 and 8 starting from floor 3 going up, and check that LOOK visits 5, 8, then 2.</p>",
     body=f"""
<p>The elevator problem has two parts that interviewers probe separately: the <strong>state machine</strong> for one car (what it may do next) and the <strong>scheduling</strong> across cars (which car answers a call). Keeping them separate is most of the design.</p>

<h2>Requirements to confirm</h2>
<ul>
<li>N cars, M floors. <strong>Hall calls</strong> (someone on floor 6 presses "down") and <strong>car calls</strong> (someone inside presses 2).</li>
<li>Doors must be closed while moving. A car can be taken out of service.</li>
<li>Out of scope unless asked: weight limits, express zones, emergency modes.</li>
</ul>

<h2>The state machine</h2>
{table(["From", "Allowed next states"], [
    ["IDLE", "MOVING_UP, MOVING_DOWN, DOORS_OPEN, OUT_OF_SERVICE"],
    ["MOVING_UP", "DOORS_OPEN (arrived at a stop), OUT_OF_SERVICE"],
    ["MOVING_DOWN", "DOORS_OPEN, OUT_OF_SERVICE"],
    ["DOORS_OPEN", "DOORS_CLOSING"],
    ["DOORS_CLOSING", "DOORS_OPEN (something in the way), IDLE, MOVING_UP, MOVING_DOWN"],
    ["OUT_OF_SERVICE", "IDLE"],
])}
<p>The illegal transitions are the interesting part: moving with the doors open (<code>DOORS_OPEN → MOVING_*</code>), reversing direction without stopping (<code>MOVING_UP → MOVING_DOWN</code>), and moving straight out of maintenance. Encode the table once and enforce it in one place:</p>
{code(ELEVATOR_STATE)}

<h2>One car: the LOOK algorithm</h2>
<p>First-come-first-served makes a car zigzag. The classic fix comes from disk scheduling. <strong>SCAN</strong> keeps moving in one direction to the end of the shaft, serving stops on the way, then reverses. <strong>LOOK</strong> reverses as soon as there are no more stops ahead, which is what real elevators do. Two sorted sets of stops, above and below the car, make "next stop in this direction" an O(log n) lookup:</p>
{code(ELEVATOR_CAR)}

<h2>Many cars: a swappable dispatch strategy</h2>
<p>Which car should answer a hall call? A good default: the nearest car that is idle or already heading towards the caller in the same direction, with a penalty for cars that would have to turn around. Real buildings change policy by time of day, sending idle cars to the lobby in the morning rush, so dispatch is a <a href="solid-patterns.html">strategy</a>:</p>
{code(ELEVATOR_DISPATCH)}

<h2>Concurrency</h2>
<p>Buttons are pressed from many places at once. The simplest safe structure: each car is driven by its own single-threaded controller, an event loop that takes stops from a thread-safe queue, so a car's state is only ever changed by one thread. The dispatcher only adds stops to cars. With <code>synchronized</code> methods on the car, as above, the state machine stays consistent either way.</p>

<h2>Interview checklist</h2>
<ul class="check">
<li>Separate per-car state from dispatch across cars.</li>
<li>Write the transition table, and name the illegal transitions.</li>
<li>Enforce transitions in one method that throws.</li>
<li>Explain SCAN vs LOOK, implemented with sorted sets.</li>
<li>Make dispatch a strategy, and say how you'd swap it.</li>
</ul>
"""),
    ]
    for p in lld:
        p["section"] = "LLD"
    return hld + lld
