package org.csucampuscraft.storefront.checkout;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.lang.reflect.Proxy;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import javax.sql.DataSource;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;
import org.apache.ibatis.session.RowBounds;
import org.apache.ibatis.session.SqlSessionFactory;
import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartItemMapper;
import org.csucampuscraft.storefront.cart.CartLine;
import org.csucampuscraft.storefront.cart.CartPage;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;

/** External native probe of the built STEP08 classes, with no test framework or repository hook. */
public final class NativeCheckoutProbe {
    private static final List<Map<String, Object>> checks = new ArrayList<>();
    private static final List<Map<String, Object>> sqlEvents = new ArrayList<>();
    private static final SessionSupport sessions = new SessionSupport();
    private static final Instant BASE = Instant.parse("2026-11-14T00:00:00.123456Z");

    private static void check(String name, boolean condition) {
        checks.add(Map.of("name", name, "passed", condition));
        if (!condition) throw new AssertionError(name);
    }

    private static final class MutableClock extends Clock {
        Instant current = BASE;
        public ZoneId getZone() { return ZoneOffset.UTC; }
        public Clock withZone(ZoneId zone) { return Clock.fixed(current, zone); }
        public Instant instant() { return current; }
    }

    private static final class SessionState {
        final Map<String, Object> values = new HashMap<>();
        boolean valid = true;
        final HttpSession proxy = (HttpSession) Proxy.newProxyInstance(
                HttpSession.class.getClassLoader(), new Class<?>[]{HttpSession.class}, (p, m, a) -> {
                    if (m.getName().equals("equals")) return p == a[0];
                    if (m.getName().equals("hashCode")) return System.identityHashCode(p);
                    if (m.getName().equals("toString")) return "ProbeSession[REDACTED]";
                    if (!valid) throw new IllegalStateException("Session ended");
                    return switch (m.getName()) {
                        case "getAttribute" -> values.get((String) a[0]);
                        case "setAttribute" -> { values.put((String) a[0], a[1]); yield null; }
                        case "removeAttribute" -> { values.remove((String) a[0]); yield null; }
                        case "getAttributeNames" -> Collections.enumeration(values.keySet());
                        case "getCreationTime", "getLastAccessedTime" -> BASE.toEpochMilli();
                        case "getId" -> "probe-session-redacted";
                        case "getMaxInactiveInterval" -> 1800;
                        case "isNew" -> false;
                        case "invalidate" -> { valid = false; values.clear(); yield null; }
                        default -> primitiveDefault(m.getReturnType());
                    };
                });
    }

    private static final class RequestState {
        final SessionState session;
        final Map<String, Object> attributes = new HashMap<>();
        final HttpServletRequest request;

        RequestState(long userId) { this(new SessionState(), userId); }

        RequestState(SessionState session, long userId) {
            this.session = session;
            identity(userId);
            request = (HttpServletRequest) Proxy.newProxyInstance(HttpServletRequest.class.getClassLoader(),
                    new Class<?>[]{HttpServletRequest.class}, (p, m, a) -> {
                        if (m.getName().equals("equals")) return p == a[0];
                        if (m.getName().equals("hashCode")) return System.identityHashCode(p);
                        if (m.getName().equals("toString")) return "ProbeRequest[REDACTED]";
                        return switch (m.getName()) {
                            case "getSession" -> session.valid ? session.proxy : null;
                            case "getAttribute" -> attributes.get((String) a[0]);
                            case "setAttribute" -> { attributes.put((String) a[0], a[1]); yield null; }
                            case "removeAttribute" -> { attributes.remove((String) a[0]); yield null; }
                            case "getAttributeNames" -> Collections.enumeration(attributes.keySet());
                            case "getMethod" -> "POST";
                            case "getRequestURI", "getServletPath" -> "/orders";
                            case "getContextPath" -> "";
                            case "changeSessionId" -> "probe-new-session-redacted";
                            default -> primitiveDefault(m.getReturnType());
                        };
                    });
        }

