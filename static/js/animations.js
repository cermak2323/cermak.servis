// Document Ready Handler
document.addEventListener('DOMContentLoaded', function() {
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

    // Parallax efekti için
    document.addEventListener('mousemove', (e) => {
        const moveX = (e.clientX - window.innerWidth / 2) * 0.01;
        const moveY = (e.clientY - window.innerHeight / 2) * 0.01;
        
        document.querySelector('.welcome-container').style.transform = 
            `translate(${moveX}px, ${moveY}px) rotate(${moveX * 0.1}deg)`;
    });
});
