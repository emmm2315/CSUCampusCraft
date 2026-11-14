package org.csucampuscraft.storefront.auth;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface StoreUserMapper extends BaseMapper<StoreUser> {
    @Select("""
            SELECT id, username, password_hash AS passwordHash,
                   display_name AS displayName, role, status, updated_at AS updatedAt
              FROM store_user WHERE username = #{username} LIMIT 1
            """)
    StoreUser selectForLoginByUsername(@Param("username") String username);
}

