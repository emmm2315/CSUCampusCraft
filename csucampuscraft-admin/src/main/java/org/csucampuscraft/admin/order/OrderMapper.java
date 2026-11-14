package org.csucampuscraft.admin.order;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface OrderMapper extends BaseMapper<SalesOrder> {
    String COLUMNS = "id,order_no,user_id,status,total_amount,receiver_name,receiver_phone,receiver_address,"
            + "created_at,updated_at,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at";
    String READ_COLUMNS = "o.id,o.order_no,o.user_id,o.status,o.total_amount,o.receiver_name,o.receiver_phone,"
            + "o.receiver_address,o.created_at,o.updated_at,o.payment_method,o.payment_no,o.paid_at,"
            + "o.cancelled_at,o.shipped_at,o.completed_at,u.username AS customer_username,"
            + "u.display_name AS customer_display_name";
    String FILTER = "<where>1=1"
            + "<if test='query.orderNo != null and query.orderNo.length() > 0'> AND o.order_no=#{query.orderNo}</if>"
            + "<if test='query.status != \"ALL\"'> AND o.status=#{query.status}</if>"
            + "<if test='query.userId != null'> AND o.user_id=#{query.userId}</if></where>";

    @Select("<script>SELECT COUNT(*) FROM sales_order o " + FILTER + "</script>")
    long count(@Param("query") OrderQuery query);

    @Select("<script>SELECT " + READ_COLUMNS + " FROM sales_order o LEFT JOIN store_user u ON u.id=o.user_id "
            + FILTER + " ORDER BY o.created_at DESC,o.id DESC LIMIT #{query.size} OFFSET #{query.offset}</script>")
    List<SalesOrder> selectPage(@Param("query") OrderQuery query);

    @Select("SELECT id,username,display_name,status FROM store_user WHERE id=#{userId} AND role='CUSTOMER'")
    OrderCustomer selectCustomer(@Param("userId") long userId);

    @Select("SELECT " + READ_COLUMNS + " FROM sales_order o LEFT JOIN store_user u ON u.id=o.user_id "
            + "WHERE o.order_no=#{orderNo}")
    SalesOrder selectOrder(@Param("orderNo") String orderNo);

    @Select("SELECT " + COLUMNS + " FROM sales_order WHERE order_no=#{orderNo} FOR UPDATE")
    SalesOrder selectForUpdate(@Param("orderNo") String orderNo);

    @Update("""
            UPDATE sales_order SET status='SHIPPED',shipped_at=GREATEST(CURRENT_TIMESTAMP(6),paid_at)
             WHERE id=#{orderId} AND status='PAID' AND payment_method='MOCK'
                   AND payment_no IS NOT NULL AND paid_at IS NOT NULL AND shipped_at IS NULL
            """)
    int markShipped(@Param("orderId") long orderId);
}
