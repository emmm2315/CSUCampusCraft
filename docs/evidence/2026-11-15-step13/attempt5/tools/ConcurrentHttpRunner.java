import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** New external STEP13 tool. Private input is read from stdin and never echoed or written. */
public final class ConcurrentHttpRunner {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern BCRYPT = Pattern.compile("\\$2[aby]\\$\\d\\d\\$[./A-Za-z0-9]{53}");
    private static final Pattern INPUT = Pattern.compile("<input\\b[^>]*>", Pattern.CASE_INSENSITIVE);
    private static final Pattern NAME = Pattern.compile("\\bname=[\"']([^\"']*)[\"']", Pattern.CASE_INSENSITIVE);
    private static final Pattern VALUE = Pattern.compile("(\\bvalue=[\"'])[^\"']*([\"'])", Pattern.CASE_INSENSITIVE);
    private static final Set<String> PRIVATE_FIELDS = Set.of("_csrf", "confirmationToken", "password", "receiverName", "receiverPhone", "receiverAddress");

    private static String hash(byte[] data) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
    }
    private static String redact(String text, List<String> privateValues) {
        String value = text;
        for (String secret : privateValues) if (secret != null && secret.length() >= 4) value = value.replace(secret, "[REDACTED]");
        value = BCRYPT.matcher(value).replaceAll("[REDACTED-HASH]");
        Matcher inputs = INPUT.matcher(value);
        StringBuffer out = new StringBuffer();
        while (inputs.find()) {
            String tag = inputs.group();
            Matcher name = NAME.matcher(tag);
            if (name.find() && PRIVATE_FIELDS.contains(name.group(1))) tag = VALUE.matcher(tag).replaceAll("$1[REDACTED]$2");
            inputs.appendReplacement(out, Matcher.quoteReplacement(tag));
        }
        inputs.appendTail(out);
        value = out.toString().replaceAll("(?is)(<textarea\\b[^>]*\\bname=[\"'](?:receiverName|receiverPhone|receiverAddress)[\"'][^>]*>).*?(</textarea>)", "$1[REDACTED]$2");
        value = value.replaceAll("(?is)(<([a-z][a-z0-9]*)\\b[^>]*\\bdata-(?:shipping-value|customer-contact)(?:=[\"'][^\"']*[\"'])?[^>]*>).*?(</\\2>)", "$1[REDACTED]$3");
        return value.replaceAll("(?i);CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9.-]+", ";CSUCAMPUSCRAFT_SESSION=[REDACTED]");
    }
    private static List<String> privateValues(JsonNode input) {
        List<String> values = new ArrayList<>();
        for (JsonNode node : input.path("private_values")) values.add(node.asText());
        JsonNode jdbc = input.path("jdbc");
        if (jdbc.has("password")) values.add(jdbc.get("password").asText());
        for (JsonNode request : input.path("requests")) {
            request.path("headers").fields().forEachRemaining(field -> {
                if (field.getKey().equalsIgnoreCase("Cookie")) {
                    for (String cookie : field.getValue().asText().split(";")) {
                        int equals = cookie.indexOf('=');
                        if (equals >= 0) values.add(cookie.substring(equals + 1).strip());
                    }
                }
            });
            request.path("private_form_values").forEach(v -> values.add(v.asText()));
        }
        return values;
    }
    private static Connection connection(JsonNode jdbc, String schema) throws Exception {
        Connection connection = DriverManager.getConnection(jdbc.required("url").asText(), jdbc.required("user").asText(), jdbc.required("password").asText());
        try (var statement = connection.createStatement()) {
            statement.execute("SET SESSION time_zone='+00:00'");
            try (ResultSet result = statement.executeQuery("SELECT DATABASE()")) {
                if (!result.next() || !schema.equals(result.getString(1))) throw new IllegalArgumentException("Isolated schema mismatch");
            }
        }
        return connection;
    }
    private static List<Map<String,Object>> waits(Connection observer, String schema, long blockerId) throws Exception {
        String sql = "SELECT rt.PROCESSLIST_ID,bt.PROCESSLIST_ID,l.OBJECT_SCHEMA,l.OBJECT_NAME,l.INDEX_NAME,l.LOCK_TYPE,l.LOCK_MODE,l.LOCK_STATUS,l.LOCK_DATA "
                + "FROM performance_schema.data_lock_waits w "
                + "JOIN performance_schema.threads rt ON rt.THREAD_ID=w.REQUESTING_THREAD_ID "
                + "JOIN performance_schema.threads bt ON bt.THREAD_ID=w.BLOCKING_THREAD_ID "
                + "JOIN performance_schema.data_locks l ON l.ENGINE=w.ENGINE AND l.ENGINE_LOCK_ID=w.REQUESTING_ENGINE_LOCK_ID "
                + "WHERE l.OBJECT_SCHEMA=? AND bt.PROCESSLIST_ID=? ORDER BY rt.PROCESSLIST_ID,l.OBJECT_NAME";
        List<Map<String,Object>> rows = new ArrayList<>();
        try (PreparedStatement query = observer.prepareStatement(sql)) {
            query.setString(1, schema); query.setLong(2, blockerId);
            try (ResultSet result = query.executeQuery()) {
                while (result.next()) {
                    Map<String,Object> row = new LinkedHashMap<>();
                    row.put("requesting_connection_id", result.getLong(1));
                    row.put("blocking_connection_id", result.getLong(2));
                    row.put("schema", result.getString(3)); row.put("table", result.getString(4));
                    row.put("index", result.getString(5)); row.put("lock_type", result.getString(6));
                    row.put("lock_mode", result.getString(7)); row.put("lock_status", result.getString(8));
                    String data = result.getString(9);
                    row.put("lock_data", data == null || data.matches("[0-9, ]+|supremum pseudo-record") ? data : "[REDACTED-NONNUMERIC-LOCK-DATA]");
                    rows.add(row);
                }
            }
        }
        return rows;
    }
    private static Map<String,Object> request(JsonNode specification, CountDownLatch ready, CountDownLatch go,
                                               List<String> privateValues, long originNano) {
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("name", specification.path("name").asText());
        try {
            URI uri = URI.create(specification.required("url").asText());
            if (!"http".equals(uri.getScheme()) || !"127.0.0.1".equals(uri.getHost())
                    || !Set.of(8080,8081,18080,18081).contains(uri.getPort())) throw new IllegalArgumentException("Only isolated loopback app endpoints are allowed");
            String method = specification.path("method").asText("POST");
            if (!Set.of("GET", "POST").contains(method)) throw new IllegalArgumentException("Unexpected request method");
            HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10)).followRedirects(HttpClient.Redirect.NEVER).version(HttpClient.Version.HTTP_1_1).build();
            HttpRequest.Builder builder = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(60)).header("Accept", "text/html");
            specification.path("headers").fields().forEachRemaining(field -> builder.header(field.getKey(), field.getValue().asText()));
            if ("POST".equals(method)) builder.header("Content-Type", "application/x-www-form-urlencoded").POST(HttpRequest.BodyPublishers.ofString(specification.path("form_body").asText(), StandardCharsets.UTF_8));
            else builder.GET();
            HttpRequest request = builder.build();
            result.put("method", method); result.put("port", uri.getPort()); result.put("path", uri.getRawPath());
            ready.countDown();
            if (!go.await(20, TimeUnit.SECONDS)) throw new IllegalStateException("No release signal");
            result.put("started_at_utc", Instant.now().toString());
            result.put("started_offset_ns", System.nanoTime() - originNano);
            long start = System.nanoTime();
            HttpResponse<byte[]> response = client.send(request, HttpResponse.BodyHandlers.ofByteArray());
            long finish = System.nanoTime();
            result.put("finished_at_utc", Instant.now().toString());
            result.put("finished_offset_ns", finish - originNano);
            result.put("elapsed_ns", finish - start);
            String raw = new String(response.body(), StandardCharsets.UTF_8);
            result.put("status", response.statusCode());
            result.put("location", redact(response.headers().firstValue("Location").orElse(""), privateValues));
            result.put("content_type", response.headers().firstValue("Content-Type").orElse(""));
            result.put("raw_body_sha256", hash(response.body())); result.put("raw_body_bytes", response.body().length);
            result.put("raw_bcrypt_present", BCRYPT.matcher(raw).find());
            result.put("raw_session_url_tracking", raw.contains(";CSUCAMPUSCRAFT_")
                    || response.headers().firstValue("Location").orElse("").contains(";CSUCAMPUSCRAFT_"));
            boolean rawCredential = false;
            for (JsonNode credential : specification.path("credential_values")) {
                if (!credential.asText().isEmpty() && raw.contains(credential.asText())) rawCredential = true;
            }
            result.put("raw_known_credential_present", rawCredential);
            result.put("redacted_body", redact(raw, privateValues));
            result.put("cookie_or_csrf_values_recorded", false);
            result.put("completed", true);
        } catch (Throwable failed) {
            ready.countDown();
            result.put("completed", false); result.put("failure_class", failed.getClass().getName());
            result.put("finished_at_utc", Instant.now().toString());
            result.put("finished_offset_ns", System.nanoTime() - originNano);
        }
        return result;
    }
    private static Map<String,Object> run(JsonNode input) throws Exception {
        String scenario = input.required("scenario").asText();
        if (!scenario.matches("[A-Za-z0-9_-]{1,64}")) throw new IllegalArgumentException("Unsafe scenario name");
        JsonNode specifications = input.required("requests");
        if (!specifications.isArray() || specifications.size() != 2) throw new IllegalArgumentException("Exactly two independent request workers required");
        String schema = input.required("schema").asText();
        if (!schema.matches("[A-Za-z0-9_]{1,64}")) throw new IllegalArgumentException("Unsafe isolated schema");
        long originNano = System.nanoTime();
        Map<String,Object> result = new LinkedHashMap<>();
        result.put("scenario", scenario); result.put("started_at_utc", Instant.now().toString());
        result.put("synchronization", "Two independent HttpClient/worker threads, CountDownLatch ready and common release; no redirects or retries");
        result.put("database_window", "One common before/after is supplied by caller; concurrent responses have no invented per-request isolated zero-write claim");
        ExecutorService pool = Executors.newFixedThreadPool(2);
        Connection gate = null, observer = null;
        try {
            JsonNode gateSpecification = input.required("gate");
            String table = gateSpecification.required("table").asText();
            if (!Set.of("store_user", "product", "sales_order").contains(table)) throw new IllegalArgumentException("Unexpected gate table");
            long id = gateSpecification.required("id").asLong();
            if (id <= 0) throw new IllegalArgumentException("Gate ID must be positive");
            int minimumWaiters = gateSpecification.path("minimum_waiters").asInt(2);
            if (minimumWaiters < 1 || minimumWaiters > 2) throw new IllegalArgumentException("Unexpected waiter threshold");
            gate = connection(input.required("jdbc"), schema); observer = connection(input.required("jdbc"), schema);
            gate.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED); gate.setAutoCommit(false);
            long gateId;
            try (var statement = gate.createStatement(); ResultSet current = statement.executeQuery("SELECT CONNECTION_ID()")) { current.next(); gateId = current.getLong(1); }
            String orderNumber = null;
            if ("sales_order".equals(table)) {
                // Business order reads use the unique order_no index. Holding only PRIMARY would
                // let the first worker own the secondary key while the other waits behind it.
                try (PreparedStatement lookup = gate.prepareStatement("SELECT order_no FROM sales_order WHERE id=?")) {
                    lookup.setLong(1,id);
                    try (ResultSet row = lookup.executeQuery()) {
                        if (!row.next()) throw new IllegalStateException("Order gate fixture is absent");
                        orderNumber = row.getString(1);
                    }
                }
            }
            String lockSql = "sales_order".equals(table)
                    ? "SELECT id FROM sales_order WHERE order_no=? FOR UPDATE"
                    : "SELECT id FROM " + table + " WHERE id=? FOR UPDATE";
            try (PreparedStatement lock = gate.prepareStatement(lockSql)) {
                if (orderNumber == null) lock.setLong(1,id); else lock.setString(1,orderNumber);
                try (ResultSet row = lock.executeQuery()) {
                    if (!row.next() || row.getLong(1) != id) throw new IllegalStateException("Gate fixture is absent or inconsistent");
                }
            }
            Map<String,Object> gateRecord = new LinkedHashMap<>();
            gateRecord.put("table", table); gateRecord.put("id", id); gateRecord.put("connection_id", gateId);
            gateRecord.put("lock_predicate", orderNumber == null ? "PRIMARY id" : "Unique order_no resolved from the supplied id; same index as both real business requests");
            gateRecord.put("purpose", "External read-only locking transaction to make real HTTP Service contention observable; not a replacement for business requests");
            gateRecord.put("acquired_at_utc", Instant.now().toString()); gateRecord.put("minimum_waiters", minimumWaiters);
            result.put("gate", gateRecord);
            CountDownLatch ready = new CountDownLatch(2), go = new CountDownLatch(1);
            List<String> secrets = privateValues(input);
            List<Future<Map<String,Object>>> futures = new ArrayList<>();
            for (JsonNode specification : specifications) futures.add(pool.submit(() -> request(specification, ready, go, secrets, originNano)));
            if (!ready.await(20, TimeUnit.SECONDS)) throw new IllegalStateException("Workers did not become ready");
            result.put("release_at_utc", Instant.now().toString()); result.put("release_offset_ns", System.nanoTime() - originNano); go.countDown();
            long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(12);
            List<Map<String,Object>> samples = new ArrayList<>(); Set<Long> observed = new HashSet<>();
            int maximumSimultaneousWaiters = 0;
            String previousSignature = null;
            while (System.nanoTime() < deadline) {
                List<Map<String,Object>> waiting = waits(observer, schema, gateId);
                long currentWaiters = waiting.stream().map(row -> row.get("requesting_connection_id")).distinct().count();
                maximumSimultaneousWaiters = Math.max(maximumSimultaneousWaiters, (int) currentWaiters);
                for (Map<String,Object> row : waiting) observed.add(((Number) row.get("requesting_connection_id")).longValue());
                String signature = JSON.writeValueAsString(waiting);
                if (!signature.equals(previousSignature) || !waiting.isEmpty()) {
                    samples.add(Map.of("at_utc", Instant.now().toString(), "offset_ns", System.nanoTime()-originNano, "waiting", waiting));
                    previousSignature = signature;
                }
                if (currentWaiters >= minimumWaiters) break;
                Thread.sleep(10);
            }
            gateRecord.put("wait_samples", samples); gateRecord.put("observed_waiting_connection_ids", observed.stream().sorted().toList());
            gateRecord.put("maximum_simultaneous_waiters", maximumSimultaneousWaiters);
            gateRecord.put("threshold_observed", maximumSimultaneousWaiters >= minimumWaiters);
            gate.commit(); gateRecord.put("released_at_utc", Instant.now().toString()); gateRecord.put("released_offset_ns", System.nanoTime()-originNano);
            gateRecord.put("gate_dml", false);
            List<Map<String,Object>> responses = new ArrayList<>();
            for (Future<Map<String,Object>> future : futures) responses.add(future.get(75, TimeUnit.SECONDS));
            result.put("responses", responses);
            result.put("completed", responses.stream().allMatch(r -> Boolean.TRUE.equals(r.get("completed"))));
            result.put("finished_at_utc", Instant.now().toString());
            result.put("caller_must_validate_business_outcome", true);
            return result;
        } finally {
            if (gate != null) { try { gate.rollback(); } finally { gate.close(); } }
            if (observer != null) observer.close();
            pool.shutdownNow(); pool.awaitTermination(5, TimeUnit.SECONDS);
        }
    }
    public static void main(String[] args) throws Exception {
        try {
            JsonNode input = JSON.readTree(System.in);
            System.out.println(JSON.writeValueAsString(run(input)));
        } catch (Throwable failed) {
            System.out.println(JSON.writeValueAsString(Map.of("completed", false, "failure_class", failed.getClass().getName(), "private_input_or_exception_message_recorded", false)));
            System.exit(1);
        }
    }
}
