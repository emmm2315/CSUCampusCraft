package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class CategoryService {
    private final CategoryMapper categoryMapper;

    public CategoryService(CategoryMapper categoryMapper) {
        this.categoryMapper = categoryMapper;
    }

    public List<Category> listTopLevelThemes() {
        return categoryMapper.selectList(Wrappers.lambdaQuery(Category.class)
                .select(Category::getId, Category::getCode, Category::getName)
                .isNull(Category::getParentId)
                .orderByAsc(Category::getSortOrder, Category::getId));
    }
}
