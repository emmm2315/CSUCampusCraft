package org.csucampuscraft.storefront.catalog;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

@TableName("category")
public class Category {
    @TableId
    private Long id;
    private String code;
    private Long parentId;
    private String name;
    private Integer sortOrder;

    public Long getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public Long getParentId() {
        return parentId;
    }

    public String getName() {
        return name;
    }

    public Integer getSortOrder() {
        return sortOrder;
    }
}
