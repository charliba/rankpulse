/**
 * RankPulse — JavaScript utilities
 * HTMX + Alpine.js + Chart.js for interactivity.
 */

document.addEventListener('DOMContentLoaded', function() {
    // HTMX after-swap handler
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Re-initialize any needed components
    });
});

// Toast notification helper
function showToast(message, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const bgColor = type === 'success' ? 'bg-green-600' 
                  : type === 'error'   ? 'bg-red-600' 
                  : type === 'warning' ? 'bg-yellow-600' 
                  : 'bg-blue-600';

    const toast = document.createElement('div');
    toast.className = `toast px-4 py-3 rounded-lg shadow-lg text-white text-sm ${bgColor}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copiado!', 'success');
    }).catch(function() {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('Copiado!', 'success');
    });
}

// Format number with locale
function formatNumber(n) {
    return new Intl.NumberFormat('pt-BR').format(n);
}
