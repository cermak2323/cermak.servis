
document.addEventListener('DOMContentLoaded', function() {
    // Table row animations
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach((row, index) => {
        row.style.setProperty('--row-index', index);
    });

    // Dashboard card animations
    const dashboardCards = document.querySelectorAll('.card');
    dashboardCards.forEach((card, index) => {
        card.style.setProperty('--card-index', index);
        card.classList.add('dashboard-card');
    });

    // Form submission loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
            }
        });
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});