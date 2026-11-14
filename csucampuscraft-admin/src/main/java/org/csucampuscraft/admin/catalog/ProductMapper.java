package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.*;

@Mapper
public interface ProductMapper extends BaseMapper<Product> {
    String COLUMNS = "p.id,p.sku,p.category_id,p.name,p.summary,p.description,p.cover_image,p.price,"
            + "p.stock,p.status,p.sort_order,p.version,p.created_at,p.updated_at";
    String FROM = " FROM product p JOIN category c ON c.id=p.category_id ";
    String WHERE = """
            <bind name="likePattern" value="query.getLikePattern()"/>
            WHERE 1=1
            <if test="query.categoryId != null">
                <choose>
                    <when test="rootScope">AND c.parent_id=#{query.categoryId}</when>
                    <otherwise>AND p.category_id=#{query.categoryId}</otherwise>
                </choose>
            </if>
            <if test="query.status.name() != 'ALL'">AND p.status=#{query.status}</if>
            <if test="likePattern != null">AND p.name LIKE #{likePattern} ESCAPE '!'</if>
            """;

    @Select("<script>SELECT COUNT(*)" + FROM + WHERE + "</script>")
    long countProducts(@Param("query") ProductQuery query, @Param("rootScope") boolean rootScope);

    @Select("<script>SELECT " + COLUMNS + ",c.name AS category_name" + FROM + WHERE
            + " ORDER BY p.sort_order ASC,p.id ASC LIMIT #{query.size} OFFSET #{offset}</script>")
    List<Product> selectProducts(@Param("query") ProductQuery query, @Param("rootScope") boolean rootScope,
                                 @Param("offset") long offset);

    @Select("SELECT " + COLUMNS + ",c.name AS category_name" + FROM + " WHERE p.id=#{id}")
    Product selectProduct(@Param("id") long id);

    @Select("SELECT " + COLUMNS + " FROM product p WHERE p.id=#{id} FOR UPDATE")
    Product lockProduct(@Param("id") long id);

    @Select("SELECT id,code,parent_id,name,sort_order FROM category ORDER BY sort_order ASC,id ASC")
    List<Category> selectCategories();

    @Select("SELECT id,code,parent_id,name,sort_order FROM category WHERE id=#{id}")
    Category selectCategory(@Param("id") long id);

    @Select("SELECT id,code,parent_id,name,sort_order FROM category WHERE id=#{id} FOR UPDATE")
    Category lockCategory(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM product WHERE sku=#{sku}")
    long countSku(@Param("sku") String sku);

    @Insert("""
            INSERT INTO product(sku,category_id,name,summary,description,cover_image,price,stock,status,sort_order,version)
            VALUES(#{product.sku},#{product.categoryId},#{product.name},#{product.summary},#{product.description},
                   #{product.coverImage},#{product.price},#{product.stock},'DRAFT',#{product.sortOrder},0)
            """)
    @Options(useGeneratedKeys = true, keyProperty = "product.id", keyColumn = "id")
    int insertProduct(@Param("product") Product product);

    @Update("""
            UPDATE product SET category_id=#{product.categoryId},name=#{product.name},
                summary=#{product.summary},description=#{product.description},cover_image=#{product.coverImage},
                price=#{product.price},sort_order=#{product.sortOrder},version=version+1
            WHERE id=#{product.id} AND version=#{expectedVersion} AND version<9223372036854775807
            """)
    int updateDetails(@Param("product") Product product, @Param("expectedVersion") long expectedVersion);

    @Update("""
            UPDATE product SET status=#{target},version=version+1
            WHERE id=#{id} AND version=#{expectedVersion} AND status=#{expectedStatus}
              AND version<9223372036854775807
            """)
    int updateStatus(@Param("id") long id, @Param("expectedVersion") long expectedVersion,
                     @Param("expectedStatus") String expectedStatus, @Param("target") String target);

    @Update("""
            UPDATE product SET stock=stock+#{quantity},version=version+1
            WHERE id=#{id} AND stock<=#{maximumBeforeAdd} AND version<9223372036854775807
            """)
    int addStock(@Param("id") long id, @Param("quantity") int quantity,
                 @Param("maximumBeforeAdd") int maximumBeforeAdd);
}
