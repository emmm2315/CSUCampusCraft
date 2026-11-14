package org.csucampuscraft.admin.order;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface OrderItemMapper extends BaseMapper<SalesOrderItem> {
    @Select("""
            SELECT id,order_id,product_id,sku_snapshot,product_name_snapshot,cover_image_snapshot,
                   unit_price,quantity,line_amount
              FROM sales_order_item WHERE order_id=#{orderId} ORDER BY id ASC
            """)
    List<SalesOrderItem> selectForOrder(@Param("orderId") long orderId);
}
