package org.csucampuscraft.storefront.order;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;
import org.csucampuscraft.storefront.catalog.Product;

@Mapper
public interface OrderMapper extends BaseMapper<SalesOrder> {
    String COLUMNS = "id,order_no,user_id,status,total_amount,receiver_name,receiver_phone,receiver_address,"
            + "created_at,updated_at,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at";
    String OWN_WHERE = "<where>user_id=#{userId}"
            + "<if test='query.orderNo != null and query.orderNo.length() > 0'> AND order_no=#{query.orderNo}</if>"
            + "<if test='query.status != \"ALL\"'> AND status=#{query.status}</if></where>";

    @Select("<script>SELECT COUNT(*) FROM sales_order " + OWN_WHERE + "</script>")
    long countOwn(@Param("userId") long userId, @Param("query") OrderQuery query);

    @Select("<script>SELECT " + COLUMNS + " FROM sales_order " + OWN_WHERE
            + " ORDER BY created_at DESC,id DESC LIMIT #{query.size} OFFSET #{query.offset}</script>")
    List<SalesOrder> selectOwn(@Param("userId") long userId, @Param("query") OrderQuery query);

    @Select("SELECT " + COLUMNS + " FROM sales_order WHERE user_id=#{userId} AND order_no=#{orderNo}")
    SalesOrder selectOwnOrder(@Param("userId") long userId, @Param("orderNo") String orderNo);

    @Insert("""
            INSERT INTO sales_order(order_no,user_id,status,total_amount,
                    receiver_name,receiver_phone,receiver_address,payment_method,payment_no,paid_at)
            VALUES(#{order.orderNo},#{order.userId},'PENDING_PAYMENT',#{order.totalAmount},
                    #{order.receiverName},#{order.receiverPhone},#{order.receiverAddress},NULL,NULL,NULL)
            """)
    @Options(useGeneratedKeys = true, keyProperty = "order.id", keyColumn = "id")
    int insertOrder(@Param("order") SalesOrder order);

    @Select("SELECT id,sku,category_id,name,cover_image,price,stock,status,version "
            + "FROM product WHERE id=#{productId} FOR UPDATE")
    Product selectProductForUpdate(@Param("productId") long productId);

    @Update("""
            UPDATE product SET stock=stock-#{quantity},version=version+1
             WHERE id=#{productId} AND stock>=#{quantity} AND version=#{version}
                   AND status='ON_SALE' AND version<9223372036854775807
            """)
    int deductProduct(@Param("productId") long productId, @Param("quantity") int quantity,
                      @Param("version") long version);

    @Delete("""
            DELETE FROM cart_item WHERE id=#{itemId} AND user_id=#{userId}
                   AND product_id=#{productId} AND quantity=#{quantity} AND version=#{version}
            """)
    int deleteConfirmedCart(@Param("userId") long userId, @Param("itemId") long itemId,
                            @Param("productId") long productId, @Param("quantity") int quantity,
                            @Param("version") long version);
}
