package org.csucampuscraft.admin.auth;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface StoreUserMapper extends BaseMapper<StoreUser> {
    @Select("""
            SELECT id, username, password_hash, display_name, role, status, updated_at
            FROM store_user WHERE username = #{username}
            """)
    StoreUser selectForLoginByUsername(@Param("username") String username);
}
