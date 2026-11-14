package org.csucampuscraft.admin.web;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.csucampuscraft.admin.catalog.ProductQuery;

/** Business return context only. A fixed list path plus validated filters is never an arbitrary redirect. */
public final class ProductReturnUrls {
    private static final Set<String> KEYS = Set.of("categoryId", "q", "status", "page", "size");
    private ProductReturnUrls() { }

    public static String resolve(String raw) {
        String fallback = "/products";
        if (raw == null || raw.isBlank()) return fallback;
        try {
            URI uri = new URI(raw);
            if (uri.isAbsolute() || uri.getRawAuthority() != null || uri.getRawFragment() != null
                    || !"/products".equals(uri.getRawPath())) return fallback;
            Map<String, String> parameters = new HashMap<>();
            String query = uri.getRawQuery();
            if (query != null && !query.isEmpty()) {
                for (String part : query.split("&", -1)) {
                    String[] pair = part.split("=", 2);
                    String key = URLDecoder.decode(pair[0], StandardCharsets.UTF_8);
                    String value = pair.length == 1 ? "" : URLDecoder.decode(pair[1], StandardCharsets.UTF_8);
                    if (!KEYS.contains(key) || parameters.putIfAbsent(key, value) != null) return fallback;
                }
            }
            ProductQuery bound = ProductQuery.bind(parameters.get("categoryId"), parameters.get("q"),
                    parameters.get("status"), parameters.get("page"), parameters.get("size"));
            return bound.path(bound.page());
        } catch (Exception invalid) {
            return fallback;
        }
    }
}
