// Document Ready Handler
document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.module-card');
    
    cards.forEach((card, index) => {
        card.style.setProperty('--card-index', index);
        
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
});
