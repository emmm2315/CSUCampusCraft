package org.csucampuscraft.storefront.cart;

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
public interface CartItemMapper extends BaseMapper<CartItem> {
    @Select("SELECT id,user_id,product_id,quantity,version,created_at,updated_at "
            + "FROM cart_item WHERE user_id=#{userId} ORDER BY id ASC")
    List<CartItem> selectByUser(@Param("userId") long userId);

    @Select("SELECT id,user_id,product_id,quantity,version,created_at,updated_at "
            + "FROM cart_item WHERE id=#{itemId}")
    CartItem selectItem(@Param("itemId") long itemId);

    @Select("SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id=#{userId}")
    long selectQuantity(@Param("userId") long userId);

    @Select("""
            SELECT ci.id,ci.product_id,ci.quantity,ci.version,
                   p.sku,p.name,p.cover_image,p.price,p.stock,p.status
              FROM cart_item ci LEFT JOIN product p ON p.id=ci.product_id
             WHERE ci.user_id=#{userId} ORDER BY ci.id ASC
            """)
    List<CartLine> selectLines(@Param("userId") long userId);

    @Select("SELECT id,sku,category_id,name,cover_image,price,stock,status,version "
            + "FROM product WHERE id=#{productId}")
    Product selectProduct(@Param("productId") long productId);

    @Insert("""
            INSERT INTO cart_item(user_id,product_id,quantity,version)
            VALUES(#{item.userId},#{item.productId},#{item.quantity},0)
            """)
    @Options(useGeneratedKeys = true, keyProperty = "item.id", keyColumn = "id")
    int insertItem(@Param("item") CartItem item);

    @Update("""
            UPDATE cart_item SET quantity=#{quantity},version=version+1
             WHERE id=#{itemId} AND user_id=#{userId} AND version=#{version}
                   AND version<9223372036854775807
            """)
    int updateQuantity(@Param("userId") long userId, @Param("itemId") long itemId,
                       @Param("quantity") int quantity, @Param("version") long version);

    @Delete("DELETE FROM cart_item WHERE id=#{itemId} AND user_id=#{userId} AND version=#{version}")
    int deleteItem(@Param("userId") long userId, @Param("itemId") long itemId,
                   @Param("version") long version);
}
