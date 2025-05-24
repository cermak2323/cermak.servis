document.addEventListener('DOMContentLoaded', function() {
    // Ekipman durum yönetimi
    initEquipmentStatusManager();
    
    // Tooltips'leri etkinleştir
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Animasyonlu bilgi kartları
    animateInfoCards();
    
    // Resim önizleme efektleri
    initImagePreviewEffects();
});

// Bilgi kartlarına animasyon ekle
function animateInfoCards() {
    const infoItems = document.querySelectorAll('.info-item');
    if (infoItems.length === 0) return;
    
    infoItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            item.style.transition = 'all 0.5s ease';
            item.style.opacity = '1';
            item.style.transform = 'translateY(0)';
        }, 100 + (index * 100)); // Sıralı olarak ekrana gelme efekti
    });
}

// Resim önizleme efektleri
function initImagePreviewEffects() {
    const photoLinks = document.querySelectorAll('.photo-link');
    if (photoLinks.length === 0) return;
    
    photoLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            const overlay = this.querySelector('.photo-overlay');
            overlay.style.opacity = '1';
        });
        
        link.addEventListener('mouseleave', function() {
            const overlay = this.querySelector('.photo-overlay');
            overlay.style.opacity = '0';
        });
    });
}

// Ekipman durum yönetimi
function initEquipmentStatusHandlers() {
    // Durum badgelerine tıklama olaylarını ekle
    document.querySelectorAll('.status-badge').forEach(badge => {
        badge.addEventListener('click', function(e) {
            if (e.target.classList.contains('delivery-date-badge')) return;
            
            const container = this.closest('.delivery-status-container');
            const actions = container.querySelector('.status-actions');
            
            // Diğer tüm açık menüleri kapat
            document.querySelectorAll('.status-actions').forEach(menu => {
                if (menu !== actions) {
                    menu.style.opacity = '0';
                    setTimeout(() => { menu.style.display = 'none'; }, 300);
                }
            });
            
            // Bu menüyü aç/kapat
            if (actions) {
                const isVisible = actions.style.display === 'block';
                
                if (isVisible) {
                    actions.style.opacity = '0';
                    setTimeout(() => { actions.style.display = 'none'; }, 300);
                } else {
                    actions.style.display = 'block';
                    actions.style.opacity = '0';
                    setTimeout(() => { actions.style.opacity = '1'; }, 10);
                }
            }
        });
    });
    
    // Durum güncelleme butonları
    document.querySelectorAll('.update-status-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const equipmentId = this.dataset.equipmentId;
            const container = this.closest('.delivery-status-container');
            const statusSelect = container.querySelector('.delivery-status-select');
            const newStatus = statusSelect.value;
            
            // Formları bul
            const prepTimeInput = container.querySelector('.prep-time');
            const deliveryDateInput = container.querySelector('.delivery-date');
            
            // Loading durumunu göster
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Kaydediliyor...';
            
            try {
                // Form verilerini oluştur
                const formData = new FormData();
                formData.append('status', newStatus);
                if (prepTimeInput) formData.append('prep_time', prepTimeInput.value);
                if (deliveryDateInput) formData.append('delivery_date', deliveryDateInput.value);
                
                // API isteği gönder
                const response = await fetch(`/equipment/delivery-status/${equipmentId}`, {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    // UI'ı güncelle
                    updateStatusUI(container, newStatus, deliveryDateInput?.value);
                    showToast('Teslim durumu başarıyla güncellendi', 'success');
                    
                    // Menüyü kapat
                    const actions = container.querySelector('.status-actions');
                    actions.style.opacity = '0';
                    setTimeout(() => { actions.style.display = 'none'; }, 300);
                } else {
                    throw new Error('Güncelleme başarısız');
                }
            } catch (error) {
                console.error('Hata:', error);
                showToast('Durum güncellenirken bir hata oluştu', 'danger');
            } finally {
                // Butonu eski haline getir
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-save me-1"></i> Kaydet';
            }
        });
    });
    
    // Durum seçildiğinde ekstra alanları göster/gizle
    document.querySelectorAll('.delivery-status-select').forEach(select => {
        select.addEventListener('change', function() {
            const container = this.closest('.delivery-status-container');
            const actions = container.querySelector('.status-actions');
            const newStatus = this.value;
            
            // Mevcut ekstra alanları temizle
            const existingExtras = actions.querySelectorAll('.status-extra-field');
            existingExtras.forEach(field => field.remove());
            
            // Yeni duruma göre ekstra alanlar ekle
            if (newStatus === 'Hazırlanıyor') {
                const prepTimeField = document.createElement('div');
                prepTimeField.className = 'form-group status-extra-field';
                prepTimeField.innerHTML = `
                    <input type="number" class="form-control mb-2 prep-time" 
                           placeholder="Hazırlanma Süresi (Saat)" 
                           min="1">
                `;
                actions.insertBefore(prepTimeField, actions.querySelector('.update-status-btn'));
            } else if (newStatus === 'Teslim Edildi') {
                const dateField = document.createElement('div');
                dateField.className = 'form-group status-extra-field';
                dateField.innerHTML = `
                    <input type="datetime-local" class="form-control mb-2 delivery-date">
                `;
                actions.insertBefore(dateField, actions.querySelector('.update-status-btn'));
            }
        });
    });
}

