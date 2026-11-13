package org.csucampuscraft.storefront.catalog;

/** SQL order clauses are fixed in ProductMapper; this enum carries no request SQL. */
public enum ProductSort {
    DEFAULT("默认"), PRICE_ASC("价格从低到高"), PRICE_DESC("价格从高到低"), NEWEST("最新商品");

    private final String label;
    ProductSort(String label) { this.label = label; }
    public String getLabel() { return label; }
}
