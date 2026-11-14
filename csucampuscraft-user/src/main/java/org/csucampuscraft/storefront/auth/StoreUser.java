package org.csucampuscraft.storefront.auth;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import java.time.LocalDateTime;

/** Private persistence object; never add it to a model, session, or log. */
@TableName("store_user")
public final class StoreUser {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String username;
    @TableField(select = false)
    private String passwordHash;
    private String displayName;
    private String role;
    private String status;
    private LocalDateTime updatedAt;

    public Long getId() { return id; }
    public String getUsername() { return username; }
    public String getPasswordHash() { return passwordHash; }
    public String getDisplayName() { return displayName; }
    public String getRole() { return role; }
    public String getStatus() { return status; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}