        void identity(long userId) {
            session.values.put(SessionSupport.IDENTITY_ATTRIBUTE,
                    new SessionIdentity(userId, LocalDateTime.of(2026, 11, 14, 0, 0, 0, 123456000)));
            attributes.put(SessionSupport.CURRENT_USER_ATTRIBUTE,
                    new AuthUser(userId, "probe", "Probe", "CUSTOMER"));
        }
    }

    private static Object primitiveDefault(Class<?> type) {
        if (type == boolean.class) return false;
        if (type == int.class) return 0;
        if (type == long.class) return 0L;
        if (type == double.class) return 0D;
        if (type == float.class) return 0F;
        if (type == short.class) return (short) 0;
        if (type == byte.class) return (byte) 0;
        if (type == char.class) return (char) 0;
        return null;
    }

    private static final class FakeCartService extends CartService {
        CartPage page;
        int reads;
        long readUser;
        RuntimeException failure;
        FakeCartService() { super(null, null); reset(); }
        @Override public CartPage read(long userId) {
            reads++;
            readUser = userId;
            if (failure != null) throw failure;
            return page;
        }
        void reset() {
            failure = null;
            page = page(line(101, 1001, 2, 7, "18.00", 100, "ON_SALE"),
                    line(102, 1002, 1, 0, "49.00", 12, "ON_SALE"));
        }
    }

    private static void set(Object object, String fieldName, Object value) {
        try {
            Field field = object.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            field.set(object, value);
        } catch (ReflectiveOperationException failure) { throw new IllegalStateException("Fixture setup failed"); }
    }

    private static CartLine line(long itemId, long productId, int quantity, long version,
                                 String price, int stock, String status) {
        CartLine line = new CartLine();
        set(line, "id", itemId);
        set(line, "productId", productId);
        set(line, "quantity", quantity);
        set(line, "version", version);
        set(line, "price", new BigDecimal(price));
        set(line, "stock", stock);
        set(line, "status", status);
        set(line, "sku", "PROBE-" + productId);
        set(line, "name", "Probe item");
        set(line, "coverImage", "images/catalog-placeholder.svg");
        return line;
    }

    private static CartPage page(CartLine... lines) {
        long quantity = 0;
        int invalid = 0;
        BigDecimal total = new BigDecimal("0.00");
        for (CartLine line : lines) {
            quantity += line.getQuantity();
            if (line.isValid()) total = total.add(line.getPrice().multiply(BigDecimal.valueOf(line.getQuantity())));
            else invalid++;
        }
        return new CartPage(List.of(lines), quantity, total, invalid);
    }

