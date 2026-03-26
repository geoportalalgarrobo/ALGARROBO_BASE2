/**
 * portal.js — Portal de Administración
 * Municipalidad de Algarrobo
 * 
 * Responsabilidades:
 * - Verificar autenticación
 * - Saludo dinámico según hora
 * - Animación de entrada de cards
 */

document.addEventListener('DOMContentLoaded', () => {

    /* ── 1. Verificar sesión activa ── */
    const token = localStorage.getItem('authToken');
    if (!token) {
        const base = window.location.hostname.endsWith('github.io') ? '/ALGARROBO_BASE2' : '';
        window.location.href = base + '/frontend/index.html';
        return;
    }

    /* ── 2. Saludo dinámico usando los datos del layout.js ── */
    try {
        const raw = localStorage.getItem('userData') ||
                    localStorage.getItem('user_data') ||
                    localStorage.getItem('user');
        if (raw) {
            const user = JSON.parse(raw);
            const nombre = user?.nombre || user?.nombre_completo || user?.username || 'Usuario';
            const hora = new Date().getHours();
            const saludo = hora < 12 ? 'Buenos días' : hora < 19 ? 'Buenas tardes' : 'Buenas noches';
            const subtitleEl = document.getElementById('hero-subtitle');
            if (subtitleEl) {
                subtitleEl.textContent = `${saludo}, ${nombre.split(' ')[0]}. Seleccione el módulo al que desea acceder.`;
            }
        }
    } catch (e) {
        console.warn('Portal: no se pudo leer datos de usuario:', e);
    }

    /* ── 3. Micro-animación de entrada escalonada de las cards ── */
    const cards = document.querySelectorAll('.module-card');
    cards.forEach((card, i) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `opacity 0.5s ease ${0.35 + i * 0.1}s,
                                  transform 0.5s cubic-bezier(0.34,1.56,0.64,1) ${0.35 + i * 0.1}s,
                                  box-shadow 0.35s ease,
                                  border-color 0.3s`;
        requestAnimationFrame(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        });
    });

});
