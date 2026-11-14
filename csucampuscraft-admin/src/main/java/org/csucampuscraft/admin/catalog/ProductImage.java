package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/** Album metadata only. The independent product cover is never written here. */
@TableName("product_image")
public class ProductImage {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long productId;
    private String imagePath;
    private String altText;
    private Integer sortOrder;

    public Long getId() { return id; }
    public void setId(Long value) { this.id = value; }
    public Long getProductId() { return productId; }
    public void setProductId(Long value) { this.productId = value; }
    public String getImagePath() { return imagePath; }
    public void setImagePath(String value) { this.imagePath = value; }
    public String getAltText() { return altText; }
    public void setAltText(String value) { this.altText = value; }
    public Integer getSortOrder() { return sortOrder; }
    public void setSortOrder(Integer value) { this.sortOrder = value; }
}
