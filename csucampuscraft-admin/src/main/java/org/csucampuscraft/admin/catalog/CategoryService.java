package org.csucampuscraft.admin.catalog;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.csucampuscraft.admin.auth.AdminWriteGuard;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CategoryService {
    private final CategoryMapper categories;
    private final AdminWriteGuard writeGuard;

    public CategoryService(CategoryMapper categories, AdminWriteGuard writeGuard) {
        this.categories = categories;
        this.writeGuard = writeGuard;
    }

    @Transactional(readOnly = true)
    public List<Category> listTopLevelThemes() {
        return categories.selectList(Wrappers.lambdaQuery(Category.class)
                .select(Category::getId, Category::getCode, Category::getName)
                .isNull(Category::getParentId).orderByAsc(Category::getSortOrder, Category::getId));
    }

    @Transactional(readOnly = true)
    public List<Category> listAll() { return categories.selectHierarchy(); }

    @Transactional(readOnly = true)
    public List<Category> listSecondLevel() { return categories.selectSecondLevel(); }

    @Transactional(readOnly = true)
    public Category getRequired(long id) { return require(categories.selectById(id)); }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public Category create(SessionIdentity actor, CategoryForm form) {
        writeGuard.lock(actor);
        String name = InputChecks.requiredText("name", form.name(), 50);
        int sort = sortOrder(form.sortOrder());
        String parentText = form.parentId() == null ? "" : form.parentId().strip();
        Long parentId = null;
        String code;
        if (parentText.isEmpty()) {
            code = InputChecks.requiredText("code", form.code(), 21);
        } else {
            parentId = InputChecks.longInteger("parentId", parentText, 1, Long.MAX_VALUE);
            ChildType type = InputChecks.enumeration("type", form.type(), ChildType.class);
            Category parent = require(categories.lockById(parentId));
            if (parent.getParentId() != null) {
                throw conflict("CATEGORY_PARENT_LEVEL", "二级分类只能选择一级主题作为父级。", "parentId");
            }
            String suffix = "_" + type.name();
            if (categories.countType(parentId, suffix, suffix.length()) != 0) {
                throw conflict("CATEGORY_TYPE_EXISTS", "该主题下已经有此类型的分类。", "type");
            }
            code = InputChecks.requiredText("code", parent.getCode() + suffix, 32);
        }
        if (categories.countCode(code) != 0) {
            throw conflict("CATEGORY_CODE_EXISTS", "分类编码已占用，请修改编码或类型。", parentId == null ? "code" : "type");
        }
        ensureUniqueName(parentId, name, 0);
        Category created = new Category(code, parentId, name, sort);
        try {
            if (categories.insert(created) != 1 || created.getId() == null || created.getId() <= 0) {
                throw new IllegalStateException("Category generated ID was not returned");
            }
            Category inserted = categories.selectById(created.getId());
            if (inserted == null || !Objects.equals(created.getId(), inserted.getId())
                    || !code.equals(inserted.getCode()) || !Objects.equals(parentId, inserted.getParentId())
                    || !name.equals(inserted.getName()) || sort != inserted.getSortOrder()) {
                throw new IllegalStateException("Generated category ID verification failed");
            }
            return inserted;
        } catch (DataIntegrityViolationException failure) {
            throw conflict("CATEGORY_CONFLICT", "分类编码、名称或关联数据已变化，请刷新后重试。", null);
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void update(SessionIdentity actor, long id, CategoryForm form) {
        writeGuard.lock(actor);
        Category current = require(categories.lockById(id));
        String name = InputChecks.requiredText("name", form.name(), 50);
        int sort = sortOrder(form.sortOrder());
        ensureUniqueName(current.getParentId(), name, id);
        if (name.equals(current.getName()) && sort == current.getSortOrder()) return;
        try {
            if (categories.updateDetails(id, name, sort) != 1) {
                throw conflict("CATEGORY_CHANGED", "分类已变化，请刷新列表后重试。", null);
            }
        } catch (DataIntegrityViolationException failure) {
            throw conflict("CATEGORY_CONFLICT", "同父级的分类名称已占用，请修改后重试。", "name");
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void remove(SessionIdentity actor, long id) {
        writeGuard.lock(actor);
        require(categories.lockById(id));
        if (categories.countChildren(id) != 0 || categories.countProductReferences(id) != 0) {
            throw conflict("CATEGORY_REFERENCED", "分类含子类或仍被商品引用（包括草稿），请先处理关联数据。", null);
        }
        try {
            if (categories.deleteById(id) != 1) {
                throw conflict("CATEGORY_CHANGED", "分类已变化，请刷新列表后重试。", null);
            }
        } catch (DataIntegrityViolationException failure) {
            throw conflict("CATEGORY_REFERENCED", "分类仍有新的关联引用，暂时无法删除。", null);
        }
    }

    private void ensureUniqueName(Long parentId, String name, long excludedId) {
        if (categories.countSiblingName(parentId == null ? 0 : parentId, name, excludedId) != 0) {
            throw conflict("CATEGORY_NAME_EXISTS", "同父级已存在该分类名称。", "name");
        }
    }

    private int sortOrder(String raw) {
        return raw == null || raw.isBlank() ? 0 : InputChecks.integer("sortOrder", raw, 0, Integer.MAX_VALUE);
    }

    private Category require(Category category) {
        if (category == null) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "CATEGORY_NOT_FOUND", "未找到请求的分类。");
        }
        return category;
    }

    private BusinessException conflict(String code, String message, String field) {
        return new BusinessException(HttpStatus.CONFLICT, code, message,
                field == null ? Map.of() : Map.of(field, message));
    }

    private enum ChildType { STATIONERY, SOUVENIR }
}
