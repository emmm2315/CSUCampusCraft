package org.csucampuscraft.storefront.catalog;

public record TypeLink(String type, String label, String code) {
    public String getType() { return type; }
    public String getLabel() { return label; }
    public String getCode() { return code; }
}
