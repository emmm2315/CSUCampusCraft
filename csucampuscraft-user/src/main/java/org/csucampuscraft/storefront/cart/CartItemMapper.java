package org.csucampuscraft.storefront.cart;

import java.util.List;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;
import org.csucampuscraft.storefront.auth.StoreUser;
import org.csucampuscraft.storefront.catalog.Product;

@Mapper
public interface CartItemMapper {
    String ITEM_COLUMNS = "id,user_id AS userId,product_id AS productId,quantity,version";

    @Select("""
            SELECT id,username,display_name AS displayName,role,status,updated_at AS updatedAt
              FROM store_user WHERE id=#{userId} FOR UPDATE
            """)
    StoreUser lockUser(@Param("userId") long userId);

    @Select("""
            SELECT c.id,c.user_id AS userId,c.product_id AS productId,c.quantity,c.version,
                   p.sku,p.name,p.cover_image AS coverImage,p.price,p.stock,p.status
              FROM cart_item c LEFT JOIN product p ON p.id=c.product_id
             WHERE c.user_id=#{userId} ORDER BY c.id ASC
            """)
    List<CartItem> selectCart(@Param("userId") long userId);

    /** No product join/filter: invalid rows still contribute to the navigation badge. */
    @Select("SELECT COALESCE(SUM(quantity),0) FROM cart_item WHERE user_id=#{userId}")
    long sumQuantity(@Param("userId") long userId);

    @Select("SELECT " + ITEM_COLUMNS + " FROM cart_item WHERE user_id=#{userId} AND product_id=#{productId}")
    CartItem selectForProduct(@Param("userId") long userId, @Param("productId") long productId);

    @Select("SELECT " + ITEM_COLUMNS + " FROM cart_item WHERE id=#{id}")
    CartItem selectItem(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM cart_item WHERE user_id=#{userId}")
    long countKinds(@Param("userId") long userId);

    @Select("""
            SELECT id,sku,name,cover_image AS coverImage,price,stock,status,version
              FROM product WHERE id=#{productId} FOR UPDATE
            """)
    Product lockProduct(@Param("productId") long productId);

    @Insert("""
            INSERT INTO cart_item(user_id,product_id,quantity,version)
            VALUES(#{userId},#{productId},#{quantity},0)
            """)
    int insertItem(@Param("userId") long userId, @Param("productId") long productId,
                   @Param("quantity") int quantity);

    @Update("""
            UPDATE cart_item SET quantity=#{quantity},version=version+1
             WHERE id=#{id} AND user_id=#{userId} AND version=#{version}
               AND version<9223372036854775807
            """)
    int updateQuantity(@Param("id") long id, @Param("userId") long userId,
                       @Param("quantity") int quantity, @Param("version") long version);

    @Delete("DELETE FROM cart_item WHERE id=#{id} AND user_id=#{userId} AND version=#{version}")
    int deleteItem(@Param("id") long id, @Param("userId") long userId, @Param("version") long version);
}
