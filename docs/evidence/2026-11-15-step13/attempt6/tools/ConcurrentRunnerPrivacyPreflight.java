import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import com.fasterxml.jackson.databind.ObjectMapper;

/** Offline actual-runner privacy regression only. No HTTP, JDBC, application or business action. */
public final class ConcurrentRunnerPrivacyPreflight {
    private static int count;
    private static void check(boolean passed) { if (!passed) throw new AssertionError("privacy-preflight"); count++; }
    public static void main(String[] args) throws Exception {
        Field field = ConcurrentHttpRunner.class.getDeclaredField("BCRYPT"); field.setAccessible(true);
        Pattern bcrypt = (Pattern) field.get(null);
        for (String prefix : List.of("a", "b", "y")) check(bcrypt.matcher("$2" + prefix + "$10$" + "A".repeat(53)).find());
        check(!bcrypt.matcher("$2x$10$" + "A".repeat(53)).find());
        check(!bcrypt.matcher("$2a$10$" + "A".repeat(52)).find());
        Method redact = ConcurrentHttpRunner.class.getDeclaredMethod("redact", String.class, List.class); redact.setAccessible(true);
        String secret = "synthetic-private-cookie-value";
        String csrf = "synthetic-csrf-form-value";
        String html = "<input name='_csrf' value='" + csrf + "'><input value='" + csrf + "' name='_csrf'>"
                + "<input name='confirmationToken' value='synthetic-confirmation-value'>"
                + "<dd data-shipping-value='receiverAddress'>synthetic-private-address</dd>"
                + "<dd data-customer-contact='phone'>synthetic-private-phone</dd>"
                + "<span>CHECKOUT_CONFIRMATION_INVALID</span><a href='/;CSUCAMPUSCRAFT_USER_SESSION=" + secret + "'>safe</a>";
        String safe = (String) redact.invoke(null, html, List.of(secret));
        check(!safe.contains(secret)); check(!safe.contains(csrf));
        check(!safe.contains("synthetic-confirmation-value"));
        check(!safe.contains("synthetic-private-address")); check(!safe.contains("synthetic-private-phone"));
        check(safe.contains("CHECKOUT_CONFIRMATION_INVALID"));
        String credential = "$2a$10$" + "A".repeat(53);
        check(!bcrypt.matcher((String) redact.invoke(null, credential, List.of())).find());
        System.out.println(new ObjectMapper().writeValueAsString(Map.of("overall", "PASS", "checks", count,
                "scope", "Offline actual runner redaction/BCrypt behavior only; no HTTP/JDBC/application action",
                "synthetic_private_values_recorded", false)));
    }
}
