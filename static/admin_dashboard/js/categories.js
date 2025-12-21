// static/admin_dashboard/js/categories.js

document.addEventListener('DOMContentLoaded', function() {
    initializeCategoryManagement();
});

function initializeCategoryManagement() {
    // Search functionality
    const searchInput = document.getElementById('categorySearch');
    if (searchInput) {
        searchInput.addEventListener('input', filterCategories);
    }

    // Filter functionality
    const statusFilter = document.getElementById('statusFilter');
    const sortBy = document.getElementById('sortBy');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', filterCategories);
    }
    
    if (sortBy) {
        sortBy.addEventListener('change', sortCategories);
    }

    // Delete buttons
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', handleDeleteClick);
    });

    // Close modal on overlay click
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeDeleteModal();
            }
        });
    }
}

// Filter categories based on search and status
function filterCategories() {
    const searchTerm = document.getElementById('categorySearch')?.value.toLowerCase() || '';
    const statusFilter = document.getElementById('statusFilter')?.value || '';
    
    const rows = document.querySelectorAll('.data-table tbody tr[data-category-id]');
    
    rows.forEach(row => {
        const categoryName = row.querySelector('.category-name strong')?.textContent.toLowerCase() || '';
        const categoryDesc = row.querySelector('.category-info small')?.textContent.toLowerCase() || '';
        const status = row.querySelector('.status-badge')?.classList.contains('status-active') ? 'active' : 'inactive';
        
        const matchesSearch = categoryName.includes(searchTerm) || categoryDesc.includes(searchTerm);
        const matchesStatus = !statusFilter || status === statusFilter;
        
        if (matchesSearch && matchesStatus) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Sort categories
function sortCategories() {
    const sortBy = document.getElementById('sortBy')?.value;
    if (!sortBy) return;
    
    const tbody = document.querySelector('.data-table tbody');
    const rows = Array.from(tbody.querySelectorAll('tr[data-category-id]'));
    
    rows.sort((a, b) => {
        let aValue, bValue;
        
        switch(sortBy) {
            case 'name':
                aValue = a.querySelector('.category-name strong')?.textContent || '';
                bValue = b.querySelector('.category-name strong')?.textContent || '';
                return aValue.localeCompare(bValue);
                
            case '-name':
                aValue = a.querySelector('.category-name strong')?.textContent || '';
                bValue = b.querySelector('.category-name strong')?.textContent || '';
                return bValue.localeCompare(aValue);
                
            case '-product_count':
                aValue = parseInt(a.querySelector('.product-count')?.textContent.match(/\d+/)?.[0] || 0);
                bValue = parseInt(b.querySelector('.product-count')?.textContent.match(/\d+/)?.[0] || 0);
                return bValue - aValue;
                
            case 'sort_order':
            default:
                aValue = parseInt(a.querySelector('.sort-order-badge')?.textContent || 0);
                bValue = parseInt(b.querySelector('.sort-order-badge')?.textContent || 0);
                return aValue - bValue;
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// Handle delete button click
function handleDeleteClick(e) {
    const button = e.currentTarget;
    const categoryId = button.dataset.categoryId;
    const categoryName = button.dataset.categoryName;
    
    showDeleteModal(categoryId, categoryName);
}

// Show delete confirmation modal
function showDeleteModal(categoryId, categoryName) {
    const modal = document.getElementById('deleteModal');
    const nameElement = document.getElementById('categoryNameToDelete');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    
    if (modal && nameElement && confirmBtn) {
        nameElement.textContent = categoryName;
        modal.classList.add('active');
        
        // Remove old event listeners
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
        
        // Add new event listener
        newConfirmBtn.addEventListener('click', () => deleteCategory(categoryId));
    }
}

// Close delete modal
function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Delete category
async function deleteCategory(categoryId) {
    try {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        const response = await fetch(`/admin-dashboard/categories/${categoryId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });
        
        if (response.ok) {
            // Remove the row from table
            const row = document.querySelector(`tr[data-category-id="${categoryId}"]`);
            if (row) {
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 300);
            }
            
            closeDeleteModal();
            showNotification('Category deleted successfully', 'success');
        } else {
            throw new Error('Failed to delete category');
        }
    } catch (error) {
        console.error('Error deleting category:', error);
        showNotification('Failed to delete category', 'error');
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
        ${message}
        <button class="alert-close">&times;</button>
    `;
    
    // Insert into messages container or create one
    let container = document.querySelector('.messages-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'messages-container';
        const content = document.querySelector('.admin-content');
        if (content) {
            content.insertBefore(container, content.firstChild);
        }
    }
    
    container.appendChild(notification);
    
    // Add close button functionality
    const closeBtn = notification.querySelector('.alert-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        });
    }
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Auto-generate slug from name (for form page)
function setupSlugGeneration() {
    const nameInput = document.querySelector('input[name="name"]');
    const slugInput = document.querySelector('input[name="slug"]');
    
    if (nameInput && slugInput) {
        nameInput.addEventListener('input', function() {
            if (!slugInput.dataset.manuallyEdited) {
                const slug = this.value
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/^-+|-+$/g, '');
                slugInput.value = slug;
            }
        });
        
        slugInput.addEventListener('input', function() {
            this.dataset.manuallyEdited = 'true';
        });
    }
}

// Initialize slug generation if on form page
if (document.getElementById('categoryForm')) {
    setupSlugGeneration();
}

// Form validation
const categoryForm = document.getElementById('categoryForm');
if (categoryForm) {
    categoryForm.addEventListener('submit', function(e) {
        const nameInput = this.querySelector('input[name="name"]');
        const slugInput = this.querySelector('input[name="slug"]');
        
        if (!nameInput.value.trim()) {
            e.preventDefault();
            showNotification('Category name is required', 'error');
            nameInput.focus();
            return false;
        }
        
        if (!slugInput.value.trim()) {
            e.preventDefault();
            showNotification('Slug is required', 'error');
            slugInput.focus();
            return false;
        }
    });
}
