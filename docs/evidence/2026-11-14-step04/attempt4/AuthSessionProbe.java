import jakarta.servlet.http.HttpSession;
import java.lang.reflect.Constructor;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.sql.DriverManager;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.catalina.Container;
import org.apache.catalina.Manager;
import org.apache.catalina.Session;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.web.embedded.tomcat.TomcatWebServer;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.annotation.Order;

/** Supplementary real-HTTP/session inspection over classes extracted from the exact tested JAR. */
public final class AuthSessionProbe {
    private static final String IDENTITY="CSUCAMPUSCRAFT_AUTH_IDENTITY";
    private static final String CONFIRMATION="CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION";
    private static final Map<String,Boolean> CHECKS=new LinkedHashMap<>();
    private static String base,cookieName,username,password,invalidPassword;
    private static HttpClient http;
    private static CookieManager cookies;
    private static Manager manager;
    private static void check(String label,boolean okay) {
        CHECKS.put(label,okay);
        if(!okay)throw new IllegalStateException("Probe assertion failed: "+label);
    }
    private static String value(String input,String name) {
        Matcher m=Pattern.compile("\\b"+name+"=\"([^\"]*)\"").matcher(input);
        return m.find()?m.group(1):null;
    }
    private static String csrf(String html) {
        Matcher inputs=Pattern.compile("<input\\b[^>]*>",Pattern.CASE_INSENSITIVE).matcher(html);
        while(inputs.find())if("_csrf".equals(value(inputs.group(),"name")))return value(inputs.group(),"value");
        throw new IllegalStateException("CSRF input unavailable");
    }
    private static HttpResponse<String> get(String path)throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create(base+path)).GET().build(),HttpResponse.BodyHandlers.ofString());
    }
    private static HttpResponse<String> post(String path,Map<String,String> fields)throws Exception {
        String form=fields.entrySet().stream().map(e->URLEncoder.encode(e.getKey(),StandardCharsets.UTF_8)+"="+URLEncoder.encode(e.getValue(),StandardCharsets.UTF_8)).reduce((a,b)->a+"&"+b).orElse("");
        return http.send(HttpRequest.newBuilder(URI.create(base+path)).header("Content-Type","application/x-www-form-urlencoded").POST(HttpRequest.BodyPublishers.ofString(form)).build(),HttpResponse.BodyHandlers.ofString());
    }
    private static String sessionId() {
        return cookies.getCookieStore().getCookies().stream().filter(c->c.getName().equals(cookieName)).map(c->c.getValue()).findFirst().orElse(null);
    }
    private static HttpSession session()throws Exception {
        Session nativeSession=manager.findSession(sessionId());
        return nativeSession==null?null:nativeSession.getSession();
    }
    private static Object attribute(HttpSession session,String name) {
        try{return session==null?null:session.getAttribute(name);}catch(IllegalStateException expired){return null;}
    }
    private static String authenticate()throws Exception {
        HttpResponse<String> page=get("/login");
        check("login-form",page.statusCode()==200);
        String old=sessionId(),token=csrf(page.body());
        HttpResponse<String> login=post("/login",Map.of("username",username,"password",password,"_csrf",token,"returnUrl","/"));
        check("login-status",login.statusCode()==303);
        check("session-rotation",old!=null&&sessionId()!=null&&!old.equals(sessionId()));
        check("csrf-retained",token.equals(csrf(get("/login").body())));
        check("password-not-reflected",!login.body().contains(password));
        return token;
    }
    private static Object identity()throws Exception{return attribute(session(),IDENTITY);}
    private static LocalDateTime stamp(Object identity)throws Exception{return (LocalDateTime)identity.getClass().getMethod("authStamp").invoke(identity);}
    private static Object userId(Object identity)throws Exception{return identity.getClass().getMethod("userId").invoke(identity);}
    private static Object replacement(Object identity,Object id,LocalDateTime stamp)throws Exception {
        Constructor<?> constructor=identity.getClass().getDeclaredConstructors()[0];
        return constructor.newInstance(id,stamp);
    }
    public static void main(String[] args)throws Exception {
        String pkg=System.getenv("STEP04_PROBE_PACKAGE"),port=System.getenv("STEP04_PROBE_PORT");
        boolean admin=pkg.endsWith(".admin");
        base="http://127.0.0.1:"+port;
        cookieName=admin?"CSUCAMPUSCRAFT_ADMIN_SESSION":"CSUCAMPUSCRAFT_USER_SESSION";
        username=admin?"admin":"alice";password=System.getenv("STEP04_VALID_PASSWORD");invalidPassword=System.getenv("STEP04_INVALID_PASSWORD");
        String main=pkg+"."+(admin?"CSUCampusCraftAdminApplication":"CSUCampusCraftUserApplication");
        ConfigurableApplicationContext context=null;
        try {
            context=SpringApplication.run(Class.forName(main),"--server.port="+port,"--spring.profiles.active=default");
            TomcatWebServer server=(TomcatWebServer)((ServletWebServerApplicationContext)context).getWebServer();
            for(Container child:server.getTomcat().getHost().findChildren())if(child instanceof org.apache.catalina.Context c&&c.getManager()!=null){manager=c.getManager();break;}
            check("native-manager-present",manager!=null);
            check("auth-filter-order",Class.forName(pkg+".auth.AuthFilter").getAnnotation(Order.class).value()==Integer.MIN_VALUE+10);
            check("csrf-filter-order",Class.forName(pkg+".foundation.security.CsrfFilter").getAnnotation(Order.class).value()==Integer.MIN_VALUE+20);
            cookies=new CookieManager(null,CookiePolicy.ACCEPT_ALL);
            http=HttpClient.newBuilder().cookieHandler(cookies).followRedirects(HttpClient.Redirect.NEVER).build();
            authenticate();
            Object first=identity();
            check("identity-server-side",first!=null&&first.getClass().getName().equals(pkg+".auth.SessionIdentity"));
            LocalDateTime fromDatabase;
            try(var connection=DriverManager.getConnection(System.getenv("CSUCAMPUSCRAFT_DB_URL")+"?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true",System.getenv("CSUCAMPUSCRAFT_DB_USER"),System.getenv("CSUCAMPUSCRAFT_DB_PASSWORD"))) {
                connection.createStatement().execute("SET SESSION time_zone='+00:00'");
                try(var query=connection.prepareStatement("SELECT updated_at FROM store_user WHERE username=?")) {
                    query.setString(1,username);try(var rows=query.executeQuery()){if(!rows.next())throw new IllegalStateException("Probe account unavailable");fromDatabase=rows.getObject(1,LocalDateTime.class);}
                }
            }
            check("utc-auth-stamp-equals-db-microseconds",stamp(first).equals(fromDatabase));
            check("nonzero-six-digit-microseconds-preserved",fromDatabase.getNano()==123456000&&stamp(first).getNano()==123456000);
            HttpSession active=session();active.setAttribute(CONFIRMATION,"verification-only confirmation");
            active.setAttribute(IDENTITY,replacement(first,userId(first),stamp(first).minusNanos(1000)));
            check("stale-stamp-next-protected-request-302",get(admin?"/":"/cart").statusCode()==302);
            check("stale-stamp-identity-cleared",attribute(active,IDENTITY)==null);
            check("stale-stamp-confirmation-cleared",attribute(active,CONFIRMATION)==null);
            authenticate();active=session();Object valid=identity();
            active.setAttribute(CONFIRMATION,"verification-only confirmation");
            active.setAttribute(IDENTITY,replacement(valid,Long.MAX_VALUE,stamp(valid)));
            check("unknown-account-next-protected-request-302",get(admin?"/":"/cart").statusCode()==302);
            check("unknown-account-identity-cleared",attribute(active,IDENTITY)==null);
            check("unknown-account-confirmation-cleared",attribute(active,CONFIRMATION)==null);
            String token=authenticate();active=session();active.setAttribute(CONFIRMATION,"verification-only confirmation");
            HttpResponse<String> wrongCsrf=post("/login",Map.of("username","QA_NO_ACCOUNT","password",invalidPassword,"_csrf","0".repeat(64)));
            check("bad-csrf-relogin-403",wrongCsrf.statusCode()==403);
            check("bad-csrf-relogin-preserves-identity",attribute(active,IDENTITY)!=null);
            check("bad-csrf-relogin-preserves-confirmation",attribute(active,CONFIRMATION)!=null);
            HttpResponse<String> failed=post("/login",Map.of("username","QA_NO_ACCOUNT","password",invalidPassword,"_csrf",token));
            check("valid-csrf-failed-relogin-readable",failed.statusCode()==200);
            check("failed-relogin-password-empty",!failed.body().contains(invalidPassword)&&!failed.body().contains(password));
            check("failed-relogin-identity-cleared",attribute(active,IDENTITY)==null);
            check("failed-relogin-confirmation-cleared",attribute(active,CONFIRMATION)==null);
            authenticate();active=session();active.setAttribute(CONFIRMATION,"verification-only confirmation");
            String logoutToken=csrf(get("/login").body());
            HttpResponse<String> logout=post("/logout",Map.of("_csrf",logoutToken));
            check("logout-303",logout.statusCode()==303);
            check("logout-identity-unavailable",attribute(active,IDENTITY)==null);
            check("logout-confirmation-unavailable",attribute(active,CONFIRMATION)==null);
            System.out.println("{\"overall\":\"PASS\",\"checks\":"+CHECKS.size()+",\"microsecondValueLogged\":false,\"sessionValuesLogged\":false}");
            CHECKS.forEach((name,okay)->System.out.println(name+": "+okay));
        } finally {if(context!=null)context.close();}
    }
}

