// static/admin_dashboard/js/products.js

document.addEventListener('DOMContentLoaded', function () {
    initializeProductManagement();
    setupProductSlugGeneration();  //for auto-slug generation
    setupCharacterLimits(); //for setting chara limit
    setupTextTruncation(); //for name truncation
});

function initializeProductManagement() {
    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', filterProducts);
    }

    const categoryFilter = document.getElementById('categoryFilter');
    const statusFilter = document.getElementById('statusFilter');

    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterProducts);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', filterProducts);
    }
}

function filterProducts() {
    const searchTerm = document.getElementById('productSearch')?.value.toLowerCase() || '';
    const categoryFilter = document.getElementById('categoryFilter')?.value || '';
    const statusFilter = document.getElementById('statusFilter')?.value || '';

    const cards = document.querySelectorAll('.product-card');

    cards.forEach(card => {
        const name = card.querySelector('.product-body h3')?.textContent.toLowerCase() || '';
        const category = card.querySelector('.product-category')?.textContent.toLowerCase() || '';
        const isInactive = card.querySelector('.inactive-badge') !== null;

        const matchesSearch = name.includes(searchTerm) || category.includes(searchTerm);
        let matchesStatus = true;

        if (statusFilter === 'active') {
            matchesStatus = !isInactive;
        } else if (statusFilter === 'inactive') {
            matchesStatus = isInactive;
        }

        if (matchesSearch && matchesStatus) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// for auto-slug generation - always active version
function setupProductSlugGeneration() {
    const nameInput = document.querySelector('input[name="name"]');
    const slugInput = document.querySelector('input[name="slug"]');
    
    if (nameInput && slugInput) {
        // Store original slug value on page load
        const originalSlug = slugInput.value;
        
        nameInput.addEventListener('input', function() {
            // Only auto-generate if slug hasn't been manually changed
            if (!slugInput.dataset.manuallyEdited) {
                const slug = this.value
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/^-+|-+$/g, '');
                slugInput.value = slug;
            }
        });
        
        // Track manual edits
        slugInput.addEventListener('focus', function() {
            this.dataset.originalValue = this.value;
        });
        
        slugInput.addEventListener('blur', function() {
            // If user changed the slug manually, mark it
            if (this.value !== this.dataset.originalValue) {
                this.dataset.manuallyEdited = 'true';
            }
        });
        
        // If slug is empty, remove the manual edit flag
        slugInput.addEventListener('input', function() {
            if (this.value === '') {
                delete this.dataset.manuallyEdited;
            }
        });
    }
}

//for setting char limit
function setupCharacterLimits() {
    // Define field limits
    const fieldLimits = {
        'name': { max: 70, label: 'Product Name' },
        'slug': { max: 75, label: 'Slug' },
        'brand': { max: 60, label: 'Brand' },
        'sku': { max: 50, label: 'SKU' },
        'short_description': { max: 300, label: 'Short Description' },
        'meta_title': { max: 60, label: 'Meta Title' },
        'tags': { max: 200, label: 'Tags' }
    };

    // Apply to each field
    Object.keys(fieldLimits).forEach(fieldName => {
        const input = document.querySelector(`input[name="${fieldName}"], textarea[name="${fieldName}"]`);
        
        if (input) {
            const config = fieldLimits[fieldName];
            
            // Set maxlength attribute
            input.setAttribute('maxlength', config.max);
            
            // Create character counter - MOVED BEFORE USING IT
            const counterDiv = document.createElement('div');
            counterDiv.className = 'character-counter';
            counterDiv.innerHTML = `<span class="char-count">0</span> / ${config.max}`;
            
            // Insert counter after input
            input.parentNode.insertBefore(counterDiv, input.nextSibling);
            
            // Update counter on input
            input.addEventListener('input', function() {
                const length = this.value.length;
                const counter = this.parentNode.querySelector('.char-count');
                
                if (counter) {
                    counter.textContent = length;
                    
                    // Color coding
                    if (length >= config.max * 0.9) {
                        counterDiv.classList.add('warning');
                    } else {
                        counterDiv.classList.remove('warning');
                    }
                    
                    if (length >= config.max) {
                        counterDiv.classList.add('danger');
                    } else {
                        counterDiv.classList.remove('danger');
                    }
                }
            });
            
            // Trigger initial count
            input.dispatchEvent(new Event('input'));
        }
    });
}

// for name truncation

function setupTextTruncation() {
    const truncateElements = document.querySelectorAll('.truncate-with-tooltip');
    
    truncateElements.forEach(element => {
        const maxLength = parseInt(element.dataset.maxLength) || 50;
        const originalText = element.textContent;
        
        if (originalText.length > maxLength) {
            element.textContent = originalText.substring(0, maxLength) + '...';
            element.title = originalText; 
            element.style.cursor = 'help';
        }
    });
}