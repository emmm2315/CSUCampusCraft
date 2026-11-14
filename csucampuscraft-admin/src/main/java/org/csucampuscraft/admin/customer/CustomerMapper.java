package org.csucampuscraft.admin.customer;

import java.time.LocalDateTime;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

/** All projections explicitly omit password_hash; no BaseMapper select-* entry point. */
@Mapper
public interface CustomerMapper {
    String COLUMNS = "id,username,display_name,status,email,phone,created_at,updated_at";
    String FILTER = "<where>role='CUSTOMER'"
            + "<if test='query.q.length() > 0'> AND username LIKE #{query.likePattern} ESCAPE '!'</if>"
            + "<if test='query.status != \"ALL\"'> AND status=#{query.status}</if></where>";

    @Select("<script>SELECT COUNT(*) FROM store_user " + FILTER + "</script>")
    long count(@Param("query") CustomerQuery query);

    @Select("<script>SELECT " + COLUMNS + " FROM store_user " + FILTER
            + " ORDER BY id ASC LIMIT #{query.size} OFFSET #{query.offset}</script>")
    List<CustomerProfile> selectPage(@Param("query") CustomerQuery query);

    @Select("SELECT " + COLUMNS + " FROM store_user WHERE id=#{userId} AND role='CUSTOMER'")
    CustomerProfile selectCustomer(@Param("userId") long userId);

    @Select("SELECT id,role,status,updated_at FROM store_user WHERE id=#{userId} FOR UPDATE")
    CustomerTarget selectTargetForUpdate(@Param("userId") long userId);

    @Update("""
            UPDATE store_user
               SET status=#{targetStatus},updated_at=GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)
             WHERE id=#{userId} AND role='CUSTOMER' AND status=#{previousStatus} AND updated_at=#{previousStamp}
            """)
    int changeStatus(@Param("userId") long userId, @Param("targetStatus") String targetStatus,
                     @Param("previousStatus") String previousStatus, @Param("previousStamp") LocalDateTime previousStamp);
}
