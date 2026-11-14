package org.csucampuscraft.admin.catalog;

public record ProductCategoryChoice(Long id, String label, boolean secondLevel) {
    public Long getId() { return id; }
    public String getLabel() { return label; }
    public boolean isSecondLevel() { return secondLevel; }
}
