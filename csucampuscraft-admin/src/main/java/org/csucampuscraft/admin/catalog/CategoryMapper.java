package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

@Mapper
public interface CategoryMapper extends BaseMapper<Category> {
    String COLUMNS = "id, code, parent_id, name, sort_order";

    @Select("""
            SELECT c.id, c.code, c.parent_id, c.name, c.sort_order
            FROM category c LEFT JOIN category p ON p.id = c.parent_id
            ORDER BY COALESCE(p.sort_order, c.sort_order), COALESCE(p.id, c.id),
                     (c.parent_id IS NOT NULL), c.sort_order, c.id
            """)
    List<Category> selectHierarchy();

    @Select("SELECT " + COLUMNS + " FROM category WHERE parent_id IS NOT NULL ORDER BY parent_id, sort_order, id")
    List<Category> selectSecondLevel();

    @Select("SELECT " + COLUMNS + " FROM category WHERE id = #{id} FOR UPDATE")
    Category lockById(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM category WHERE code = #{code}")
    long countCode(@Param("code") String code);

    @Select("""
            SELECT COUNT(*) FROM category
            WHERE parent_key = #{parentKey} AND name = #{name} AND id != #{excludedId}
            """)
    long countSiblingName(@Param("parentKey") long parentKey, @Param("name") String name,
                          @Param("excludedId") long excludedId);

    @Select("""
            SELECT COUNT(*) FROM category
            WHERE parent_id = #{parentId} AND RIGHT(code, #{suffixLength}) = #{suffix}
            """)
    long countType(@Param("parentId") long parentId, @Param("suffix") String suffix,
                   @Param("suffixLength") int suffixLength);

    @Select("SELECT COUNT(*) FROM category WHERE parent_id = #{id}")
    long countChildren(@Param("id") long id);

    @Select("SELECT COUNT(*) FROM product WHERE category_id = #{id}")
    long countProductReferences(@Param("id") long id);

    @Update("UPDATE category SET name = #{name}, sort_order = #{sortOrder} WHERE id = #{id}")
    int updateDetails(@Param("id") long id, @Param("name") String name, @Param("sortOrder") int sortOrder);
}
