import java.sql.Connection;
import java.sql.PreparedStatement;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import javax.sql.DataSource;
import org.csucampuscraft.storefront.CSUCampusCraftUserApplication;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.cart.CartItemMapper;
import org.csucampuscraft.storefront.cart.CartLine;
import org.csucampuscraft.storefront.cart.CartPage;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.cart.CustomerWriteGuard;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.aop.support.AopUtils;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.IllegalTransactionStateException;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

/** Temporary real Spring/MySQL probe. Creates/deletes only one dedicated CUSTOMER fixture. */
public class ServiceProbe {
    static int passed;
    static void check(String name, boolean valid) {
        if (!valid) throw new AssertionError(name);
        passed++;
        System.out.println("PASS " + name);
    }
    static SessionIdentity identity(JdbcTemplate jdbc, long userId) {
        return jdbc.queryForObject("SELECT id,updated_at FROM store_user WHERE id=?", (rs,n) ->
                new SessionIdentity(rs.getLong("id"),rs.getObject("updated_at",LocalDateTime.class)),userId);
    }
    static long count(JdbcTemplate jdbc, long userId) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM cart_item WHERE user_id=?",Long.class,userId);
    }
    static List<Map<String,Object>> cartRows(JdbcTemplate jdbc, long userId) {
        return jdbc.queryForList("SELECT * FROM cart_item WHERE user_id=? ORDER BY id",userId);
    }
    static Map<String,String> snapshot(JdbcTemplate jdbc) throws Exception {
        Map<String,String> hashes=new LinkedHashMap<>();
        for(String table:List.of("store_user","category","product","product_image","cart_item","sales_order","sales_order_item")) {
            String rows=jdbc.queryForList("SELECT * FROM "+table+" ORDER BY id").toString();
            hashes.put(table,HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(rows.getBytes(StandardCharsets.UTF_8))));
        }
        return hashes;
    }
    static void expectBusiness(String name, HttpStatus status, Runnable action) {
        try { action.run(); throw new AssertionError(name+" unexpectedly succeeded"); }
        catch (BusinessException expected) { check(name,expected.getStatus()==status); }
    }
    static void expectExpired(String name, Runnable action) {
        try { action.run(); throw new AssertionError(name+" unexpectedly succeeded"); }
        catch (SessionExpiredException expected) { check(name,true); }
    }

    public static void main(String[] args) throws Exception {
        String url=System.getenv("CSUCAMPUSCRAFT_DB_URL");
        String port=System.getenv("STEP07_PROBE_PORT");
        String schema=System.getenv("STEP07_PROBE_SCHEMA");
        if (port==null || schema==null || url==null
                || !url.startsWith("jdbc:mysql://127.0.0.1:"+port+"/"+schema)) {
            throw new IllegalStateException("Only the explicitly supplied temporary MySQL instance is permitted");
        }
        boolean readOnly=args.length>0 && "readonly".equals(args[0]);
        try (ConfigurableApplicationContext context=new SpringApplicationBuilder(CSUCampusCraftUserApplication.class)
                .web(WebApplicationType.NONE)
                .properties("spring.main.banner-mode=off","logging.level.root=WARN").run()) {
            CartService carts=context.getBean(CartService.class);
            CustomerWriteGuard guard=context.getBean(CustomerWriteGuard.class);
            check("CartService is a real Spring transaction proxy",AopUtils.isAopProxy(carts));
            check("CustomerWriteGuard is a real Spring transaction proxy",AopUtils.isAopProxy(guard));
            SessionIdentity placeholder=new SessionIdentity(1L,LocalDateTime.of(2026,11,14,0,0));
            try { guard.lock(placeholder); throw new AssertionError("Mandatory transaction was bypassed"); }
            catch (IllegalTransactionStateException expected) { check("proxied guard refuses no transaction",true); }
            try {
                new CustomerWriteGuard(context.getBean(CartItemMapper.class)).lock(placeholder);
                throw new AssertionError("Unproxied guard permitted missing transaction");
            } catch (IllegalStateException expected) { check("direct guard refuses no transaction",true); }
            if (readOnly) {
                System.out.println("SERVICE_READONLY_PROBE_PASSED="+passed);
                return;
            }

            DriverManagerDataSource rootSource=new DriverManagerDataSource(url,"root","");
            Properties utc=new Properties();
            utc.setProperty("connectionTimeZone","+00:00");
            utc.setProperty("forceConnectionTimeZoneToSession","true");
            rootSource.setConnectionProperties(utc);
            JdbcTemplate root=new JdbcTemplate(rootSource);
            System.out.println("DATABASE_VERSION="+root.queryForObject("SELECT VERSION()",String.class));
            Map<String,String> originalTables=snapshot(root);
            System.out.println("ORIGINAL_TABLE_HASHES="+originalTables);
            String username="step07_probe_"+UUID.randomUUID().toString().replace("-", "").substring(0,16);
            long userId=0;
            ExecutorService workers=Executors.newSingleThreadExecutor();
            try {
                check("dedicated CUSTOMER fixture inserted",root.update("""
                        INSERT INTO store_user(username,password_hash,display_name,role,status)
                        SELECT ?,password_hash,'STEP07 transaction probe','CUSTOMER','ENABLED'
                          FROM store_user WHERE role='CUSTOMER' ORDER BY id LIMIT 1
                        """,username)==1);
                userId=root.queryForObject("SELECT id FROM store_user WHERE username=?",Long.class,username);
                final long uid=userId;
                final SessionIdentity initial=identity(root,uid);
                final long productId=root.queryForObject("SELECT id FROM product WHERE status='ON_SALE' AND stock>=3 ORDER BY id DESC LIMIT 1",Long.class);
                Map<String,Object> productBefore=root.queryForMap("SELECT * FROM product WHERE id=?",productId);
                PlatformTransactionManager manager=context.getBean(PlatformTransactionManager.class);
                TransactionTemplate wrongIsolation=new TransactionTemplate(manager);
                wrongIsolation.setIsolationLevel(TransactionDefinition.ISOLATION_REPEATABLE_READ);
                try {
                    wrongIsolation.execute(status -> guard.lock(initial));
                    throw new AssertionError("Guard permitted wrong transaction isolation");
                } catch (IllegalStateException expected) { check("guard refuses REPEATABLE READ",true); }
                TransactionTemplate readOnlyTransaction=new TransactionTemplate(manager);
                readOnlyTransaction.setIsolationLevel(TransactionDefinition.ISOLATION_READ_COMMITTED);
                readOnlyTransaction.setReadOnly(true);
                try {
                    readOnlyTransaction.execute(status -> guard.lock(initial));
                    throw new AssertionError("Guard permitted read-only write transaction");
                } catch (IllegalStateException expected) { check("guard refuses read-only transaction",true); }

                carts.add(initial,productId,1);
                CartPage page=carts.getCart(uid);
                check("real proxied Service add commits one owned row",page.items().size()==1 && page.items().get(0).quantity()==1);
                CartLine item=page.items().get(0);
                List<Map<String,Object>> original=cartRows(root,uid);
                carts.changeQuantity(initial,item.id(),1,item.version());
                check("same quantity preserves row version and timestamps",original.equals(cartRows(root,uid)));
                check("whole cart badge sums quantity",carts.quantity(uid)==1);
                expectBusiness("negative direct Service quantity rejected",HttpStatus.BAD_REQUEST,
                        () -> carts.changeQuantity(initial,item.id(),-1,item.version()));
                check("invalid direct quantity has no mutation",original.equals(cartRows(root,uid)));
                carts.remove(initial,item.id(),item.version());
                check("real Service remove commits",count(root,uid)==0);

                // Hold the actor row using an independent connection. Disable before releasing the waiter.
                try (Connection locker=rootSource.getConnection()) {
                    locker.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);
                    locker.setAutoCommit(false);
                    try (PreparedStatement lock=locker.prepareStatement("SELECT id FROM store_user WHERE id=? FOR UPDATE")) {
                        lock.setLong(1,uid);
                        try(var locked=lock.executeQuery()) { check("independent connection locks actor",locked.next()); }
                    }
                    CountDownLatch started=new CountDownLatch(1);
                    Future<?> pending=workers.submit(() -> { started.countDown(); carts.add(initial,productId,1); });
                    check("write worker starts",started.await(5,TimeUnit.SECONDS));
                    Thread.sleep(400);
                    check("Service waits for actor row lock",!pending.isDone());
                    try (PreparedStatement disable=locker.prepareStatement("""
                            UPDATE store_user SET status='DISABLED',
                                updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)
                             WHERE id=?
                            """)) {
                        disable.setLong(1,uid); check("disable commits before waiting write resumes",disable.executeUpdate()==1);
                    }
                    locker.commit();
                    try { pending.get(15,TimeUnit.SECONDS); throw new AssertionError("Waiting write ignored disabled identity"); }
                    catch (ExecutionException failure) {
                        check("waiting write rechecks identity inside lock",failure.getCause() instanceof SessionExpiredException);
                    }
                }
                check("lock-time authentication refusal preserves empty cart",count(root,uid)==0);
                root.update("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=?",uid);
                expectExpired("re-enabled account cannot reuse old auth stamp",() -> carts.add(initial,productId,1));
                check("old stamp refusal has no mutation",count(root,uid)==0);

                SessionIdentity renewed=identity(root,uid);
                carts.add(renewed,productId,1);
                CartLine current=carts.getCart(uid).items().get(0);
                root.update("UPDATE cart_item SET version=? WHERE id=?",Long.MAX_VALUE,current.id());
                List<Map<String,Object>> maximum=cartRows(root,uid);
                carts.changeQuantity(renewed,current.id(),1,Long.MAX_VALUE);
                check("max version permits a valid same-value no-op",maximum.equals(cartRows(root,uid)));
                expectBusiness("max version real change rejected",HttpStatus.CONFLICT,
                        () -> carts.changeQuantity(renewed,current.id(),2,Long.MAX_VALUE));
                expectBusiness("max version merged add rejected",HttpStatus.CONFLICT,() -> carts.add(renewed,productId,1));
                check("max version conflicts preserve all cart fields",maximum.equals(cartRows(root,uid)));
                carts.remove(renewed,current.id(),Long.MAX_VALUE);
                check("max version item remains removable",count(root,uid)==0);
                check("Service cart writes never alter product",productBefore.equals(root.queryForMap("SELECT * FROM product WHERE id=?",productId)));
                root.update("UPDATE store_user SET role='ADMIN',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=?",uid);
                SessionIdentity wrongRole=identity(root,uid);
                expectBusiness("direct Service rejects enabled wrong role",HttpStatus.FORBIDDEN,() -> carts.add(wrongRole,productId,1));
                check("wrong role refusal keeps cart empty",count(root,uid)==0);
            } finally {
                workers.shutdownNow();
                if (userId>0) {
                    root.update("DELETE FROM cart_item WHERE user_id=?",userId);
                    root.update("DELETE FROM store_user WHERE id=? AND username=?",userId,username);
                    check("dedicated fixture cleaned",root.queryForObject("SELECT COUNT(*) FROM store_user WHERE id=?",Long.class,userId)==0);
                }
            }
            Map<String,String> finalTables=snapshot(root);
            System.out.println("FINAL_TABLE_HASHES="+finalTables);
            check("all seven tables restored after dedicated fixture cleanup",originalTables.equals(finalTables));
            System.out.println("SERVICE_PROBE_PASSED="+passed);
        }
    }
}
