import java.util.Map;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.session.Configuration;
import org.csucampuscraft.admin.customer.CustomerMapper;
import org.csucampuscraft.admin.customer.CustomerQuery;
import org.csucampuscraft.admin.dashboard.DashboardMapper;

/** Offline annotation/record-binding observation only; no app, database, HTTP or business write. */
public final class MapperBindingPreflight {
    private static int checks;
    private static void check(boolean value) { if (!value) throw new AssertionError("offline binding"); checks++; }
    public static void main(String[] args) {
        Configuration c = new Configuration();
        c.setMapUnderscoreToCamelCase(true);
        c.addMapper(CustomerMapper.class);
        c.addMapper(DashboardMapper.class);
        CustomerQuery query = CustomerQuery.bind("  a%_!\\b  ", "DISABLED", "2", "10");
        check(query.offset() == 10);
        check(query.likePattern().equals("%a!%!_!!\\b%"));
        Map<String, Object> parameters = Map.of("query", query);
        BoundSql page = c.getMappedStatement(CustomerMapper.class.getName() + ".selectPage").getBoundSql(parameters);
        BoundSql count = c.getMappedStatement(CustomerMapper.class.getName() + ".count").getBoundSql(parameters);
        check(page.getSql().contains("ESCAPE '!'") && page.getSql().contains("ORDER BY id ASC"));
        check(count.getSql().contains("role='CUSTOMER'") && count.getSql().contains("ESCAPE '!'") && count.getSql().contains("status=?"));
        check(page.getParameterMappings().size() == 4 && count.getParameterMappings().size() == 2);
        for (var mapping : page.getParameterMappings()) {
            check(c.newMetaObject(parameters).getValue(mapping.getProperty()) != null);
        }
        BoundSql all = c.getMappedStatement(CustomerMapper.class.getName() + ".selectPage")
                .getBoundSql(Map.of("query", CustomerQuery.bind(null, null, null, null)));
        check(!all.getSql().contains(" LIKE ") && !all.getSql().contains("AND status"));
        CustomerQuery huge = CustomerQuery.bind(null, null, "9223372036854775807", "50");
        check(!huge.isOffsetRepresentable());
        BoundSql dashboard = c.getMappedStatement(DashboardMapper.class.getName() + ".selectSummary").getBoundSql(null);
        check(dashboard.getSql().split("SELECT COUNT", -1).length - 1 == 5);
        check(!page.getSql().contains("password_hash") && !dashboard.getSql().contains("password_hash"));
        System.out.println("{\"overall\":\"PASS\",\"checks\":" + checks
                + ",\"scope\":\"offline actual MyBatis record/annotation binding; no database or HTTP\"}");
    }
}
