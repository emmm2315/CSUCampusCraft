import java.lang.reflect.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.util.*;

public final class FoundationChecks {
    enum Choice { FIRST, SECOND }
    private static int count;
    private static Class<?> checks;
    private static void ok(String id, boolean value) {
        if (!value) throw new AssertionError(id);
        count++;
        System.out.println(id + " PASS");
    }
    private static Object call(String name, Class<?>[] types, Object... values) throws Exception {
        return checks.getMethod(name, types).invoke(null, values);
    }
    private static void invalid(String id, String name, Class<?>[] types, Object... values) throws Exception {
        boolean rejected=false;
        try { call(name, types, values); }
        catch (InvocationTargetException exception) {
            Throwable target=exception.getTargetException();
            if (target.getClass().getSimpleName().equals("BusinessException")) {
                Object status=target.getClass().getMethod("getStatus").invoke(target);
                rejected=(int)status.getClass().getMethod("value").invoke(status)==400;
            }
        }
        ok(id, rejected);
    }
    public static void main(String[] args) throws Exception {
        String prefix=args[0];
        Object passwords=Class.forName(prefix+".security.PasswordService").getConstructor().newInstance();
        Method matches=passwords.getClass().getMethod("matches",String.class,String.class);
        Method hash=passwords.getClass().getMethod("hash",String.class);
        var hashes=Files.readAllLines(Path.of(args[1]));
        String raw=System.getenv("STEP02_SEED_RAW");
        ok("PASSWORD_SEEDS_DISTINCT",hashes.size()==4 && new HashSet<>(hashes).size()==4);
        for(int i=0;i<hashes.size();i++) {
            ok("PASSWORD_SEED_POSITIVE_"+i,(boolean)matches.invoke(passwords,raw,hashes.get(i)));
            ok("PASSWORD_SEED_NEGATIVE_"+i,!(boolean)matches.invoke(passwords,UUID.randomUUID().toString(),hashes.get(i)));
        }
        String fresh=UUID.randomUUID().toString();
        String encoded=(String)hash.invoke(passwords,fresh);
        ok("PASSWORD_NEW_COST10",encoded.startsWith("$2a$10$") && (boolean)matches.invoke(passwords,fresh,encoded));
        ok("PASSWORD_NULL_SAFE",!(boolean)matches.invoke(passwords,null,encoded) && !(boolean)matches.invoke(passwords,fresh,null));
        ok("PASSWORD_MALFORMED_SAFE",!(boolean)matches.invoke(passwords,fresh,"invalid"));
        String bound="a".repeat(72);
        String boundHash=(String)hash.invoke(passwords,bound);
        ok("PASSWORD_72_UTF8_BYTES",(boolean)matches.invoke(passwords,bound,boundHash));
        ok("PASSWORD_73_BYTES_REJECT_MATCH",!(boolean)matches.invoke(passwords,bound+"a",boundHash));
        boolean rejected=false;
        try { hash.invoke(passwords,bound+"a"); } catch(InvocationTargetException ex) { rejected=ex.getTargetException() instanceof IllegalArgumentException; }
        ok("PASSWORD_73_BYTES_REJECT_HASH",rejected);

        Object policy=Class.forName(prefix+".security.ReturnUrlPolicy").getConstructor().newInstance();
        Method resolve=policy.getClass().getMethod("resolve",String.class,String.class);
        boolean admin=prefix.contains(".admin.");
        String[] allow=admin?new String[]{"/","/categories","/categories/new","/categories/1/edit","/products","/products/new","/products/1/edit","/products/1/images","/orders","/orders/ORDER_1","/customers","/customers/1","/products?q=%E4%B8%AD&page=1"}
            :new String[]{"/","/products","/products/1","/cart","/checkout","/orders","/orders/ORDER_1","/orders/ORDER_1/payment","/products?q=%E4%B8%AD&page=1"};
        for(int i=0;i<allow.length;i++)ok("RETURN_ALLOW_"+i,allow[i].equals(resolve.invoke(policy,allow[i],"/")));
        String[] deny={null,"","https://example.invalid/","//example.invalid/","/\\example.invalid","C:/system/file","../relative","/products/../orders","/%2e%2e/orders","/%252e%252e/orders","/%2F%2Fexample.invalid","/%5cexample.invalid","/products?x=%0d%0aLocation:test","/products?x=%250a","/products?x=%25250a","/products#fragment","/login","/logout","/orders/ORDER_1/cancel","/orders/ORDER_1/ship","/products/1/publish","/products/1/restock","/customers/1/status","/unknown-path"," /products","/products\t","/products?x=%ZZ"};
        for(int i=0;i<deny.length;i++)ok("RETURN_DENY_"+i,"/orders".equals(resolve.invoke(policy,deny[i],"/orders")));
        ok("RETURN_BAD_FALLBACK","/".equals(resolve.invoke(policy,"https://example.invalid/","//example.invalid/")));
        ok("RETURN_NULL_FALLBACK","/".equals(resolve.invoke(policy,null,null)));

        checks=Class.forName(prefix+".validation.InputChecks");
        Class<?>[] ints={String.class,String.class,int.class,int.class};
        Class<?>[] longs={String.class,String.class,long.class,long.class};
        Class<?>[] text={String.class,String.class,int.class,int.class};
        Class<?>[] required={String.class,String.class,int.class};
        Class<?>[] money={String.class,String.class};
        Class<?>[] en={String.class,String.class,Class.class};
        ok("INTEGER_BOUND_ZERO",(int)call("integer",ints,"field","0",0,99)==0);
        ok("INTEGER_BOUND_MAX",(int)call("integer",ints,"field","99",0,99)==99);
        invalid("INTEGER_FRACTION","integer",ints,"field","1.5",0,99);
        invalid("INTEGER_OVER_RANGE","integer",ints,"field","100",0,99);
        invalid("INTEGER_OVERFLOW","integer",ints,"field","9223372036854775808",0,99);
        invalid("INTEGER_MISSING","integer",ints,"field",null,0,99);
        invalid("INTEGER_SCIENTIFIC","integer",ints,"field","1e1",0,99);
        ok("LONG_BOUND",(long)call("longInteger",longs,"field",Long.toString(Long.MAX_VALUE),0L,Long.MAX_VALUE)==Long.MAX_VALUE);
        invalid("LONG_OVERFLOW","longInteger",longs,"field","9223372036854775808",0L,Long.MAX_VALUE);
        ok("TEXT_TRIM","test".equals(call("requiredText",required,"field"," test ",4)));
        ok("TEXT_UNICODE_CODEPOINTS","\uD83D\uDE00".equals(call("text",text,"field","\uD83D\uDE00",1,1)));
        invalid("TEXT_EMPTY","requiredText",required,"field"," ",4);
        invalid("TEXT_OVER_LENGTH","requiredText",required,"field","12345",4);
        ok("MONEY_MAX",new BigDecimal("9999999999.99").equals(call("money",money,"field","9999999999.99")));
        ok("MONEY_MIN",new BigDecimal("-9999999999.99").equals(call("money",money,"field","-9999999999.99")));
        ok("MONEY_SCALE_TWO",new BigDecimal("1.00").equals(call("money",money,"field","1")));
        invalid("MONEY_RANGE","money",money,"field","10000000000.00");
        invalid("MONEY_THREE_DECIMALS","money",money,"field","1.001");
        invalid("MONEY_TRAILING_THIRD","money",money,"field","1.000");
        invalid("MONEY_SCIENTIFIC","money",money,"field","1e1");
        ok("ENUM_ALLOWED",call("enumeration",en,"field","FIRST",Choice.class)==Choice.FIRST);
        invalid("ENUM_REJECT","enumeration",en,"field","first",Choice.class);
        System.out.println("FOUNDATION_CHECKS_PASS checks="+count);
    }
}

