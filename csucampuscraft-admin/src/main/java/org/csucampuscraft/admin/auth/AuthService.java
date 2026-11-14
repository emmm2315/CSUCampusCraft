package org.csucampuscraft.admin.auth;

import java.util.UUID;
import org.csucampuscraft.admin.foundation.security.PasswordService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {
    public static final String REQUIRED_ROLE = "ADMIN";
    private final StoreUserMapper users;
    private final PasswordService passwords;
    private final String dummyHash;

    public AuthService(StoreUserMapper users, PasswordService passwords) {
        this.users = users;
        this.passwords = passwords;
        this.dummyHash = passwords.hash(UUID.randomUUID().toString());
    }

    public StoreUser authenticate(String username, String password) {
        StoreUser user = users.selectForLoginByUsername(username);
        boolean matched = passwords.matches(password, user == null ? dummyHash : user.getPasswordHash());
        return matched && user != null && "ENABLED".equals(user.getStatus())
                && REQUIRED_ROLE.equals(user.getRole()) && user.getUpdatedAt() != null ? user : null;
    }

    /** Role is checked separately so a current authenticated identity with a wrong role is 403. */
    public StoreUser findCurrent(SessionIdentity identity) {
        if (identity == null) return null;
        StoreUser user = users.selectById(identity.userId());
        return user != null && "ENABLED".equals(user.getStatus())
                && identity.authStamp().equals(user.getUpdatedAt()) ? user : null;
    }
}
