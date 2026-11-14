import java.lang.reflect.*;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.*;
import javax.sql.DataSource;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.*;
import org.apache.ibatis.session.*;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Standalone actual-JAR Service probe. No endpoint, no fault injection, no concurrent transactions. */
public final class AlbumWriteProbe {
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
  static long version(DataSource ds)throws Exception{try(Connection c=ds.getConnection();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT version FROM product WHERE id=1")){r.next();return r.getLong(1);}}
  static long image(DataSource ds)throws Exception{try(Connection c=ds.getConnection();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT id FROM product_image WHERE product_id=1 AND alt_text='native STEP06' ORDER BY id DESC LIMIT 1")){r.next();return r.getLong(1);}}
  static String rows(DataSource ds)throws Exception{StringBuilder b=new StringBuilder();try(Connection c=ds.getConnection();Statement s=c.createStatement()){for(String q:List.of("SELECT id,version,cover_image,stock,status FROM product ORDER BY id","SELECT id,product_id,image_path,COALESCE(alt_text,''),sort_order FROM product_image ORDER BY id")){try(ResultSet r=s.executeQuery(q)){while(r.next()){for(int i=1;i<=r.getMetaData().getColumnCount();i++)b.append(r.getString(i)).append('|');b.append('\n');}}}}return b.toString();}
  static Throwable invoke(Method m,Object bean,Object...a)throws Exception{try{m.invoke(bean,a);return null;}catch(InvocationTargetException e){return e.getCause();}}
  static boolean table(Event e,String t){return e.sql.toLowerCase(Locale.ROOT).contains("from "+t+" ");}
  static void trace(String label,boolean parent) {
    for(int i=0;i<events.size();i++){Event e=events.get(i);System.out.println("SQL_TRACE "+label+" #"+(i+1)+" active="+e.active+" declaredIsolation="+e.declaredIsolation+" jdbcIsolation="+e.jdbcIsolation+" sql="+e.sql);}
    check(label+"-first-actor-lock",!events.isEmpty()&&table(events.get(0),"store_user")&&events.get(0).sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE"));
    check(label+"-all-active-rc",events.stream().allMatch(e->e.active&&Objects.equals(e.declaredIsolation,Connection.TRANSACTION_READ_COMMITTED)&&e.jdbcIsolation==Connection.TRANSACTION_READ_COMMITTED));
    check(label+"-single-connection",events.stream().map(Event::connection).distinct().count()==1);
    if(parent)check(label+"-second-parent-lock",events.size()>1&&table(events.get(1),"product")&&events.get(1).sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE"));
  }
  public static void main(String[]args)throws Exception {
    ConfigurableApplicationContext ctx=null;Connection root=null;String originalStatus=null;LocalDateTime originalStamp=null;boolean complete=false;
    try {
      ctx=SpringApplication.run(Class.forName("org.csucampuscraft.admin.CSUCampusCraftAdminApplication"),"--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default");
      DataSource ds=ctx.getBean(DataSource.class);Class<?> ident=Class.forName("org.csucampuscraft.admin.auth.SessionIdentity");Class<?> input=Class.forName("org.csucampuscraft.admin.catalog.ProductImageInput");
      Constructor<?> form=input.getConstructor(String.class,String.class,String.class,String.class);
      Object actor=identity(ident,4,stamp(ds,4));Object bean=ctx.getBean(Class.forName("org.csucampuscraft.admin.catalog.ProductImageService"));
      Method create=bean.getClass().getMethod("create",ident,long.class,input),update=bean.getClass().getMethod("update",ident,long.class,long.class,input),remove=bean.getClass().getMethod("remove",ident,long.class,long.class,String.class);
      ctx.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new Trace());
      long v=version(ds);events.clear();check("create-success",invoke(create,bean,actor,1L,form.newInstance("images/catalog-placeholder.svg","native STEP06","17",String.valueOf(v)))==null);trace("create",true);
      check("create-one-parent-bump",version(ds)==v+1);check("create-version-conditional-bump",events.stream().anyMatch(e->e.sql.toLowerCase(Locale.ROOT).contains("update product ")&&e.sql.toLowerCase(Locale.ROOT).matches(".*version\\s*=\\s*version\\s*\\+.*")&&e.sql.toLowerCase(Locale.ROOT).matches(".*where.*version\\s*=.*")));
      long image=image(ds);v=version(ds);events.clear();check("edit-success",invoke(update,bean,actor,1L,image,form.newInstance("images/catalog-placeholder.svg","native changed","18",String.valueOf(v)))==null);trace("edit",true);
      check("edit-scoped-image-query",events.stream().skip(2).anyMatch(e->table(e,"product_image")&&e.sql.contains("product_id")&&e.sql.toLowerCase(Locale.ROOT).contains("id")));check("edit-one-parent-bump",version(ds)==v+1);
      String before=rows(ds);v=version(ds);events.clear();check("no-op-success",invoke(update,bean,actor,1L,image,form.newInstance("images/catalog-placeholder.svg","native changed","18",String.valueOf(v)))==null);trace("no-op",true);check("no-op-no-dml",events.stream().noneMatch(e->e.sql.toLowerCase(Locale.ROOT).matches("^(insert|update|delete).*")));check("no-op-zero-write",before.equals(rows(ds)));
      before=rows(ds);events.clear();check("stale-version-refused",invoke(update,bean,actor,1L,image,form.newInstance("images/catalog-placeholder.svg","ignored","18","0"))!=null);trace("stale-version",true);check("version-before-image-lookup",events.size()==2);check("stale-zero-write",before.equals(rows(ds)));
      before=rows(ds);events.clear();check("invalid-path-refused",invoke(create,bean,actor,1L,form.newInstance("images/../bad.svg","ignored","0",String.valueOf(version(ds))))!=null);trace("invalid-path",true);check("invalid-path-no-dml",events.stream().noneMatch(e->e.sql.toLowerCase(Locale.ROOT).matches("^(insert|update|delete).*")));check("invalid-path-zero-write",before.equals(rows(ds)));
      Object[] denied={null,identity(ident,4,stamp(ds,4).minusNanos(1000)),identity(ident,1,stamp(ds,1))};String[] tags={"missing-actor","stale-stamp","customer-role"};
      for(int i=0;i<denied.length;i++){before=rows(ds);events.clear();check(tags[i]+"-refused",invoke(remove,bean,denied[i],1L,image,String.valueOf(version(ds)))!=null);if(i>0){trace(tags[i],false);check(tags[i]+"-only-actor-query",events.size()==1);}else check("missing-actor-no-sql",events.isEmpty());check(tags[i]+"-zero-write",before.equals(rows(ds)));}
      root=DriverManager.getConnection("jdbc:mysql://127.0.0.1:"+System.getenv("STEP06_MYSQL_PORT")+"/csucampuscraft?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true","root",System.getenv("STEP06_ROOT_PASSWORD"));
      try(Statement s=root.createStatement()){s.execute("SET SESSION time_zone='+00:00'");try(ResultSet r=s.executeQuery("SELECT status,updated_at FROM store_user WHERE id=4")){r.next();originalStatus=r.getString(1);originalStamp=r.getObject(2,LocalDateTime.class);}s.executeUpdate("UPDATE store_user SET status='DISABLED',updated_at=updated_at WHERE id=4");}
      before=rows(ds);events.clear();check("disabled-actor-refused",invoke(remove,bean,actor,1L,image,String.valueOf(version(ds)))!=null);trace("disabled-actor",false);check("disabled-only-actor-query",events.size()==1);check("disabled-zero-write",before.equals(rows(ds)));
      try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=4")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}
      v=version(ds);events.clear();check("remove-success",invoke(remove,bean,actor,1L,image,String.valueOf(v))==null);trace("remove",true);check("remove-one-parent-bump",version(ds)==v+1);check("remove-scoped-image-query",events.stream().skip(2).anyMatch(e->table(e,"product_image")&&e.sql.contains("product_id")));
      complete=true;
    } finally {
      if(root!=null){if(originalStatus!=null)try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=4")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}root.close();}
      if(ctx!=null)ctx.close();
      System.out.println("{\"overall\":\""+(complete&&checks.stream().allMatch(Boolean::booleanValue)?"PASS":"FAIL")+"\",\"checks\":"+checks.size()+",\"secretsRecorded\":false,\"scope\":\"actual JAR Service; serial direct invocation; no production route/fault hook/concurrency\"}");
      for(int i=0;i<labels.size();i++)System.out.println("CHECK "+labels.get(i)+"="+checks.get(i));
    }
  }
}