    private static MultiValueMap<String, String> form(String token) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.set("confirmationToken", token);
        form.set("receiverName", "  Probe  ");
        form.set("receiverPhone", " 1 ");
        form.set("receiverAddress", " X ");
        return form;
    }

    private static void conflict(String name, String code, Runnable action) {
        try { action.run(); check(name, false); }
        catch (BusinessException failure) {
            check(name + "-status", failure.getStatus().value() == 409);
            check(name + "-code", code.equals(failure.getCode()));
        }
    }

    private static void assertCleared(String name, RequestState request) {
        check(name, !request.session.values.containsKey(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE));
    }

    private static CheckoutConfirmation prepare(CheckoutService service, FakeCartService carts,
                                                 MutableClock clock, RequestState request) {
        carts.reset();
        clock.current = BASE;
        return service.prepare(request.request);
    }

    private static void controlled() throws Exception {
        FakeCartService carts = new FakeCartService();
        MutableClock clock = new MutableClock();
        CheckoutService service = new CheckoutService(carts, sessions, Duration.ofMinutes(10), clock);
        RequestState request = new RequestState(1);
        CheckoutConfirmation confirmation = service.prepare(request.request);
        check("snapshot-current-session-attribute", request.session.values.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) == confirmation);
        check("snapshot-current-user-only-read", carts.readUser == 1 && carts.reads == 1);
        check("snapshot-user", confirmation.getUserId() == 1);
        check("snapshot-instant-utc-microsecond-preserved", confirmation.getCreatedAt().equals(BASE));
        check("snapshot-default-ten-minute-duration", Duration.between(confirmation.getCreatedAt(), confirmation.getExpiresAt()).equals(Duration.ofMinutes(10)));
        check("snapshot-full-cart-item-count", confirmation.getItemCount() == 2);
        check("snapshot-full-cart-quantity", confirmation.getQuantity() == 3);
        check("snapshot-server-total-85", confirmation.getTotal().equals(new BigDecimal("85.00")));
        CheckoutLine first = confirmation.getItems().get(0);
        check("snapshot-line-identifiers-and-version", first.itemId() == 101 && first.productId() == 1001 && first.itemVersion() == 7);
        check("snapshot-line-quantity-current-price-subtotal", first.quantity() == 2 && first.unitPrice().equals(new BigDecimal("18.00")) && first.subtotal().equals(new BigDecimal("36.00")));
        try { confirmation.getItems().clear(); check("snapshot-items-unmodifiable", false); }
        catch (UnsupportedOperationException expected) { check("snapshot-items-unmodifiable", true); }
        set(carts.page.items().get(0), "quantity", 9);
        set(carts.page.items().get(0), "price", new BigDecimal("1.00"));
        set(carts.page.items().get(0), "name", "Changed source projection");
        check("snapshot-detached-from-mutable-mapper-line", first.quantity() == 2 && first.unitPrice().equals(new BigDecimal("18.00")) && first.name().equals("Probe item"));
        List<CheckoutLine> original = new ArrayList<>(confirmation.getItems());
        CheckoutConfirmation copy = new CheckoutConfirmation(confirmation.token(), BASE, BASE.plusSeconds(600), 1, original, confirmation.getTotal());
        original.clear();
        check("snapshot-constructor-defensive-list-copy", copy.getItems().size() == 2);
        check("snapshot-fields-final", List.of(CheckoutConfirmation.class.getDeclaredFields()).stream().allMatch(f -> Modifier.isFinal(f.getModifiers())));
        check("snapshot-line-immutable-record", CheckoutLine.class.isRecord());
        check("snapshot-no-receiver-fields", List.of(CheckoutConfirmation.class.getDeclaredFields()).stream().noneMatch(f -> f.getName().toLowerCase(Locale.ROOT).contains("receiver")));
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ObjectOutputStream output = new ObjectOutputStream(bytes)) { output.writeObject(copy); }
        CheckoutConfirmation restored;
        try (ObjectInputStream input = new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray()))) { restored = (CheckoutConfirmation) input.readObject(); }
        check("snapshot-session-serialization-preserves-values", restored.getItems().equals(copy.getItems()) && restored.getTotal().equals(copy.getTotal()) && restored.token().equals(copy.token()));
        check("snapshot-to-string-redacts-token", !confirmation.toString().contains(confirmation.token()));
        check("shipping-to-string-redacted", new ShippingForm("private-name", "private-phone", "private-address").toString().equals("ShippingForm[REDACTED]"));

        Set<String> generated = new HashSet<>();
        boolean entropy = true;
        for (int i = 0; i < 128; i++) {
            CheckoutConfirmation generatedConfirmation = prepare(service, carts, clock, request);
            String token = generatedConfirmation.token();
            entropy &= token.matches("[A-Za-z0-9_-]{43}") && Base64.getUrlDecoder().decode(token).length == 32;
            generated.add(token);
        }
        check("token-base64url-exactly-32-random-bytes-128-observations", entropy);
        check("token-128-observed-distinct-values", generated.size() == 128);
        Value defaultValue = CheckoutService.class.getConstructors()[0].getParameters()[2].getAnnotation(Value.class);
        check("ttl-property-declares-PT10M-default", defaultValue != null && defaultValue.value().equals("${csucampuscraft.checkout.confirmation-ttl:PT10M}"));
        for (Duration invalid : List.of(Duration.ZERO, Duration.ofSeconds(-1))) {
            try { new CheckoutService(carts, sessions, invalid, clock); check("ttl-reject-" + invalid, false); }
            catch (IllegalArgumentException expected) { check("ttl-reject-" + invalid, true); }
        }
        try { new CheckoutService(carts, sessions, Duration.ofSeconds(Long.MAX_VALUE), clock); check("ttl-reject-overflow", false); }
        catch (java.time.DateTimeException | ArithmeticException expected) { check("ttl-reject-overflow", true); }

        CheckoutConfirmation latest = prepare(service, carts, clock, request);
        CheckoutService.Validation valid = service.validate(request.request, form(latest.token()));
        check("valid-shipping-passes-validation-only", valid.isValid());
        check("valid-fields-trimmed", valid.form().receiverName().equals("Probe") && valid.form().receiverPhone().equals("1") && valid.form().receiverAddress().equals("X"));
        check("validation-keeps-confirmation-no-order-success", request.session.values.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) == latest);
        check("validation-result-to-string-secret-safe", !valid.toString().contains(latest.token()) && !valid.toString().contains("Probe"));
        check("session-stores-no-shipping", request.session.values.keySet().equals(Set.of(SessionSupport.IDENTITY_ATTRIBUTE, SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE)));
        MultiValueMap<String, String> tampered = form(latest.token());
        tampered.set("total", "0.01"); tampered.set("unitPrice", "0.01"); tampered.set("quantity", "99"); tampered.set("userId", "999");
        CheckoutService.Validation ignored = service.validate(request.request, tampered);
        check("client-amount-quantity-userid-not-authoritative", ignored.isValid() && ignored.confirmation().getTotal().equals(new BigDecimal("85.00")) && ignored.confirmation().getQuantity() == 3 && ignored.confirmation().getUserId() == 1);

        MultiValueMap<String, String> missing = new LinkedMultiValueMap<>(); missing.set("confirmationToken", latest.token());
        CheckoutService.Validation empty = service.validate(request.request, missing);
        check("missing-fields-aggregate-all-errors", empty.fieldErrors().keySet().equals(Set.of("receiverName", "receiverPhone", "receiverAddress")));
        check("field-errors-preserve-still-valid-token", request.session.values.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) == latest);
        for (Map.Entry<String, Integer> limit : Map.of("receiverName", 50, "receiverPhone", 30, "receiverAddress", 255).entrySet()) {
            MultiValueMap<String, String> boundary = form(latest.token());
            boundary.set(limit.getKey(), "\uD83C\uDF93".repeat(limit.getValue()));
            check("unicode-codepoint-boundary-" + limit.getKey(), service.validate(request.request, boundary).isValid());
            boundary.set(limit.getKey(), "\uD83C\uDF93".repeat(limit.getValue() + 1));
            check("unicode-codepoint-overlong-" + limit.getKey(), service.validate(request.request, boundary).fieldErrors().containsKey(limit.getKey()));
            boundary.set(limit.getKey(), " \t\n ");
            check("trimmed-empty-" + limit.getKey(), service.validate(request.request, boundary).fieldErrors().containsKey(limit.getKey()));
        }
        MultiValueMap<String, String> duplicate = form(latest.token()); duplicate.add("receiverName", "second");
        check("duplicate-shipping-values-rejected", service.validate(request.request, duplicate).fieldErrors().containsKey("receiverName"));
        String script = "<script>probe</script>";
        MultiValueMap<String, String> scripted = form(latest.token()); scripted.set("receiverName", script); scripted.set("receiverPhone", script); scripted.set("receiverAddress", script);
        CheckoutService.Validation scriptResult = service.validate(request.request, scripted);
        check("script-remains-plain-request-text-for-escaped-template", scriptResult.isValid() && scriptResult.form().receiverAddress().equals(script));
        check("request-only-shipping-never-added-to-session", request.session.values.size() == 2);

        latest = prepare(service, carts, clock, request);
        clock.current = latest.getExpiresAt().minusNanos(1);
        check("ttl-last-instant-before-boundary-valid", service.validate(request.request, form(latest.token())).isValid());
        clock.current = latest.getExpiresAt();
        final CheckoutConfirmation expiredAtBoundary = latest;
        int readsAtBoundary = carts.reads;
        conflict("ttl-exact-boundary-expired", "CHECKOUT_CONFIRMATION_EXPIRED", () -> service.validate(request.request, form(expiredAtBoundary.token())));
        check("expiry-before-cart-or-field-validation", carts.reads == readsAtBoundary);
        assertCleared("expiry-clears-session-confirmation", request);

        CheckoutConfirmation firstConfirmation = prepare(service, carts, clock, request);
        CheckoutConfirmation replacement = service.prepare(request.request);
        check("reopen-replaces-current-confirmation", request.session.values.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) == replacement && !replacement.token().equals(firstConfirmation.token()));
        conflict("old-replaced-token-rejected", "CHECKOUT_CONFIRMATION_INVALID", () -> service.validate(request.request, form(firstConfirmation.token())));
        assertCleared("stale-token-conservatively-clears-current-confirmation", request);
        int beforeInvalidToken = carts.reads;
        conflict("missing-confirmation-before-fields", "CHECKOUT_CONFIRMATION_INVALID", () -> service.validate(request.request, new LinkedMultiValueMap<>()));
        check("missing-confirmation-no-cart-read", carts.reads == beforeInvalidToken);

        latest = prepare(service, carts, clock, request);
        final String currentToken = latest.token();
        int malformedBefore = carts.reads;
        MultiValueMap<String, String> duplicateToken = form(currentToken); duplicateToken.add("confirmationToken", currentToken);
        conflict("duplicate-token-rejected", "CHECKOUT_CONFIRMATION_INVALID", () -> service.validate(request.request, duplicateToken));
        check("malformed-token-no-cart-read", carts.reads == malformedBefore);
        RequestState sameAccountOtherSession = new RequestState(1);
        prepare(service, carts, clock, sameAccountOtherSession);
        conflict("same-user-different-session-token-rejected", "CHECKOUT_CONFIRMATION_INVALID", () -> service.validate(sameAccountOtherSession.request, form(currentToken)));
        assertCleared("cross-session-conflict-clears-recipient-confirmation", sameAccountOtherSession);
        latest = prepare(service, carts, clock, request);
        final String aliceToken = latest.token(); request.identity(2);
        int userSwapBefore = carts.reads;
        conflict("confirmation-user-binding", "CHECKOUT_CONFIRMATION_INVALID", () -> service.validate(request.request, form(aliceToken)));
        check("foreign-user-confirmation-no-cart-read", carts.reads == userSwapBefore);
        request.identity(1);

        Map<String, CartPage> changes = new LinkedHashMap<>();
        changes.put("quantity", page(line(101, 1001, 3, 8, "18.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "49.00", 12, "ON_SALE")));
        changes.put("item-version-only", page(line(101, 1001, 2, 8, "18.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "49.00", 12, "ON_SALE")));
        changes.put("new-item", page(line(101, 1001, 2, 7, "18.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "49.00", 12, "ON_SALE"), line(103, 1003, 1, 0, "1.00", 10, "ON_SALE")));
        changes.put("removed-item", page(line(101, 1001, 2, 7, "18.00", 100, "ON_SALE")));
        changes.put("item-id", page(line(111, 1001, 2, 7, "18.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "49.00", 12, "ON_SALE")));
        changes.put("product-id", page(line(101, 1999, 2, 7, "18.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "49.00", 12, "ON_SALE")));
        changes.put("price-despite-same-total", page(line(101, 1001, 2, 7, "19.00", 100, "ON_SALE"), line(102, 1002, 1, 0, "47.00", 12, "ON_SALE")));
        for (Map.Entry<String, CartPage> change : changes.entrySet()) {
            CheckoutConfirmation before = prepare(service, carts, clock, request);
            carts.page = change.getValue();
            conflict("changed-" + change.getKey(), "CHECKOUT_CART_CHANGED", () -> service.validate(request.request, form(before.token())));
            assertCleared("changed-" + change.getKey() + "-cleared", request);
        }

        Map<String, CartPage> invalid = new LinkedHashMap<>();
        invalid.put("draft", page(line(101, 1001, 2, 7, "18.00", 100, "DRAFT")));
        invalid.put("sold-out", page(line(101, 1001, 2, 7, "18.00", 0, "ON_SALE")));
        invalid.put("over-stock", page(line(101, 1001, 2, 7, "18.00", 1, "ON_SALE")));
        for (Map.Entry<String, CartPage> invalidCart : invalid.entrySet()) {
            CheckoutConfirmation before = prepare(service, carts, clock, request);
            carts.page = invalidCart.getValue();
            conflict("current-cart-" + invalidCart.getKey(), "CHECKOUT_CART_INVALID", () -> service.validate(request.request, form(before.token())));
            assertCleared("invalid-" + invalidCart.getKey() + "-cleared", request);
        }
        prepare(service, carts, clock, request); carts.page = page();
        conflict("empty-new-confirmation", "CHECKOUT_CART_EMPTY", () -> service.prepare(request.request));
        assertCleared("empty-new-confirmation-invalidates-previous", request);
        prepare(service, carts, clock, request); carts.page = invalid.get("draft");
        conflict("invalid-new-confirmation", "CHECKOUT_CART_INVALID", () -> service.prepare(request.request));
        assertCleared("invalid-new-confirmation-invalidates-previous", request);

        Map<String, CartPage> oversized = new LinkedHashMap<>();
        oversized.put("line-subtotal", page(line(101, 1001, 2, 0, "9999999999.99", 99, "ON_SALE")));
        oversized.put("cart-total", page(line(101, 1001, 1, 0, "9999999990.00", 99, "ON_SALE"), line(102, 1002, 1, 0, "20.00", 99, "ON_SALE")));
        oversized.put("subcent", page(line(101, 1001, 1, 0, "1.001", 99, "ON_SALE")));
        for (Map.Entry<String, CartPage> amount : oversized.entrySet()) {
            prepare(service, carts, clock, request); carts.page = amount.getValue();
            conflict("amount-overflow-" + amount.getKey(), "CHECKOUT_AMOUNT_OUT_OF_RANGE", () -> service.prepare(request.request));
            assertCleared("amount-invalid-" + amount.getKey() + "-cleared", request);
        }
        carts.page = page(line(101, 1001, 1, 0, "9999999999.99", 99, "ON_SALE"));
        check("decimal12-2-exact-maximum-allowed", service.prepare(request.request).getTotal().equals(new BigDecimal("9999999999.99")));
        carts.page = page(line(101, 1001, 1, 0, "0.01", 99, "ON_SALE"));
        check("minimum-positive-cent-allowed", service.prepare(request.request).getTotal().equals(new BigDecimal("0.01")));

        prepare(service, carts, clock, request);
        sessions.clear(request.request);
        assertCleared("identity-clear-removes-confirmation", request);
        check("identity-clear-removes-identity", !request.session.values.containsKey(SessionSupport.IDENTITY_ATTRIBUTE));
        request.identity(1); prepare(service, carts, clock, request);
        sessions.invalidate(request.request);
        check("logout-session-end-removes-all-state", !request.session.valid && request.session.values.isEmpty());
        try { service.prepare(request.request); check("ended-session-not-usable", false); }
        catch (SessionExpiredException expected) { check("ended-session-not-usable", true); }
        RequestState technical = new RequestState(1);
        carts.reset(); carts.failure = new IllegalStateException("Probe technical failure");
        try { service.prepare(technical.request); check("technical-failure-not-converted-to-auth", false); }
        catch (IllegalStateException expected) { check("technical-failure-not-converted-to-auth", true); }
        carts.reset();

        Select select = CartItemMapper.class.getMethod("selectLines", long.class).getAnnotation(Select.class);
        String sql = String.join(" ", select.value()).toUpperCase(Locale.ROOT);
        check("mapped-cart-read-ordinary-select-without-update-lock", sql.stripLeading().startsWith("SELECT") && sql.contains("LEFT JOIN PRODUCT") && !sql.contains("FOR UPDATE"));
        check("mapped-cart-read-own-user-and-stable-order", sql.contains("CI.USER_ID=#{USERID}") && sql.contains("ORDER BY CI.ID ASC"));
        Transactional read = CartService.class.getMethod("read", long.class).getAnnotation(Transactional.class);
        check("cart-read-service-readonly-transaction", read != null && read.readOnly());
        check("checkout-service-no-write-guard-field", List.of(CheckoutService.class.getDeclaredFields()).stream().noneMatch(f -> f.getType().getSimpleName().contains("WriteGuard") || f.getType().getSimpleName().contains("Mapper")));
    }

    @Intercepts({
            @Signature(type = Executor.class, method = "query", args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class}),
            @Signature(type = Executor.class, method = "update", args = {MappedStatement.class, Object.class})
    })
    public static final class ReadTrace implements Interceptor {
        @Override public Object intercept(Invocation call) throws Throwable {
            MappedStatement statement = (MappedStatement) call.getArgs()[0];
            String sql = statement.getBoundSql(call.getArgs()[1]).getSql().replaceAll("\\s+", " ").strip();
            sqlEvents.add(Map.of("statement", statement.getId(), "sql", sql,
                    "activeTransaction", TransactionSynchronizationManager.isActualTransactionActive(),
                    "readOnlyTransaction", TransactionSynchronizationManager.isCurrentTransactionReadOnly(),
                    "executorMethod", call.getMethod().getName()));
            return call.proceed();
        }
    }

    private static void live() throws Exception {
        SpringApplication application = new SpringApplication(Class.forName("org.csucampuscraft.storefront.CSUCampusCraftUserApplication"));
        application.setLogStartupInfo(false);
        try (ConfigurableApplicationContext context = application.run("--server.port=0", "--server.address=127.0.0.1",
                "--spring.profiles.active=default", "--spring.main.banner-mode=off", "--logging.level.root=OFF",
                "--mybatis-plus.global-config.banner=false")) {
            DataSource dataSource = context.getBean(DataSource.class);
            LocalDateTime stamp;
            try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement("SELECT updated_at FROM store_user WHERE id=1")) {
                try (ResultSet rows = statement.executeQuery()) {
                    check("live-user-fixture-exists", rows.next());
                    stamp = rows.getObject(1, LocalDateTime.class);
                }
            }
            RequestState request = new RequestState(1);
            request.session.values.put(SessionSupport.IDENTITY_ATTRIBUTE, new SessionIdentity(1L, stamp));
            context.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new ReadTrace());
            CheckoutService service = context.getBean(CheckoutService.class);
            sqlEvents.clear();
            CheckoutConfirmation confirmation = service.prepare(request.request);
            check("live-current-demo-full-cart-85", confirmation.getItemCount() == 2 && confirmation.getQuantity() == 3 && confirmation.getTotal().equals(new BigDecimal("85.00")));
            check("live-prepare-one-read-joined-statement", sqlEvents.size() == 1);
            CheckoutService.Validation result = service.validate(request.request, form(confirmation.token()));
            check("live-current-cart-validation-valid", result.isValid());
            check("live-prepare-plus-validate-two-read-statements", sqlEvents.size() == 2);
            check("live-only-owned-cart-selects-no-user-lock-or-dml", sqlEvents.stream().allMatch(e -> ((String) e.get("sql")).toUpperCase(Locale.ROOT).startsWith("SELECT") && ((String) e.get("sql")).contains("FROM cart_item ci LEFT JOIN product") && !((String) e.get("sql")).toUpperCase(Locale.ROOT).contains("FOR UPDATE") && e.get("executorMethod").equals("query")));
            check("live-cart-selects-in-readonly-transactions", sqlEvents.stream().allMatch(e -> Boolean.TRUE.equals(e.get("activeTransaction")) && Boolean.TRUE.equals(e.get("readOnlyTransaction"))));
            check("live-confirmation-retained-without-order-write", request.session.values.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) == confirmation);
        }
    }

    public static void main(String[] args) throws Exception {
        boolean completed = false;
        String failureClass = null;
        boolean live = List.of(args).contains("--live");
        try { controlled(); if (live) live(); completed = true; }
        catch (Throwable failure) { failureClass = failure.getClass().getName(); }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("overall", completed ? "PASS" : "FAIL");
        result.put("scope", live ? "Controlled native object checks and actual private-DB read-only SQL trace" : "Controlled native object checks; no HTTP or live DB claim");
        result.put("checks", checks.size());
        result.put("checksPassed", checks.stream().filter(e -> Boolean.TRUE.equals(e.get("passed"))).count());
        result.put("details", checks);
        result.put("sqlEvents", sqlEvents);
        result.put("failureClass", failureClass);
        result.put("secretsRecorded", false);
        System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result));
        if (!completed) System.exit(1);
    }
}
