package org.csucampuscraft.admin.catalog;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.util.MultiValueMap;

/** Only these named fields are read; this is never bound into the database entity. */
public record CategoryForm(String code, String parentId, String type, String name, String sortOrder) {
    public static CategoryForm empty() { return new CategoryForm("", "", "STATIONERY", "", "0"); }

    public static CategoryForm edit(Category category) {
        return new CategoryForm(category.getCode(), category.getParentId() == null ? ""
                : category.getParentId().toString(), "", category.getName(), category.getSortOrder().toString());
    }

    public static CategoryForm bind(MultiValueMap<String, String> parameters, boolean editing) {
        Map<String, String> errors = new LinkedHashMap<>();
        String code = editing ? "" : single(parameters, "code", errors);
        String parent = editing ? "" : single(parameters, "parentId", errors);
        String type = editing ? "" : single(parameters, "type", errors);
        String name = single(parameters, "name", errors);
        String sort = single(parameters, "sortOrder", errors);
        if (!errors.isEmpty()) throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_FIELDS",
                "请为每个字段只提交一个值。", errors);
        return new CategoryForm(code, parent, type, name, sort);
    }

    public static CategoryForm display(MultiValueMap<String, String> parameters) {
        return new CategoryForm(display(parameters, "code"), display(parameters, "parentId"),
                display(parameters, "type"), display(parameters, "name"), display(parameters, "sortOrder"));
    }

    private static String single(MultiValueMap<String, String> values, String name,
                                 Map<String, String> errors) {
        List<String> items = values.get(name);
        if (items == null) return "";
        if (items.size() != 1) {
            errors.put(name, "每个字段只能提交一个值。");
            return "";
        }
        return items.get(0);
    }

    private static String display(MultiValueMap<String, String> values, String name) {
        List<String> items = values.get(name);
        return items != null && items.size() == 1 && items.get(0) != null ? items.get(0) : "";
    }

    public String getCode() { return code; }
    public String getParentId() { return parentId; }
    public String getType() { return type; }
    public String getName() { return name; }
    public String getSortOrder() { return sortOrder; }
}
