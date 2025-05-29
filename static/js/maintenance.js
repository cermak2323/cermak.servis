
function quickAddHours(btn, hours) {
    const input = btn.closest('form').querySelector('input[name="usage_hours"]');
    input.value = parseInt(input.value) + hours;
    btn.closest('form').submit();
}
