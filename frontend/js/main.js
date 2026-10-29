const API_URL = 'http://localhost:8000';
let token = localStorage.getItem('token');
let currentUser = null;

if (token) showDashboard();

function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('loginForm').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('registerForm').style.display = tab === 'register' ? 'block' : 'none';

    if (tab === 'login') {
        document.getElementById('regUser').value = '';
        document.getElementById('regEmail').value = '';
        document.getElementById('regPass').value = '';
        document.getElementById('regRole').value = 'viewer';
    } else {
        document.getElementById('loginUser').value = '';
        document.getElementById('loginPass').value = '';
    }
}

function showError(msg, isModal = false) {
    const el = document.getElementById(isModal ? 'modalError' : 'errorMsg');
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 4000);
}

async function request(url, method = 'GET', body = null, useAuth = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (useAuth && token) headers['Authorization'] = 'Bearer ' + token;
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API_URL + url, opts);
    
    if (res.status === 401 && token) { 
        logout(); 
        throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.'); 
    }
    
    if (!res.ok) {
        const err = await res.json().catch(() => ({detail: 'Error en la petición'}));
        let message = 'Error desconocido';
        if (typeof err.detail === 'string') {
            message = err.detail;
        } else if (Array.isArray(err.detail)) {
            message = err.detail[0]?.msg || 'Error de validación en los campos';
        }
        throw new Error(message);
    }
    return res.json();
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const data = await request('/auth/login', 'POST', {
            username: document.getElementById('loginUser').value,
            password: document.getElementById('loginPass').value
        }, false);
        token = data.access_token;
        localStorage.setItem('token', token);
        showDashboard();
    } catch (err) { showError(err.message); }
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        await request('/auth/register', 'POST', {
            username: document.getElementById('regUser').value,
            email: document.getElementById('regEmail').value,
            password: document.getElementById('regPass').value,
            role: document.getElementById('regRole').value
        }, false);
        alert('✅ Usuario creado exitosamente. Ahora inicia sesión.');
        
        document.getElementById('regUser').value = '';
        document.getElementById('regEmail').value = '';
        document.getElementById('regPass').value = '';
        document.getElementById('regRole').value = 'viewer';

        switchTab('login');
        document.querySelector('.tab').click();
    } catch (err) { showError(err.message); }
});

async function showDashboard() {
    try {
        currentUser = await request('/auth/me');
        document.getElementById('loginView').style.display = 'none';
        document.getElementById('dashboardView').style.display = 'block';
        const badge = document.getElementById('userBadge');
        badge.innerHTML = '<i class="fa-solid fa-user"></i> ' + currentUser.username + ' (' + currentUser.role + ')';
        if (currentUser.role === 'admin') {
            badge.classList.add('admin');
            document.getElementById('addSensorBtn').style.display = 'inline-flex';
        }
        loadData();
    } catch (err) { logout(); }
}

async function loadData() {
    try {
        const [sensors, alerts] = await Promise.all([
            request('/sensors/'),
            request('/alerts/')
        ]);
        
        let readings = [];
        try {
            readings = await request('/readings/');
        } catch (err) {
            console.warn('No se pudieron cargar las lecturas:', err);
        }
        
        const latestReadings = {};
        readings.forEach(r => {
            if (!latestReadings[r.sensor_id] || new Date(r.timestamp) > new Date(latestReadings[r.sensor_id].timestamp)) {
                latestReadings[r.sensor_id] = r;
            }
        });
        
        const sensorsWithLevel = sensors.map(s => {
            const latest = latestReadings[s._id];
            return {
                ...s,
                water_level: latest ? latest.water_level : 0.0,
                risk_level: latest ? latest.risk_level : 'normal'
            };
        });
        
        renderSensors(sensorsWithLevel);
        renderAlerts(alerts);
        updateStats(sensorsWithLevel);
    } catch (err) { 
        console.error('Error cargando datos:', err); 
    }
}

