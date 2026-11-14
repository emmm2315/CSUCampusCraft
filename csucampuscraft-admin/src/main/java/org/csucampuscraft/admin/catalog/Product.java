package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.annotation.*;

@TableName("product")
public class Product {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String sku;
    private Long categoryId;
    private String name;
    private String summary;
    private String description;
    private String coverImage;
    private java.math.BigDecimal price;
    private Integer stock;
    private String status;
    private Integer sortOrder;
    private Long version;
    private java.time.LocalDateTime createdAt;
    private java.time.LocalDateTime updatedAt;
    @TableField(exist = false)
    private String categoryName;
    public Long getId() { return id; }
    public void setId(Long value) { this.id = value; }
    public String getSku() { return sku; }
    public void setSku(String value) { this.sku = value; }
    public Long getCategoryId() { return categoryId; }
    public void setCategoryId(Long value) { this.categoryId = value; }
    public String getName() { return name; }
    public void setName(String value) { this.name = value; }
    public String getSummary() { return summary; }
    public void setSummary(String value) { this.summary = value; }
    public String getDescription() { return description; }
    public void setDescription(String value) { this.description = value; }
    public String getCoverImage() { return coverImage; }
    public void setCoverImage(String value) { this.coverImage = value; }
    public java.math.BigDecimal getPrice() { return price; }
    public void setPrice(java.math.BigDecimal value) { this.price = value; }
    public Integer getStock() { return stock; }
    public void setStock(Integer value) { this.stock = value; }
    public String getStatus() { return status; }
    public void setStatus(String value) { this.status = value; }
    public Integer getSortOrder() { return sortOrder; }
    public void setSortOrder(Integer value) { this.sortOrder = value; }
    public Long getVersion() { return version; }
    public void setVersion(Long value) { this.version = value; }
    public java.time.LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(java.time.LocalDateTime value) { this.createdAt = value; }
    public java.time.LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(java.time.LocalDateTime value) { this.updatedAt = value; }
    public String getCategoryName() { return categoryName; }
    public void setCategoryName(String value) { this.categoryName = value; }
}
