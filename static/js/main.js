// Init AOS animations
AOS.init({ once: true, duration: 650, easing: 'ease-out-cubic' });

// Set dynamic year in footer
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();
