package org.csucampuscraft.storefront.order;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/** Transaction-time values; order views do not join the mutable catalog. */
@TableName("sales_order_item")
public final class SalesOrderItem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long orderId;
    private Long productId;
    private String skuSnapshot;
    private String productNameSnapshot;
    private String coverImageSnapshot;
    private java.math.BigDecimal unitPrice;
    private Integer quantity;
    private java.math.BigDecimal lineAmount;

    public Long getId() { return id; }
    public void setId(Long value) { id = value; }
    public Long getOrderId() { return orderId; }
    public void setOrderId(Long value) { orderId = value; }
    public Long getProductId() { return productId; }
    public void setProductId(Long value) { productId = value; }
    public String getSkuSnapshot() { return skuSnapshot; }
    public void setSkuSnapshot(String value) { skuSnapshot = value; }
    public String getProductNameSnapshot() { return productNameSnapshot; }
    public void setProductNameSnapshot(String value) { productNameSnapshot = value; }
    public String getCoverImageSnapshot() { return coverImageSnapshot; }
    public void setCoverImageSnapshot(String value) { coverImageSnapshot = value; }
    public java.math.BigDecimal getUnitPrice() { return unitPrice; }
    public void setUnitPrice(java.math.BigDecimal value) { unitPrice = value; }
    public Integer getQuantity() { return quantity; }
    public void setQuantity(Integer value) { quantity = value; }
    public java.math.BigDecimal getLineAmount() { return lineAmount; }
    public void setLineAmount(java.math.BigDecimal value) { lineAmount = value; }
}