// Durum UI'ını güncelle
function updateStatusUI(container, newStatus, deliveryDate = null) {
    const statusBadge = container.querySelector('.status-badge');
    if (!statusBadge) return;
    
    // Badge'i animasyonla değiştir
    statusBadge.style.opacity = '0';
    setTimeout(() => {
        // Sınıfları temizle
        statusBadge.classList.remove('status-teslim-edilmedi', 'status-hazırlanıyor', 'status-teslim-edildi');
        
        // Yeni sınıfı ekle
        const statusClass = `status-${newStatus.toLowerCase().replace(/\s+/g, '-')}`;
        statusBadge.classList.add(statusClass);
        
        // İçeriği güncelle
        statusBadge.innerHTML = newStatus;
        
        // Teslim edildi durumunda tarih badge'i ekle
        if (newStatus === 'Teslim Edildi') {
            let displayDate;
            
            if (deliveryDate) {
                const date = new Date(deliveryDate);
                displayDate = `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()}`;
            } else {
                const today = new Date();
                displayDate = `${today.getDate().toString().padStart(2, '0')}/${(today.getMonth() + 1).toString().padStart(2, '0')}/${today.getFullYear()}`;
            }
            
            const dateElement = document.createElement('div');
            dateElement.className = 'delivery-date-badge';
            dateElement.textContent = displayDate;
            statusBadge.appendChild(dateElement);
        }
        
        statusBadge.style.opacity = '1';
    }, 300);
}

