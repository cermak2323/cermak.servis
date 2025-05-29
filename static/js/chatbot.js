// Chatbot'u açıp kapatma fonksiyonu
function toggleChatbot() {
    var chatbot = document.getElementById('chatbot');
    // Eğer chatbot gizli ise, göster
    if (chatbot.style.display === 'none') {
        chatbot.style.display = 'block';
    } else {
        // Eğer chatbot görünürse, gizle
        chatbot.style.display = 'none';
    }
}
