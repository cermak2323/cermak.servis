
// İki saat hareketsizlik kontrolü
let inactivityTimeout;
const INACTIVITY_DURATION = 2 * 60 * 60 * 1000; // 2 saat

function resetInactivityTimeout() {
    clearTimeout(inactivityTimeout);
    inactivityTimeout = setTimeout(logout, INACTIVITY_DURATION);
}

function setupInactivityDetection() {
    document.addEventListener('mousemove', resetInactivityTimeout);
    document.addEventListener('keypress', resetInactivityTimeout);
    resetInactivityTimeout();
}

// Sekme kapatıldığında çıkış yapma
window.addEventListener('beforeunload', function(e) {
    if (document.visibilityState === 'hidden') {
        e.preventDefault();
        e.returnValue = 'Oturumu kapatmak istiyor musunuz?';
        return e.returnValue;
    }
});

function logout() {
    fetch('/auth/logout', {
        method: 'GET',
        credentials: 'same-origin'
    }).then(() => {
        window.location.href = '/auth/login';
    });
}

setupInactivityDetection();