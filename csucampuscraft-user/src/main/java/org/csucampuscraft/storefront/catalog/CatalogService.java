package org.csucampuscraft.storefront.catalog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Public catalog reads only; this service never reserves, deducts, or writes inventory. */
@Service
@Transactional(readOnly = true)
public class CatalogService {
    private final CategoryService categories;
    private final CategoryMapper categoryMapper;
    private final ProductMapper products;
    private final ProductImageMapper images;

    public CatalogService(CategoryService categories, CategoryMapper categoryMapper,
                          ProductMapper products, ProductImageMapper images) {
        this.categories = categories;
        this.categoryMapper = categoryMapper;
        this.products = products;
        this.images = images;
    }

    public HomeCatalog home() {
        List<Category> themes = categories.listTopLevelThemes();
        return new HomeCatalog(themes, navigation(themes),
                categoryMapper.selectRootByCode("GRADUATION"),
                products.selectNewest(), products.selectFeatured());
    }

    public CatalogPage products(CatalogQuery query) {
        Category selected = query.categoryId() == null ? null : requireTheme(query.categoryId());
        List<Category> themes = categories.listTopLevelThemes();
        long total = products.countPublic(query);
        long totalPages = total == 0 ? 0 : 1 + (total - 1) / query.size();
        boolean inRange = query.page() <= totalPages;
        // Do not multiply an unbounded requested page into OFFSET for an empty/out-of-range page.
        List<Product> rows = !inRange ? List.of()
                : products.selectPublic(query, Math.multiplyExact(query.page() - 1, (long) query.size()));
        boolean hasPrevious = query.page() > 1;
        boolean hasNext = inRange && query.page() < totalPages;
        long previous = !inRange ? Math.max(1, totalPages) : Math.max(1, query.page() - 1);
        long next = hasNext ? query.page() + 1 : query.page();
        return new CatalogPage(query, selected, rows, total, totalPages, hasPrevious, hasNext,
                previous, next, themes, navigation(themes));
    }

    public ProductDetail detail(long productId) {
        if (productId <= 0) throw notFound("PRODUCT_NOT_FOUND", "未找到可浏览的商品。");
        Product product = products.selectPublicById(productId);
        if (product == null) throw notFound("PRODUCT_NOT_FOUND", "未找到可浏览的商品。");
        Category category = categoryMapper.selectById(product.getCategoryId());
        Category theme = category == null || category.getParentId() == null
                ? null : categoryMapper.selectById(category.getParentId());
        if (theme == null || theme.getParentId() != null) {
            throw notFound("PRODUCT_NOT_FOUND", "未找到可浏览的商品。");
        }
        return new ProductDetail(product, theme, category, images.selectForProduct(productId));
    }

    private Category requireTheme(long categoryId) {
        if (categoryId <= 0) throw notFound("THEME_NOT_FOUND", "未找到请求的校园主题。");
        Category theme = categoryMapper.selectById(categoryId);
        if (theme == null || theme.getParentId() != null) {
            throw notFound("THEME_NOT_FOUND", "未找到请求的校园主题。");
        }
        return theme;
    }

    private List<ThemeNavigation> navigation(List<Category> themes) {
        Map<Long, List<TypeLink>> links = new LinkedHashMap<>();
        for (Category theme : themes) links.put(theme.getId(), new ArrayList<>());
        for (Category child : categoryMapper.selectChildren()) {
            ProductType type = ProductType.fromCategoryCode(child.getCode());
            List<TypeLink> children = links.get(child.getParentId());
            if (type != null && children != null) {
                children.add(new TypeLink(type.name(), child.getName(), child.getCode()));
            }
        }
        List<ThemeNavigation> result = new ArrayList<>();
        for (Category theme : themes) {
            result.add(new ThemeNavigation(theme, List.copyOf(links.get(theme.getId()))));
        }
        return List.copyOf(result);
    }

    private BusinessException notFound(String code, String message) {
        return new BusinessException(HttpStatus.NOT_FOUND, code, message);
    }
}
