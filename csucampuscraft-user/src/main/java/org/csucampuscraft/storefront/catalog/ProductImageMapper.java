package org.csucampuscraft.storefront.catalog;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface ProductImageMapper {
    @Select("""
            SELECT id, product_id, image_path, alt_text, sort_order
            FROM product_image WHERE product_id = #{productId}
            ORDER BY sort_order ASC, id ASC
            """)
    List<ProductImage> selectForProduct(@Param("productId") long productId);
}
