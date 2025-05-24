$(document).ready(function() {
    let selectedParts = [];
    let searchTimeout;

    // Part search autocomplete
    $('#part_search').autocomplete({
        source: function(request, response) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                if (request.term.length >= 3) {
                    $.ajax({
                        url: '/periodic_maintenance/search_parts',
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        data: { search_term: request.term },
                        success: function(data) {
                            if (data && data.length > 0) {
                                response(data.map(function(item) {
                                    return {
                                        label: item.part_code + ' - ' + item.part_name,
                                        value: item.part_code,
                                        part: item
                                    };
                                }));
                            } else {
                                response([]);
                                console.log('Parça bulunamadı: ' + request.term);
                            }
                        },
                        error: function(xhr, status, error) {
                            console.error('Parça arama hatası:', error);
                            alert('Parça arama sırasında bir hata oluştu: ' + error);
                        }
                    });
                } else {
                    response([]);
                }
            }, 300);
        },
        minLength: 3,
        select: function(event, ui) {
            if (ui.item) {
                addPartToList(ui.item.part);
                $(this).val('');
                return false;
            }
        }
    });

    // Add button click handler
    $('#add_part_btn').on('click', function(e) {
        e.preventDefault();
        const searchTerm = $('#part_search').val().trim();
        if (searchTerm.length >= 3) {
            $.ajax({
                url: '/periodic_maintenance/search_parts',
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                data: { search_term: searchTerm },
                success: function(data) {
                    if (data && data.length > 0) {
                        addPartToList(data[0]);
                        $('#part_search').val('');
                    } else {
                        alert('Aradığınız parça bulunamadı: ' + searchTerm);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Parça ekleme hatası:', error);
                    alert('Parça eklenirken bir hata oluştu: ' + error);
                }
            });
        } else {
            alert('Lütfen en az 3 karakter girin!');
        }
    });

    function addPartToList(part) {
        if (!part) return;

        const existingPart = selectedParts.find(p => p.part_code === part.part_code);
        if (existingPart) {
            alert('Bu parça zaten eklenmiş!');
            return;
        }

        selectedParts.push(part);
        updateSelectedPartsDisplay();
    }

    window.removePart = function(partCode) {
        selectedParts = selectedParts.filter(p => p.part_code !== partCode);
        updateSelectedPartsDisplay();
    };

    function updateSelectedPartsDisplay() {
        const selectedPartsDiv = $('#selected_parts');
        selectedPartsDiv.empty();
        selectedParts.forEach(part => {
            const partElement = $(`
                <div class="mb-2 p-2 bg-gray-100 rounded flex justify-between items-center">
                    <span>${part.part_code} - ${part.part_name} (${part.price_eur} EUR)</span>
                    <button type="button" class="text-red-600 hover:text-red-800" onclick="removePart('${part.part_code}')">
                        Kaldır
                    </button>
                    <input type="hidden" name="selected_parts[][id]" value="${part.id}">
                    <input type="hidden" name="selected_parts[][part_code]" value="${part.part_code}">
                    <input type="hidden" name="selected_parts[][part_name]" value="${part.part_name}">
                    <input type="hidden" name="selected_parts[][price_eur]" value="${part.price_eur}">
                </div>
            `);
            selectedPartsDiv.append(partElement);
        });
    }

    // Yağ checkbox'ları için event handler
    $('.oil-checkbox').on('change', function() {
        const oilId = $(this).data('oil');
        const quantityDiv = $(`#quantity_${oilId}`);
        if (this.checked) {
            quantityDiv.addClass('show').removeClass('quantity-container');
            quantityDiv.find('input').prop('required', true);
        } else {
            quantityDiv.removeClass('show').addClass('quantity-container');
            quantityDiv.find('input').prop('required', false).val(1);
        }
    });

    // Form validation
    $('#pdfForm').on('submit', function(e) {
        // Filtre tipi kontrolü - daha sıkı validasyon
        const filterType = $('input[name="filter_type"]:checked').val();
        if (!filterType) {
            e.preventDefault();
            alert('LÜTFEN FİLTRE TÜRÜNÜ SEÇİN (ORİJİNAL/MUADİL)!');
            $('input[name="filter_type"]').first().focus();
            return false;
        }

        // Parça veya yağ seçimi kontrolü
        if (selectedParts.length === 0 && $('input[name^="oil_"]:checked').length === 0) {
            e.preventDefault();
            alert('Lütfen en az bir parça veya yağ seçin!');
            return false;
        }

        // Diğer form alanları kontrolü
        const requiredFields = {
            'serial_number': 'Seri Numarası',
            'customer_first_name': 'Müşteri Adı',
            'customer_last_name': 'Müşteri Soyadı',
            'company_name': 'Firma Adı',
            'phone': 'Telefon',
            'offeror_name': 'Teklifi Veren'
        };

        for (const [fieldName, fieldLabel] of Object.entries(requiredFields)) {
            const value = $(`[name="${fieldName}"]`).val();
            if (!value || value.trim() === '') {
                e.preventDefault();
                alert(`${fieldLabel} alanı boş bırakılamaz!`);
                $(`[name="${fieldName}"]`).focus();
                return false;
            }
        }

        return true;
    });

    // Filtre tipi değiştiğinde parçaları güncelle
    $('input[name="filter_type"]').on('change', function() {
        const filterType = $(this).val();
        const machineModel = $('select[name="machine_model"]').val();
        const maintenanceInterval = $('select[name="maintenance_interval"]').val();

        if (machineModel && maintenanceInterval) {
            // Parçaları yeniden yükle
            $.ajax({
                url: '/periodic_maintenance/get_maintenance_parts',
                method: 'GET',
                data: {
                    machine_model: machineModel,
                    maintenance_interval: maintenanceInterval,
                    filter_type: filterType
                },
                success: function(response) {
                    if (response.parts && response.parts.length > 0) {
                        const partsContainer = $('#selected_parts');
                        partsContainer.empty();

                        response.parts.forEach(function(part) {
                            const partHtml = `
                                <div class="mb-2 p-2 bg-gray-100 rounded flex justify-between items-center">
                                    <span>${part.part_code} - ${part.name} (${part.price_tl.toFixed(2)} TL)</span>
                                    <input type="hidden" name="selected_parts[][id]" value="${part.id}">
                                    <input type="hidden" name="selected_parts[][part_code]" value="${part.part_code}">
                                    <input type="hidden" name="selected_parts[][part_name]" value="${part.name}">
                                    <input type="hidden" name="selected_parts[][price_tl]" value="${part.price_tl}">
                                    <input type="hidden" name="selected_parts[][is_alternate]" value="${part.is_alternate ? 'true' : 'false'}">
                                </div>
                            `;
                            partsContainer.append(partHtml);
                        });
                    } else {
                        $('#selected_parts').html('<p class="text-red-600">Seçilen kriterlere uygun parça bulunamadı.</p>');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Parça listesi alınırken hata:', error);
                    alert('Parça listesi alınırken bir hata oluştu: ' + error);
                }
            });
        }
    });
});