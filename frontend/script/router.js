
// Base Path Auto-Detection (consistente con layout.js)
const BASE = (() => {
    const { hostname, pathname } = window.location;
    const isGhPages = hostname.endsWith('github.io');
    const isLocal = hostname === '' || hostname === 'localhost' || hostname === '127.0.0.1';
    if (isGhPages || (!isLocal && pathname.startsWith('/ALGARROBO_BASE2'))) {
        return '/ALGARROBO_BASE2';
    }
    return '';
})();

const diccionarioRutas = {
    10: [
        `${BASE}/frontend/division/secplan/admin_general/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_general/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_general/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_general/informe.html`,
        `${BASE}/frontend/division/secplan/admin_general/calendario.html`,
        `${BASE}/frontend/administracion/`
    ],
    11: [
        `${BASE}/frontend/division/secplan/admin_proyectos/dashboard.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/proyecto.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/mapa.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/informe.html`,
        `${BASE}/frontend/division/secplan/admin_proyectos/calendario.html`,
        `${BASE}/frontend/administracion/index.html`
    ],
    12: [
        `${BASE}/frontend/division/secplan/director_obras/dashboard.html`,
        `${BASE}/frontend/division/secplan/director_obras/proyecto.html`,
        `${BASE}/frontend/division/secplan/director_obras/mapa.html`,
        `${BASE}/frontend/division/secplan/director_obras/informe.html`,
        `${BASE}/frontend/division/secplan/director_obras/calendario.html`,
        `${BASE}/frontend/administracion/index.html`
    ]
};

function verificarRutaPermitida(user) {
    if (!user) return false;
    const nivelAcceso = user.nivel_acceso;
    const path = window.location.pathname;

    const rutasPermitidas = diccionarioRutas[nivelAcceso] || [];
    const pathNormalizado = path.replace(/\/+$/, "");

    return rutasPermitidas.some(ruta =>
        pathNormalizado.includes(ruta.replace(/\/+$/, ""))
    );
}

function checkLoginStatus() {
    const userDataString = localStorage.getItem('userData') || localStorage.getItem('user_data');
    if (!userDataString) {
        window.location.href = `${BASE}/frontend/index.html`;
        return [null, null];
    }

    let userData;
    try {
        userData = JSON.parse(userDataString);
    } catch (e) {
        window.location.href = `${BASE}/frontend/index.html`;
        return [null, null];
    }

    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const token = localStorage.getItem('authToken');

    if (!isLoggedIn || isLoggedIn !== 'true' || !token) {
        const currentUrl = window.location.href;
        window.location.href = `${BASE}/frontend/index.html?redirect=${encodeURIComponent(currentUrl)}`;
        return [null, null];
    }

    // Role verification (Control de Acceso)
    const validRoles = [10, 11]; // admin_general (10), admin_proyectos (11)
    let userRole = null;
    
    if (userData.roles && userData.roles.length > 0) {
        userRole = userData.roles[0].role_id;
    } else if (userData.nivel_acceso) {
        userRole = parseInt(userData.nivel_acceso);
    }

    if (!validRoles.includes(userRole)) {
        console.error("Acceso denegado: Rol no autorizado.");
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('authToken');
        localStorage.removeItem('userData');
        localStorage.removeItem('user_data');
        localStorage.removeItem('user');
        window.location.href = `${BASE}/frontend/index.html`;
        return [null, null];
    }

    return [token, userData];
}

function logout() {
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    localStorage.removeItem('user_data');
    localStorage.removeItem('user');
    window.location.href = `${BASE}/frontend/index.html`;
}

function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    if (menu) menu.classList.toggle('hidden');
}

function toggleNotifications() {
    console.log("Notificaciones - En desarrollo");
}

const [token, userData] = checkLoginStatus();

if (userData && !verificarRutaPermitida(userData)) {
    window.location.href = `${BASE}/frontend/index.html`;
}

document.addEventListener('click', function (event) {
    const userMenu = document.getElementById('userMenu');
    const userButton = event.target.closest('button[onclick="toggleUserMenu()"]');

    if (userMenu && !userButton && !userMenu.contains(event.target)) {
        userMenu.classList.add('hidden');
    }
});


function strToBytes(str) {
    return new TextEncoder().encode(str);
}

function bytesToStr(bytes) {
    return new TextDecoder().decode(bytes);
}

function getKey(seed) {
    const OFUSCADO = "VgAMFkZXBBFdUEpXQwFFXRZXA19NXV1XXQdQBVpDFlBIIwMkGxUkEgJcIRAXAUBcBQ=="; // <-- generado antes

    const data = Uint8Array.from(
        atob(OFUSCADO),
        c => c.charCodeAt(0)
    );

    const s = strToBytes(seed);
    const out = new Uint8Array(data.length);

    for (let i = 0; i < data.length; i++) {
        out[i] = data[i] ^ s[i % s.length];
    }

    return bytesToStr(out);
}





