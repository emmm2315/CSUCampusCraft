import com.fasterxml.jackson.databind.ObjectMapper;
import java.lang.reflect.Method;
import java.util.LinkedHashMap;
import java.util.Map;

/** Offline wire-encoding regression only. No HTTP, JDBC or business action. */
public final class ConcurrentRunnerWirePreflight {
    public static void main(String[] args) throws Exception {
        Map<String,Object> value = new LinkedHashMap<>();
        value.put("text", "\u6821\u56ed\u6bd5\u4e1a\u793c\u76d2\ud83d\ude00");
        value.put("stdout_charset", System.out.charset().name());
        value.put("scope", "Offline synthetic JSON encoding only");
        if (args.length == 1 && "old-print-control".equals(args[0])) {
            // Reproduce the old mechanism, without changing the archived old runner bytes.
            System.out.println(new ObjectMapper().writeValueAsString(value));
        } else {
            Method write = ConcurrentHttpRunner.class.getDeclaredMethod("writeJson", Object.class);
            write.setAccessible(true);
            write.invoke(null, value);
        }
    }
}