// Toast bildirimi göster
function showToast(message, type) {
    // Toast container bul ya da oluştur
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Toast oluştur
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast bg-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white`;
    toast.role = 'alert';
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header bg-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white">
            <i class="fas fa-${type === 'danger' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            <strong class="me-auto">${type === 'danger' ? 'Hata' : type === 'success' ? 'Başarılı' : 'Bilgi'}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Bootstrap Toast oluştur
    const bsToast = new bootstrap.Toast(toast, {
        animation: true,
        autohide: true,
        delay: 5000
    });
    
    // Göster
    bsToast.show();
    
    // Gizlendikten sonra DOM'dan kaldır
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}
document.addEventListener('DOMContentLoaded', function() {
    // Equipment Status Management
    initEquipmentStatusManager();
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Enhanced Equipment Status Management
function initEquipmentStatusManager() {
    const deliveryStatusContainers = document.querySelectorAll('.delivery-status-container');
    
    deliveryStatusContainers.forEach(container => {
        const statusBadge = container.querySelector('.status-badge');
        const statusActions = container.querySelector('.status-actions');
        const statusSelect = container.querySelector('.delivery-status-select');
        const updateBtn = container.querySelector('.update-status-btn');
        
        // Show/hide actions on badge click with smooth animation
        if (statusBadge && statusActions) {
            statusBadge.addEventListener('click', () => {
                const isVisible = statusActions.style.display === 'block';
                
                // Hide all other status action menus
                document.querySelectorAll('.status-actions').forEach(actions => {
                    if (actions !== statusActions) {
                        actions.style.opacity = '0';
                        setTimeout(() => {
                            actions.style.display = 'none';
                        }, 300);
                    }
                });
                
                if (isVisible) {
                    statusActions.style.opacity = '0';
                    setTimeout(() => {
                        statusActions.style.display = 'none';
                    }, 300);
                } else {
                    statusActions.style.display = 'block';
                    statusActions.style.opacity = '0';
                    setTimeout(() => {
                        statusActions.style.opacity = '1';
                    }, 10);
                }
            });
        }
        
        // Handle status changes with visual feedback
        if (updateBtn && statusSelect) {
            updateBtn.addEventListener('click', async function() {
                const equipmentId = this.dataset.equipmentId;
                const newStatus = statusSelect.value;
                const prepTimeInput = container.querySelector('.prep-time');
                const deliveryDateInput = container.querySelector('.delivery-date');
                
                // Show loading state
                updateBtn.disabled = true;
                updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Kaydediliyor...';
                
                try {
                    const response = await fetch(`/equipment/delivery-status/${equipmentId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: new URLSearchParams({
                            'status': newStatus,
                            'prep_time': prepTimeInput ? prepTimeInput.value : '',
                            'delivery_date': deliveryDateInput ? deliveryDateInput.value : ''
                        })
                    });
                    
                    if (response.ok) {
                        // Update the UI without reloading
                        updateStatusBadge(container, newStatus);
                        
                        // Show success message
                        showToast('Teslim durumu başarıyla güncellendi!', 'success');
                        
                        // Hide status actions
                        statusActions.style.opacity = '0';
                        setTimeout(() => {
                            statusActions.style.display = 'none';
                        }, 300);
                    } else {
                        throw new Error('Status update failed');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showToast('Durum güncellenirken bir hata oluştu!', 'error');
                } finally {
                    // Reset button state
                    updateBtn.disabled = false;
                    updateBtn.innerHTML = '<i class="fas fa-save me-1"></i> Kaydet';
                }
            });
            
            // Show/hide additional fields based on selected status
            statusSelect.addEventListener('change', function() {
                const newStatus = this.value;
                const prepTimeField = container.querySelector('.prep-time')?.closest('.form-group');
                const deliveryDateField = container.querySelector('.delivery-date')?.closest('.form-group');
                
                if (prepTimeField) {
                    prepTimeField.style.display = newStatus === 'Hazırlanıyor' ? 'block' : 'none';
                }
                
                if (deliveryDateField) {
                    deliveryDateField.style.display = newStatus === 'Teslim Edildi' ? 'block' : 'none';
                }
            });
        }
    });
}

// Update status badge in UI
function updateStatusBadge(container, newStatus) {
    const statusBadge = container.querySelector('.status-badge');
    if (!statusBadge) return;
    
    // Remove all status classes
    statusBadge.classList.remove('status-teslim-edilmedi', 'status-hazirlaniyor', 'status-teslim-edildi');
    
    // Add new status class
    const statusClass = `status-${newStatus.toLowerCase().replace(' ', '-')}`;
    statusBadge.classList.add(statusClass);
    
    // Update text with animation
    statusBadge.style.opacity = '0';
    setTimeout(() => {
        statusBadge.textContent = newStatus;
        
        // Add delivery date badge if needed
        if (newStatus === 'Teslim Edildi') {
            const today = new Date();
            const formattedDate = `${today.getDate().toString().padStart(2, '0')}/${(today.getMonth() + 1).toString().padStart(2, '0')}/${today.getFullYear()}`;
            
            const deliveryDateBadge = document.createElement('div');
            deliveryDateBadge.className = 'delivery-date-badge';
            deliveryDateBadge.textContent = formattedDate;
            
            // Remove existing delivery date badge if any
            const existingBadge = statusBadge.querySelector('.delivery-date-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            statusBadge.appendChild(deliveryDateBadge);
        } else {
            // Remove delivery date badge if exists
            const existingBadge = statusBadge.querySelector('.delivery-date-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
        }
        
        statusBadge.style.opacity = '1';
    }, 300);
}

// Show toast notification
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = `toast bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white`;
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="toast-header bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} text-white">
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            <strong class="me-auto">${type === 'error' ? 'Hata' : type === 'success' ? 'Başarılı' : 'Bilgi'}</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // Initialize and show toast
    const toast = new bootstrap.Toast(toastEl, { 
        animation: true,
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove toast after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
