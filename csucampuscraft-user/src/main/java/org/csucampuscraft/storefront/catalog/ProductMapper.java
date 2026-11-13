package org.csucampuscraft.storefront.catalog;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface ProductMapper {
    String COLUMNS = """
            p.id, p.sku, p.category_id, p.name, p.summary, p.description,
            p.cover_image, p.price, p.stock, p.status, p.sort_order, p.version, p.created_at
            """;
    String PUBLIC_FROM = """
             FROM product p
             JOIN category c ON c.id = p.category_id
             JOIN category t ON t.id = c.parent_id AND t.parent_id IS NULL
            """;
    /** Shared verbatim by count and list; all values remain prepared parameters. */
    String PUBLIC_WHERE = """
             WHERE p.status = 'ON_SALE'
             <if test="query.categoryId != null">AND t.id = #{query.categoryId}</if>
             <if test="query.type.suffix != null">
                 AND RIGHT(c.code, #{query.type.suffixLength}) = #{query.type.suffix}
             </if>
             <if test="query.likePattern != null">AND p.name LIKE #{query.likePattern} ESCAPE '!'</if>
            """;

    @Select("<script>SELECT COUNT(*) " + PUBLIC_FROM + PUBLIC_WHERE + "</script>")
    long countPublic(@Param("query") CatalogQuery query);

    @Select("<script>SELECT " + COLUMNS + PUBLIC_FROM + PUBLIC_WHERE + """
             <choose>
                 <when test="query.sort.name() == 'PRICE_ASC'">ORDER BY p.price ASC, p.id ASC</when>
                 <when test="query.sort.name() == 'PRICE_DESC'">ORDER BY p.price DESC, p.id ASC</when>
                 <when test="query.sort.name() == 'NEWEST'">ORDER BY p.created_at DESC, p.id DESC</when>
                 <otherwise>ORDER BY p.sort_order ASC, p.id ASC</otherwise>
             </choose>
             LIMIT #{query.size} OFFSET #{offset}
             </script>
            """)
    List<Product> selectPublic(@Param("query") CatalogQuery query, @Param("offset") long offset);

    @Select("SELECT " + COLUMNS + PUBLIC_FROM + """
             WHERE p.status = 'ON_SALE'
             ORDER BY p.created_at DESC, p.id DESC LIMIT 3
            """)
    List<Product> selectNewest();

    @Select("SELECT " + COLUMNS + PUBLIC_FROM + """
             WHERE p.status = 'ON_SALE'
             ORDER BY p.sort_order ASC, p.id ASC LIMIT 4
            """)
    List<Product> selectFeatured();

    @Select("SELECT " + COLUMNS + PUBLIC_FROM + """
             WHERE p.id = #{productId} AND p.status = 'ON_SALE'
            """)
    Product selectPublicById(@Param("productId") long productId);
}
