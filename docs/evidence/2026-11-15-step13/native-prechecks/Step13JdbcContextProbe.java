import java.sql.*;
import javax.sql.DataSource;
import org.springframework.boot.*;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

public class Step13JdbcContextProbe {
 public static void main(String[] args) throws Exception {
  String module=args[0];
  String main=module.equals("user")?"org.csucampuscraft.storefront.CSUCampusCraftUserApplication":"org.csucampuscraft.admin.CSUCampusCraftAdminApplication";
  try(ConfigurableApplicationContext app=new SpringApplicationBuilder(Class.forName(main)).web(WebApplicationType.NONE).bannerMode(Banner.Mode.OFF).properties("spring.main.log-startup-info=false","logging.level.root=ERROR").run();
      Connection c=app.getBean(DataSource.class).getConnection();
      Statement stmt=c.createStatement();
      ResultSet r=stmt.executeQuery("SELECT @@session.time_zone,@@server_uuid,@@port,DATABASE(),CONNECTION_ID()")) {
    if(!r.next() || !"+00:00".equals(r.getString(1)))throw new AssertionError("Actual Hikari JDBC UTC required");
    System.out.println("STEP13_JDBC_CONTEXT {\"module\":\""+module+"\",\"session_timezone\":\""+r.getString(1)+"\",\"mysql_uuid\":\""+r.getString(2)+"\",\"mysql_port\":"+r.getInt(3)+",\"schema\":\""+r.getString(4)+"\",\"connection_id\":"+r.getLong(5)+",\"source\":\"fresh tested application Spring context and Hikari DataSource\",\"writes\":false}");
  }
 }
}
