package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface ProductImageMapper extends BaseMapper<ProductImage> {
    @Select("SELECT id,product_id,image_path,alt_text,sort_order FROM product_image "
            + "WHERE product_id=#{productId} ORDER BY sort_order ASC,id ASC")
    List<ProductImage> selectImages(@Param("productId") long productId);

    @Select("SELECT id,product_id,image_path,alt_text,sort_order FROM product_image "
            + "WHERE product_id=#{productId} AND id=#{imageId}")
    ProductImage selectImage(@Param("productId") long productId, @Param("imageId") long imageId);

    @Insert("""
            INSERT INTO product_image(product_id,image_path,alt_text,sort_order)
            VALUES(#{image.productId},#{image.imagePath},#{image.altText},#{image.sortOrder})
            """)
    @Options(useGeneratedKeys = true, keyProperty = "image.id", keyColumn = "id")
    int insertImage(@Param("image") ProductImage image);

    @Update("""
            UPDATE product_image SET image_path=#{image.imagePath},alt_text=#{image.altText},
                sort_order=#{image.sortOrder}
            WHERE product_id=#{image.productId} AND id=#{image.id}
            """)
    int updateImage(@Param("image") ProductImage image);

    @Delete("DELETE FROM product_image WHERE product_id=#{productId} AND id=#{imageId}")
    int deleteImage(@Param("productId") long productId, @Param("imageId") long imageId);

    @Update("""
            UPDATE product SET version=version+1
            WHERE id=#{productId} AND version=#{expectedVersion} AND version<9223372036854775807
            """)
    int incrementProductVersion(@Param("productId") long productId,
                                @Param("expectedVersion") long expectedVersion);
}
