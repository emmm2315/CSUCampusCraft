package org.csucampuscraft.admin.dashboard;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface DashboardMapper {
    @Select("""
            SELECT (SELECT COUNT(*) FROM product WHERE status='ON_SALE') AS on_sale_product_count,
                   (SELECT COUNT(*) FROM product WHERE status='DRAFT') AS draft_product_count,
                   (SELECT COUNT(*) FROM sales_order WHERE status='PAID') AS paid_order_count,
                   (SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED') AS enabled_customer_count,
                   (SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED') AS disabled_customer_count
            """)
    DashboardSummary selectSummary();
}
