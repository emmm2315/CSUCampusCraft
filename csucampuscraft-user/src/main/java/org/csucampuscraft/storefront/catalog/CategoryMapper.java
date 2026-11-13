package org.csucampuscraft.storefront.catalog;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface CategoryMapper extends BaseMapper<Category> {
    @Select("""
            SELECT id, code, parent_id, name, sort_order
            FROM category WHERE parent_id IS NOT NULL
            ORDER BY sort_order ASC, id ASC
            """)
    List<Category> selectChildren();

    @Select("""
            SELECT id, code, parent_id, name, sort_order
            FROM category WHERE parent_id IS NULL AND code = #{code}
            LIMIT 1
            """)
    Category selectRootByCode(@Param("code") String code);
}
