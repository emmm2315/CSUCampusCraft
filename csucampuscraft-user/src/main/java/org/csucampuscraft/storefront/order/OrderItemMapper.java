package org.csucampuscraft.storefront.order;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface OrderItemMapper extends BaseMapper<SalesOrderItem> {
    @Insert("""
            INSERT INTO sales_order_item(order_id,product_id,sku_snapshot,product_name_snapshot,
                    cover_image_snapshot,unit_price,quantity,line_amount)
            VALUES(#{item.orderId},#{item.productId},#{item.skuSnapshot},#{item.productNameSnapshot},
                    #{item.coverImageSnapshot},#{item.unitPrice},#{item.quantity},#{item.lineAmount})
            """)
    @Options(useGeneratedKeys = true, keyProperty = "item.id", keyColumn = "id")
    int insertItem(@Param("item") SalesOrderItem item);

    @Select("""
            SELECT id,order_id,product_id,sku_snapshot,product_name_snapshot,cover_image_snapshot,
                   unit_price,quantity,line_amount
              FROM sales_order_item WHERE order_id=#{orderId} ORDER BY id ASC
            """)
    List<SalesOrderItem> selectForOrder(@Param("orderId") long orderId);
}
