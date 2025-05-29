
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('machineRegistrationForm');
    if (!form) return;

    const steps = document.querySelectorAll('.registration-step');
    const progressSteps = document.querySelectorAll('.progress-step');
    const progressBar = document.getElementById('registrationProgress');

    let currentStep = 1;
    const totalSteps = steps.length;

    function showStep(step) {
        steps.forEach((s, index) => {
            if (index + 1 === step) {
                s.style.display = 'block';
            } else {
                s.style.display = 'none';
            }
        });

        // Her adımda butonları güncelle
        updateNavigationButtons(step);
    }

    function updateNavigationButtons(step) {
        // Önceki butonları temizle
        const oldButtons = document.querySelectorAll('.next-prev-container');
        oldButtons.forEach(container => container.remove());

        // Yeni buton container oluştur
        const navigationContainer = document.createElement('div');
        navigationContainer.className = 'next-prev-container';

        // Geri butonu
        if (step > 1) {
            const prevButton = document.createElement('button');
            prevButton.type = 'button';
            prevButton.className = 'btn prev-step-btn';
            prevButton.innerHTML = '<i class="fas fa-arrow-left me-1"></i> Geri';
            prevButton.onclick = () => {
                currentStep--;
                showStep(currentStep);
                updateProgressBar();
            };
            navigationContainer.appendChild(prevButton);
        }

        // İleri/Kaydet butonu
        const nextButton = document.createElement('button');
        nextButton.type = step === totalSteps ? 'submit' : 'button';
        nextButton.className = step === totalSteps ? 'btn submit-form-btn' : 'btn next-step-btn';
        nextButton.innerHTML = step === totalSteps ? 
            '<i class="fas fa-save me-1"></i> Makineyi Kaydet' : 
            'İleri <i class="fas fa-arrow-right ms-1"></i>';
        
        if (step !== totalSteps) {
            nextButton.onclick = () => {
                if (validateStep(currentStep)) {
                    currentStep++;
                    showStep(currentStep);
                    updateProgressBar();
                }
            };
        }
        navigationContainer.appendChild(nextButton);

        // Container'ı mevcut adıma ekle
        const currentStepElement = document.querySelector(`.registration-step[data-step="${step}"]`);
        currentStepElement.appendChild(navigationContainer);
    }

    function updateProgressBar() {
        const progressPercentage = ((currentStep - 1) / (totalSteps - 1)) * 100;
        progressBar.style.width = progressPercentage + '%';
        progressBar.setAttribute('aria-valuenow', progressPercentage);

        progressSteps.forEach((step, index) => {
            const container = step.closest('.progress-step-container');
            if (container) {
                if (index + 1 <= currentStep) {
                    container.classList.add('active');
                } else {
                    container.classList.remove('active');
                }
            }
        });
    }

    function validateStep(step) {
        const currentStepEl = document.querySelector(`.registration-step[data-step="${step}"]`);
        const requiredFields = currentStepEl.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value) {
                isValid = false;
                field.classList.add('is-invalid');
                showToast('Lütfen tüm zorunlu alanları doldurun!', 'error');
            } else {
                field.classList.remove('is-invalid');
            }
        });

        return isValid;
    }

    // Başlangıç adımını göster
    showStep(currentStep);
    updateProgressBar();

    // Ekipman bölümü işlevselliği
    setupEquipmentSection();
});

function setupEquipmentSection() {
    const addEquipmentBtn = document.getElementById('addEquipment');
    if (!addEquipmentBtn) return;

    addEquipmentBtn.addEventListener('click', function() {
        const equipmentList = document.querySelector('.equipment-list');
        const equipmentCount = equipmentList.querySelectorAll('.equipment-item').length;

        if (equipmentCount >= 10) {
            showToast('En fazla 10 ekipman ekleyebilirsiniz!', 'error');
            return;
        }

        const newEquipment = document.createElement('div');
        newEquipment.className = 'equipment-item mb-4';
        newEquipment.innerHTML = `
            <div class="card equipment-card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Ekipman #${equipmentCount + 1}</h5>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-equipment-btn">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">Ekipman Türü</label>
                            <select class="form-select equipment-type" name="equipment_type[]" required>
                                <option value="">Ekipman Türü Seçin</option>
                                <option value="kova">Kova</option>
                                <option value="atasman">Ataşman</option>
                                <option value="quickhitch">Quick Hitch</option>
                                <option value="50_saat_bakim">50 Saat Bakım Filtre Seti</option>
                                <option value="250_saat_bakim">250 Saat Bakım Filtre Seti</option>
                                <option value="500_saat_bakim">500 Saat Bakım Filtre Seti</option>
                                <option value="750_saat_bakim">750 Saat Bakım Filtre Seti</option>
                                <option value="1000_saat_bakim">1000 Saat Bakım Filtre Seti</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Boyut/Ölçü</label>
                            <select class="form-select kova-size d-none" name="equipment_size[]">
                                <option value="">Genişlik Seçin (cm)</option>
                                <option value="20">20 cm</option>
                                <option value="25">25 cm</option>
                                <option value="30">30 cm</option>
                                <option value="35">35 cm</option>
                                <option value="40">40 cm</option>
                                <option value="45">45 cm</option>
                                <option value="50">50 cm</option>
                                <option value="55">55 cm</option>
                                <option value="60">60 cm</option>
                                <option value="65">65 cm</option>
                                <option value="70">70 cm</option>
                                <option value="75">75 cm</option>
                                <option value="80">80 cm</option>
                                <option value="90">90 cm</option>
                                <option value="100">100 cm</option>
                                <option value="110">110 cm</option>
                                <option value="120">120 cm</option>
                                <option value="140">140 cm</option>
                                <option value="160">160 cm</option>
                            </select>
                            <input type="text" class="form-control size-input d-none" name="equipment_size[]" placeholder="Ölçü/Boyut">
                        </div>
                        <div class="col-12">
                            <label class="form-label">Detaylar</label>
                            <textarea class="form-control" name="equipment_details[]" rows="2" placeholder="Ekipman hakkında ek detaylar"></textarea>
                        </div>
                    </div>
                </div>
            </div>
        `;

        equipmentList.appendChild(newEquipment);

        // Yeni eklenen ekipman için event listener'ları ekle
        const removeBtn = newEquipment.querySelector('.remove-equipment-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                newEquipment.remove();
            });
        }

        const equipmentType = newEquipment.querySelector('.equipment-type');
        const kovaSize = newEquipment.querySelector('.kova-size');
        const sizeInput = newEquipment.querySelector('.size-input');

        if (equipmentType) {
            equipmentType.addEventListener('change', function() {
                if (kovaSize) kovaSize.classList.add('d-none');
                if (sizeInput) sizeInput.classList.add('d-none');

                if (this.value === 'kova') {
                    if (kovaSize) kovaSize.classList.remove('d-none');
                    if (sizeInput) sizeInput.value = '';
                } else if (this.value !== '') {
                    if (sizeInput) sizeInput.classList.remove('d-none');
                    if (kovaSize) kovaSize.value = '';
                }
            });
        }
    });
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            <strong class="me-auto">${type === 'error' ? 'Hata' : 'Bilgi'}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}
