package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

@TableName("category")
public class Category {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String code;
    private Long parentId;
    private String name;
    private Integer sortOrder;

    public Category() { }

    public Category(String code, Long parentId, String name, int sortOrder) {
        this.code = code;
        this.parentId = parentId;
        this.name = name;
        this.sortOrder = sortOrder;
    }

    public Long getId() { return id; }
    public String getCode() { return code; }
    public Long getParentId() { return parentId; }
    public String getName() { return name; }
    public Integer getSortOrder() { return sortOrder; }
}
