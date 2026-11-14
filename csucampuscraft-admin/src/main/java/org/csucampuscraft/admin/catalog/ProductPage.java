package org.csucampuscraft.admin.catalog;

import java.util.List;

public record ProductPage(ProductQuery query, List<Product> products, long total, long totalPages,
                          long previousPage, long nextPage, boolean hasPrevious, boolean hasNext) { }
