import org.apache.ibatis.reflection.SystemMetaObject;
import org.csucampuscraft.storefront.order.OrderQuery;

public class OrderQueryMetaProbe {
    public static void main(String[] args) {
        var query = OrderQuery.bind(null,null,null,null);
        var meta = SystemMetaObject.forObject(query);
        System.out.println("orderNo_getter="+meta.hasGetter("orderNo"));
        System.out.println("size_getter="+meta.hasGetter("size"));
        System.out.println("offset_getter="+meta.hasGetter("offset"));
        System.out.println("getOffset_getter="+meta.hasGetter("getOffset"));
        try { System.out.println("offset_value="+meta.getValue("offset")); }
        catch (RuntimeException failure) { System.out.println("offset_failure="+failure.getClass().getSimpleName()); }
        System.out.println("direct_getOffset="+query.getOffset());
    }
}
