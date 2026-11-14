import java.lang.reflect.*;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.*;
import javax.sql.DataSource;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.*;
import org.apache.ibatis.session.*;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Actual merged JAR observations plus bounded actor-lock/disable interleaving, no product/ordering fault hook. */
public final class CartWriteProbe {
  static final List<Boolean> checks=new ArrayList<>();
  static final List<String> labels=new ArrayList<>();
  static final List<Event> events=new ArrayList<>();
  record Event(String sql,int connection,boolean active,Integer declaredIsolation,int jdbcIsolation) {}
  @Intercepts({@Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),@Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})})
  public static final class Trace implements Interceptor {
    public Object intercept(Invocation call)throws Throwable {
      MappedStatement ms=(MappedStatement)call.getArgs()[0];
      String sql=ms.getBoundSql(call.getArgs()[1]).getSql().replaceAll("\\s+"," ").trim();
      Connection c=((Executor)call.getTarget()).getTransaction().getConnection();
      events.add(new Event(sql,System.identityHashCode(c),TransactionSynchronizationManager.isActualTransactionActive(),TransactionSynchronizationManager.getCurrentTransactionIsolationLevel(),c.getTransactionIsolation()));
      return call.proceed();
    }
  }
  static void check(String label,boolean good){labels.add(label);checks.add(good);if(!good)throw new IllegalStateException("Probe assertion: "+label);}
  static Object identity(Class<?> t,long id,LocalDateTime s)throws Exception{return t.getConstructor(Long.class,LocalDateTime.class).newInstance(Long.valueOf(id),s);}
  static LocalDateTime stamp(DataSource ds,long id)throws Exception{try(Connection c=ds.getConnection();PreparedStatement p=c.prepareStatement("SELECT updated_at FROM store_user WHERE id=?")){p.setLong(1,id);try(ResultSet r=p.executeQuery()){r.next();return r.getObject(1,LocalDateTime.class);}}}
  static long scalar(DataSource ds,String q)throws Exception{try(Connection c=ds.getConnection();Statement s=c.createStatement();ResultSet r=s.executeQuery(q)){r.next();return r.getLong(1);}}
  static String rows(DataSource ds)throws Exception{StringBuilder b=new StringBuilder();try(Connection c=ds.getConnection();Statement s=c.createStatement()){for(String q:List.of("SELECT id,user_id,product_id,quantity,version,created_at,updated_at FROM cart_item ORDER BY id","SELECT id,stock,status,version,price,updated_at FROM product ORDER BY id")){try(ResultSet r=s.executeQuery(q)){while(r.next()){for(int i=1;i<=r.getMetaData().getColumnCount();i++)b.append(r.getString(i)).append('|');b.append('\n');}}}}return b.toString();}
  static Throwable invoke(Method m,Object bean,Object...a)throws Exception{try{m.invoke(bean,a);return null;}catch(InvocationTargetException e){return e.getCause();}}
  static void trace(String label) {
    for(int i=0;i<events.size();i++){Event e=events.get(i);System.out.println("SQL_TRACE "+label+" #"+(i+1)+" active="+e.active+" declaredIsolation="+e.declaredIsolation+" jdbcIsolation="+e.jdbcIsolation+" sql="+e.sql);}
    check(label+"-first-actor-lock",!events.isEmpty()&&events.get(0).sql.toLowerCase(Locale.ROOT).contains("from store_user ")&&events.get(0).sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE"));
    check(label+"-all-active-rc",events.stream().allMatch(e->e.active&&Objects.equals(e.declaredIsolation,Connection.TRANSACTION_READ_COMMITTED)&&e.jdbcIsolation==Connection.TRANSACTION_READ_COMMITTED));
    check(label+"-single-connection",events.stream().map(Event::connection).distinct().count()==1);
    check(label+"-no-product-for-update",events.stream().noneMatch(e->e.sql.toLowerCase(Locale.ROOT).contains("from product ")&&e.sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE")));
  }
  static void actorLockDisable(Connection root,DataSource ds,Object bean,Method add,Object actor,long pid,Class<?> ident)throws Exception {
    String before=rows(ds);
    LocalDateTime initial=stamp(ds,1);
    ExecutorService worker=Executors.newSingleThreadExecutor();
    Future<Throwable> pending=null;
    boolean committed=false;
    long started=System.nanoTime(),observedWaitMs=-1,blockingConnection;
    try(Statement s=root.createStatement();ResultSet r=s.executeQuery("SELECT CONNECTION_ID()")){r.next();blockingConnection=r.getLong(1);}
    try {
      root.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);
      root.setAutoCommit(false);
      try(Statement s=root.createStatement();ResultSet r=s.executeQuery("SELECT id FROM store_user WHERE id=1 FOR UPDATE")){check("mid-disable-locker-holds-user",r.next());}
      events.clear();CountDownLatch entered=new CountDownLatch(1);
      pending=worker.submit(()->{entered.countDown();return invoke(add,bean,actor,pid,1);});
      check("mid-disable-worker-entered",entered.await(5,TimeUnit.SECONDS));
      long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(8);
      long waits=0;
      while(System.nanoTime()<deadline) {
        try(Statement s=root.createStatement();ResultSet r=s.executeQuery("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.threads b ON b.THREAD_ID=w.BLOCKING_THREAD_ID WHERE b.PROCESSLIST_ID=CONNECTION_ID()")){r.next();waits=r.getLong(1);}
        if(waits>0){observedWaitMs=TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-started);break;}
        if(pending.isDone())break;
        Thread.sleep(40);
      }
      check("mid-disable-wait-observed-in-performance-schema",waits>0&&!pending.isDone());
      try(Statement s=root.createStatement()){check("mid-disable-update-one-user",s.executeUpdate("UPDATE store_user SET status='DISABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1")==1);}
      root.commit();committed=true;root.setAutoCommit(true);
      Throwable rejected=pending.get(20,TimeUnit.SECONDS);
      check("mid-disable-rejected-after-lock",rejected!=null&&rejected.getClass().getName().equals("org.csucampuscraft.storefront.auth.SessionExpiredException"));
      trace("mid-disable-waiter");check("mid-disable-only-user-query",events.size()==1);
      check("mid-disable-cart-and-products-zero-write",before.equals(rows(ds)));
      LocalDateTime disabled=stamp(ds,1);
      check("mid-disable-microsecond-auth-stamp-advanced",disabled.isAfter(initial)&&disabled.getNano()%1000==0);
      try(Statement s=root.createStatement()){s.executeUpdate("UPDATE store_user SET status='ENABLED',updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND) WHERE id=1");}
      LocalDateTime enabled=stamp(ds,1);
      check("mid-disable-reenable-stamp-advanced",enabled.isAfter(disabled));
      events.clear();Throwable old=invoke(add,bean,actor,pid,1);
      check("mid-disable-old-actor-does-not-revive",old!=null&&old.getClass().getName().equals("org.csucampuscraft.storefront.auth.SessionExpiredException"));
      trace("mid-disable-reenabled-old-actor");check("mid-disable-reenable-zero-write",before.equals(rows(ds)));
      System.out.println("AUTH_LOCK_WAIT {\"observedBy\":\"performance_schema.data_lock_waits joined blocking root connection\",\"blockingConnectionId\":"+blockingConnection+",\"waitObservedMillis\":"+observedWaitMs+",\"elapsedMillis\":"+TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-started)+",\"initialStampUtc\":\""+initial+"\",\"disabledStampUtc\":\""+disabled+"\",\"reenabledStampUtc\":\""+enabled+"\",\"boundSeconds\":20,\"cartAndProductsUnchanged\":true}");
    } finally {
      if(!committed)root.rollback();
      root.setAutoCommit(true);
      if(pending!=null&&!pending.isDone())pending.cancel(true);
      worker.shutdownNow();worker.awaitTermination(2,TimeUnit.SECONDS);
    }
  }
  public static void main(String[]args)throws Exception {
    ConfigurableApplicationContext ctx=null;Connection root=null;String originalStatus=null,productStatus=null;Long productFixture=null;LocalDateTime originalStamp=null;boolean complete=false;
    try {
      ctx=SpringApplication.run(Class.forName("org.csucampuscraft.storefront.CSUCampusCraftUserApplication"),"--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default");
      DataSource ds=ctx.getBean(DataSource.class);Class<?> ident=Class.forName("org.csucampuscraft.storefront.auth.SessionIdentity");
      Object actor=identity(ident,1,stamp(ds,1));Object bean=ctx.getBean(Class.forName("org.csucampuscraft.storefront.cart.CartService"));
      Method add=bean.getClass().getMethod("add",ident,long.class,int.class),change=bean.getClass().getMethod("changeQuantity",ident,long.class,int.class,long.class),remove=bean.getClass().getMethod("remove",ident,long.class,long.class),quantity=bean.getClass().getMethod("quantityFor",long.class);
      long pid=scalar(ds,"SELECT p.id FROM product p WHERE p.status='ON_SALE' AND p.stock>=3 AND NOT EXISTS(SELECT 1 FROM cart_item c WHERE c.user_id=1 AND c.product_id=p.id) ORDER BY p.id LIMIT 1");
      ctx.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new Trace());
      events.clear();check("add-success",invoke(add,bean,actor,pid,1)==null);trace("add");
      long iid=scalar(ds,"SELECT id FROM cart_item WHERE user_id=1 AND product_id="+pid),v=scalar(ds,"SELECT version FROM cart_item WHERE id="+iid);check("new-row-version-zero",v==0);
      events.clear();check("change-success",invoke(change,bean,actor,iid,2,v)==null);trace("change");check("change-version-plus-one",scalar(ds,"SELECT version FROM cart_item WHERE id="+iid)==v+1);
      check("quantity-version-conditional-update",events.stream().anyMatch(e->e.sql.toLowerCase(Locale.ROOT).startsWith("update cart_item ")&&e.sql.toLowerCase(Locale.ROOT).matches(".*where.*version\\s*=.*")));
      String before=rows(ds);v++;events.clear();check("noop-success",invoke(change,bean,actor,iid,2,v)==null);trace("no-op");check("no-op-no-dml",events.stream().noneMatch(e->e.sql.toLowerCase(Locale.ROOT).matches("^(insert|update|delete).*")));check("no-op-zero-write",before.equals(rows(ds)));
      before=rows(ds);events.clear();check("stale-version-refused",invoke(change,bean,actor,iid,3,v-1)!=null);trace("stale-version");check("stale-zero-write",before.equals(rows(ds)));
      Object[] denied={null,identity(ident,1,stamp(ds,1).minusNanos(1000)),identity(ident,4,stamp(ds,4))};String[] tags={"missing-actor","stale-stamp","admin-role"};
      for(int i=0;i<denied.length;i++){before=rows(ds);events.clear();check(tags[i]+"-refused",invoke(remove,bean,denied[i],iid,v)!=null);if(i>0){trace(tags[i]);check(tags[i]+"-only-actor-query",events.size()==1);}else check("missing-actor-no-sql",events.isEmpty());check(tags[i]+"-zero-write",before.equals(rows(ds)));}
      root=DriverManager.getConnection("jdbc:mysql://127.0.0.1:"+System.getenv("STEP07_MYSQL_PORT")+"/csucampuscraft?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true","root",System.getenv("STEP07_ROOT_PASSWORD"));
      try(Statement s=root.createStatement()){s.execute("SET SESSION time_zone='+00:00'");}
      productFixture=pid;
      try(PreparedStatement p=root.prepareStatement("SELECT status FROM product WHERE id=?")){p.setLong(1,pid);try(ResultSet r=p.executeQuery()){r.next();productStatus=r.getString(1);}}
      try(PreparedStatement p=root.prepareStatement("UPDATE product SET status='DRAFT',updated_at=updated_at WHERE id=?")){p.setLong(1,pid);p.executeUpdate();}
      before=rows(ds);events.clear();Throwable unavailable=invoke(change,bean,actor,iid,3,v);
      check("unavailable-change-business-exception",unavailable!=null&&unavailable.getClass().getName().endsWith("BusinessException"));
      check("unavailable-change-stable-code",Objects.equals(unavailable.getClass().getMethod("getCode").invoke(unavailable),"CART_PRODUCT_UNAVAILABLE"));
      Object httpStatus=unavailable.getClass().getMethod("getStatus").invoke(unavailable);
      check("unavailable-change-409",((Number)httpStatus.getClass().getMethod("value").invoke(httpStatus)).intValue()==409);
      trace("unavailable-change");check("unavailable-change-zero-write",before.equals(rows(ds)));
      events.clear();check("unavailable-same-quantity-noop",invoke(change,bean,actor,iid,2,v)==null);trace("unavailable-noop");check("unavailable-noop-zero-write",before.equals(rows(ds)));
      try(PreparedStatement p=root.prepareStatement("UPDATE product SET status=?,updated_at=updated_at WHERE id=?")){p.setString(1,productStatus);p.setLong(2,pid);p.executeUpdate();}
      try(Statement s=root.createStatement()){s.execute("SET SESSION time_zone='+00:00'");try(ResultSet r=s.executeQuery("SELECT status,updated_at FROM store_user WHERE id=1")){r.next();originalStatus=r.getString(1);originalStamp=r.getObject(2,LocalDateTime.class);}s.executeUpdate("UPDATE store_user SET status='DISABLED',updated_at=updated_at WHERE id=1");}
      before=rows(ds);events.clear();check("disabled-refused",invoke(remove,bean,actor,iid,v)!=null);trace("disabled");check("disabled-only-actor-query",events.size()==1);check("disabled-zero-write",before.equals(rows(ds)));
      try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=1")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}
      actorLockDisable(root,ds,bean,add,actor,pid,ident);
      // The preceding root fixture is test-only; restore the exact original account after recording old-session rejection.
      try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=1")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}
      events.clear();check("remove-success",invoke(remove,bean,actor,iid,v)==null);trace("remove");check("removed-row-gone",scalar(ds,"SELECT COUNT(*) FROM cart_item WHERE id="+iid)==0);
      events.clear();Object sum=quantity.invoke(bean,1L);check("quantity-sum-value",((Number)sum).longValue()==scalar(ds,"SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id=1"));
      check("quantity-sql-sum-no-join-or-count",events.size()==1&&events.get(0).sql.toLowerCase(Locale.ROOT).contains("sum(quantity)")&&events.get(0).sql.toLowerCase(Locale.ROOT).contains("where user_id")&&!events.get(0).sql.toLowerCase(Locale.ROOT).contains("join")&&!events.get(0).sql.toLowerCase(Locale.ROOT).contains("count("));
      System.out.println("BADGE_SQL "+events.get(0).sql);
      complete=true;
    } finally {
      if(root!=null){if(!root.getAutoCommit()){root.rollback();root.setAutoCommit(true);}if(originalStatus!=null)try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=1")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}if(productStatus!=null)try(PreparedStatement p=root.prepareStatement("UPDATE product SET status=?,updated_at=updated_at WHERE id=?")){p.setString(1,productStatus);p.setLong(2,productFixture);p.executeUpdate();}root.close();}
      if(ctx!=null)ctx.close();
      System.out.println("{\"overall\":\""+(complete&&checks.stream().allMatch(Boolean::booleanValue)?"PASS":"FAIL")+"\",\"checks\":"+checks.size()+",\"secretsRecorded\":false,\"scope\":\"actual merged user JAR; serial cart calls and observed actor-lock/disable interleaving; no cart/order concurrency or injected fault\"}");
      for(int i=0;i<labels.size();i++)System.out.println("CHECK "+labels.get(i)+"="+checks.get(i));
    }
  }
}
