package org.csucampuscraft.storefront.payment;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;
import org.csucampuscraft.storefront.catalog.Product;
import org.csucampuscraft.storefront.order.OrderMapper;
import org.csucampuscraft.storefront.order.SalesOrder;

/** Only STEP10 state transitions; the existing order creation mapper remains unchanged. */
@Mapper
public interface OrderActionMapper {
    @Select("SELECT " + OrderMapper.COLUMNS
            + " FROM sales_order WHERE order_no=#{orderNo} AND user_id=#{userId} FOR UPDATE")
    SalesOrder selectOwnForUpdate(@Param("userId") long userId, @Param("orderNo") String orderNo);

    @Update("""
            UPDATE sales_order
               SET status='PAID',payment_method='MOCK',payment_no=#{paymentNo},
                   paid_at=GREATEST(CURRENT_TIMESTAMP(6),created_at)
             WHERE id=#{orderId} AND user_id=#{userId} AND status='PENDING_PAYMENT'
                   AND payment_method IS NULL AND payment_no IS NULL AND paid_at IS NULL
            """)
    int markPaid(@Param("userId") long userId, @Param("orderId") long orderId,
                 @Param("paymentNo") String paymentNo);

    @Select("SELECT id,sku,name,cover_image,price,stock,status,version "
            + "FROM product WHERE id=#{productId} FOR UPDATE")
    Product selectProductForUpdate(@Param("productId") long productId);

    @Update("""
            UPDATE product SET stock=stock+#{quantity},version=version+1
             WHERE id=#{productId} AND version=#{version}
                   AND stock<=2147483647-#{quantity} AND version<9223372036854775807
            """)
    int restockProduct(@Param("productId") long productId, @Param("quantity") int quantity,
                       @Param("version") long version);

    @Update("""
            UPDATE sales_order
               SET status='CANCELLED',cancelled_at=GREATEST(CURRENT_TIMESTAMP(6),created_at)
             WHERE id=#{orderId} AND user_id=#{userId} AND status='PENDING_PAYMENT'
                   AND payment_method IS NULL AND payment_no IS NULL AND paid_at IS NULL
                   AND cancelled_at IS NULL
            """)
    int markCancelled(@Param("userId") long userId, @Param("orderId") long orderId);
}
