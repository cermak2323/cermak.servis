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
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        data: { search_term: request.term },
                        success: function(data) {
                            response(data.map(function(item) {
                                return {
                                    label: item.part_code + ' - ' + item.part_name,
                                    value: item.part_code,
                                    part: item
                                };
                            }));
                        },
                        error: function(xhr, status, error) {
                            console.error('Parça arama hatası:', error);
                        }
                    });
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
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                data: { search_term: searchTerm },
                success: function(data) {
                    if (data && data.length > 0) {
                        addPartToList(data[0]);
                        $('#part_search').val('');
                    } else {
                        alert('Parça bulunamadı!');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Parça ekleme hatası:', error);
                    alert('Parça eklenirken bir hata oluştu!');
                }
            });
        } else {
            alert('Lütfen en az 3 karakter girin!');
        }
    });

    function addPartToList(part) {
        if (!part) return;

        // Duplicate check
        const existingPart = selectedParts.find(p => p.part_code === part.part_code);
        if (existingPart) {
            alert('Bu parça zaten eklenmiş!');
            return;
        }

        selectedParts.push(part);

        // Update the selected parts display
        const selectedPartsDiv = $('#selected_parts');
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
    }

    function removePart(partCode) {
        selectedParts = selectedParts.filter(p => p.part_code !== partCode);
        updateSelectedPartsDisplay();
    }

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
            quantityDiv.addClass('show');
            quantityDiv.find('input').prop('required', true);
        } else {
            quantityDiv.removeClass('show');
            quantityDiv.find('input').prop('required', false);
        }
    });

    // Form validation
    $('#pdfForm').on('submit', function(e) {
        return true;
    });
});