function renderSensors(sensors) {
    const grid = document.getElementById('sensorsGrid');
    if (!sensors.length) { grid.innerHTML = '<div class="empty-state">No hay sensores registrados</div>'; return; }
    grid.innerHTML = sensors.map(s => `
        <div class="sensor-card">
            <h3><span class="status ${s.risk_level}"></span>${s.name}</h3>
<div class="river"><i class="fa-solid fa-water" style="color: #38bdf8; margin-right: 0.3rem"></i>${s.river_name}</div>            <div class="level">${parseFloat(s.water_level).toFixed(2)} <span>m</span></div>
            <span class="risk-badge ${s.risk_level}">${s.risk_level}</span>
        </div>
    `).join('');
}

function renderAlerts(alerts) {
    const list = document.getElementById('alertsList');
    const recentAlerts = alerts.slice(0, 5);
    if (!recentAlerts.length) { 
        list.innerHTML = '<div class="empty-state">✅ No hay alertas activas recientes</div>'; 
        return; 
    }
    list.innerHTML = recentAlerts.map(a => `
        <div class="alert-item ${a.risk_level}">
<div class="icon"><i class="fa-solid ${a.risk_level === 'peligro' ? 'fa-circle-exclamation' : 'fa-circle-exclamation'}" style="color: ${a.risk_level === 'peligro' ? '#ef4444' : '#f59e0b'}"></i></div>            <div class="content">
                <div class="message">${a.message || 'Nivel de agua alcanzó umbral de ' + a.risk_level}</div>
                <div class="time">🕒 ${new Date(a.created_at).toLocaleString('es-CO')}</div>
            </div>
        </div>
    `).join('');
}

function updateStats(sensors) {
    document.getElementById('statSensors').textContent = sensors.length;
    document.getElementById('statDanger').textContent = sensors.filter(s => s.risk_level === 'peligro').length;
    document.getElementById('statAlert').textContent = sensors.filter(s => s.risk_level === 'alerta').length;
    document.getElementById('statNormal').textContent = sensors.filter(s => s.risk_level === 'normal').length;
}

function openModal() { document.getElementById('sensorModal').classList.add('active'); }

function closeModal() { 
    document.getElementById('sensorModal').classList.remove('active'); 
    document.getElementById('modalError').style.display = 'none';
    document.getElementById('sensorName').value = '';
    document.getElementById('sensorRiver').value = '';
    document.getElementById('sensorLat').value = '';
    document.getElementById('sensorLng').value = '';
}

async function createSensor() {
    try {
        await request('/sensors/', 'POST', {
            name: document.getElementById('sensorName').value,
            river_name: document.getElementById('sensorRiver').value,
            location: {
                lat: parseFloat(document.getElementById('sensorLat').value),
                lng: parseFloat(document.getElementById('sensorLng').value)
            }
        });
        closeModal();
        loadData();
        alert('✅ Sensor registrado correctamente');
    } catch (err) { showError(err.message, true); }
}

function logout() {
    localStorage.removeItem('token');
    token = null;
    currentUser = null;
    document.getElementById('dashboardView').style.display = 'none';
    document.getElementById('loginView').style.display = 'flex';
    document.getElementById('loginUser').value = '';
    document.getElementById('loginPass').value = '';
}

function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);
    const icon = button.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fa-solid fa-eye-slash' ;
    } else {
        input.type = 'password';
        icon.className = 'fa-solid fa-eye';
    }
}

setInterval(() => { if (token) loadData(); }, 15000);

// ===== TEMA CLARO / OSCURO =====
function toggleTheme() {
    const body = document.body;
    const icon = document.getElementById('themeIcon');
    
    body.classList.toggle('light-theme');
    
    if (body.classList.contains('light-theme')) {
        icon.className = 'fa-solid fa-moon';
        localStorage.setItem('theme', 'light');
    } else {
        icon.className = 'fa-solid fa-sun';
        localStorage.setItem('theme', 'dark');
    }
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    const icon = document.getElementById('themeIcon');
    
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        if (icon) icon.className = 'fa-solid fa-moon';
    }
}

loadTheme();