package org.csucampuscraft.storefront.order;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/** Existing sales_order projection. Receiver data must never enter diagnostic text. */
@TableName("sales_order")
public final class SalesOrder {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String orderNo;
    private Long userId;
    private String status;
    private java.math.BigDecimal totalAmount;
    private String receiverName;
    private String receiverPhone;
    private String receiverAddress;
    private java.time.LocalDateTime createdAt;
    private java.time.LocalDateTime updatedAt;
    private String paymentMethod;
    private String paymentNo;
    private java.time.LocalDateTime paidAt;
    private java.time.LocalDateTime cancelledAt;
    private java.time.LocalDateTime shippedAt;
    private java.time.LocalDateTime completedAt;

    public Long getId() { return id; }
    public void setId(Long value) { id = value; }
    public String getOrderNo() { return orderNo; }
    public void setOrderNo(String value) { orderNo = value; }
    public Long getUserId() { return userId; }
    public void setUserId(Long value) { userId = value; }
    public String getStatus() { return status; }
    public void setStatus(String value) { status = value; }
    public java.math.BigDecimal getTotalAmount() { return totalAmount; }
    public void setTotalAmount(java.math.BigDecimal value) { totalAmount = value; }
    public String getReceiverName() { return receiverName; }
    public void setReceiverName(String value) { receiverName = value; }
    public String getReceiverPhone() { return receiverPhone; }
    public void setReceiverPhone(String value) { receiverPhone = value; }
    public String getReceiverAddress() { return receiverAddress; }
    public void setReceiverAddress(String value) { receiverAddress = value; }
    public java.time.LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(java.time.LocalDateTime value) { createdAt = value; }
    public java.time.LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(java.time.LocalDateTime value) { updatedAt = value; }
    public String getPaymentMethod() { return paymentMethod; }
    public void setPaymentMethod(String value) { paymentMethod = value; }
    public String getPaymentNo() { return paymentNo; }
    public void setPaymentNo(String value) { paymentNo = value; }
    public java.time.LocalDateTime getPaidAt() { return paidAt; }
    public void setPaidAt(java.time.LocalDateTime value) { paidAt = value; }
    public java.time.LocalDateTime getCancelledAt() { return cancelledAt; }
    public void setCancelledAt(java.time.LocalDateTime value) { cancelledAt = value; }
    public java.time.LocalDateTime getShippedAt() { return shippedAt; }
    public void setShippedAt(java.time.LocalDateTime value) { shippedAt = value; }
    public java.time.LocalDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(java.time.LocalDateTime value) { completedAt = value; }

    public String getStatusLabel() { return OrderStatus.valueOf(status).getLabel(); }
    public String getCreatedAtDisplay() { return display(createdAt); }
    public String getUpdatedAtDisplay() { return display(updatedAt); }
    public String getPaidAtDisplay() { return display(paidAt); }
    public String getCancelledAtDisplay() { return display(cancelledAt); }
    public String getShippedAtDisplay() { return display(shippedAt); }
    public String getCompletedAtDisplay() { return display(completedAt); }
    private static String display(java.time.LocalDateTime value) {
        return value == null ? null : value.atOffset(ZoneOffset.UTC)
                .atZoneSameInstant(ZoneId.of("Asia/Shanghai"))
                .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
    }
    @Override public String toString() { return "SalesOrder[receiver=REDACTED]"; }
}
