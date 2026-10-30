const API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://safecity-backend-fgwl.onrender.com';
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
        
        const addBtn = document.getElementById('addSensorBtn');
        
        if (currentUser.role === 'admin') {
            badge.classList.add('admin');
            addBtn.style.display = 'inline-flex';  // Mostrar solo para admin
        } else {
            badge.classList.remove('admin');
            addBtn.style.display = 'none';  // Ocultar explícitamente para viewer
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
    
    const isAdmin = currentUser && currentUser.role === 'admin';
    
    grid.innerHTML = sensors.map(s => `
        <div class="sensor-card">
            <h3><span class="status ${s.risk_level}"></span>${s.name}</h3>
            <div class="river"><i class="fa-solid fa-water" style="color: #38bdf8; margin-right: 0.3rem"></i>${s.river_name}</div>
            <div class="level">${parseFloat(s.water_level).toFixed(2)} <span>m</span></div>
            <span class="risk-badge ${s.risk_level}">${s.risk_level}</span>
            ${isAdmin ? `
            <div class="sensor-actions">
                <button class="btn-edit" onclick="openEditModal('${s._id}', '${s.name}', '${s.river_name}', ${s.location?.lat || 0}, ${s.location?.lng || 0})">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button class="btn-delete" onclick="deleteSensor('${s._id}', '${s.name}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
            ` : ''}
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
    document.getElementById('addSensorBtn').style.display = 'none';
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

// ===== EDITAR SENSOR =====
function openEditModal(id, name, river, lat, lng) {
    document.getElementById('editSensorId').value = id;
    document.getElementById('editSensorName').value = name;
    document.getElementById('editSensorRiver').value = river;
    document.getElementById('editSensorLat').value = lat;
    document.getElementById('editSensorLng').value = lng;
    document.getElementById('editModalError').style.display = 'none';
    document.getElementById('editSensorModal').classList.add('active');
}

function closeEditModal() {
    document.getElementById('editSensorModal').classList.remove('active');
}

async function updateSensor() {
    const id = document.getElementById('editSensorId').value;
    try {
        await request(`/sensors/${id}`, 'PUT', {
            name: document.getElementById('editSensorName').value,
            river_name: document.getElementById('editSensorRiver').value,
            location: {
                lat: parseFloat(document.getElementById('editSensorLat').value),
                lng: parseFloat(document.getElementById('editSensorLng').value)
            }
        });
        closeEditModal();
        loadData();
        alert('✅ Sensor actualizado correctamente');
    } catch (err) {
        document.getElementById('editModalError').textContent = err.message;
        document.getElementById('editModalError').style.display = 'block';
    }
}

// ===== ELIMINAR SENSOR =====
async function deleteSensor(id, name) {
    if (!confirm(`¿Estás seguro de eliminar "${name}"?\n\nSe eliminarán también todas sus lecturas y alertas asociadas.`)) {
        return;
    }
    
    try {
        await request(`/sensors/${id}`, 'DELETE');
        loadData();
        alert('✅ Sensor eliminado correctamente');
    } catch (err) {
        alert('Error: ' + err.message);
    }
}


// ===== SIMULADOR LOCAL DE DATOS EN TIEMPO REAL =====
const LOCAL_SENSORS = [
    { _id: 'sim1', name: 'Sensor Puente Aranda', river_name: 'Río Bogotá', base_level: 1.5, water_level: 1.5, risk_level: 'normal', location: { lat: 4.6097, lng: -74.0817 } },
    { _id: 'sim2', name: 'Sensor La Calera', river_name: 'Quebrada La Vieja', base_level: 1.2, water_level: 1.2, risk_level: 'normal', location: { lat: 4.7110, lng: -74.0721 } },
    { _id: 'sim3', name: 'Sensor Bosa', river_name: 'Río Fucha', base_level: 1.8, water_level: 1.8, risk_level: 'alerta', location: { lat: 4.6280, lng: -74.1460 } },
    { _id: 'sim4', name: 'Sensor Usme', river_name: 'Quebrada San Cristóbal', base_level: 1.0, water_level: 1.0, risk_level: 'normal', location: { lat: 4.5615, lng: -74.1500 } }
];

function simulateReadings() {
    LOCAL_SENSORS.forEach(sensor => {
        let level = sensor.base_level + (Math.random() * 0.4 - 0.2);
        if (Math.random() < 0.15) level += Math.random() * 2.5;
        level = Math.max(0.5, level).toFixed(2);
        
        sensor.water_level = level;
        if (level > 2.5) sensor.risk_level = 'peligro';
        else if (level > 1.8) sensor.risk_level = 'alerta';
        else sensor.risk_level = 'normal';
    });
    
    if (document.getElementById('dashboardView').style.display === 'block') {
        renderSensors(LOCAL_SENSORS);
        updateStats(LOCAL_SENSORS);
    }
}

function updateStats(sensors) {
    const total = sensors.length;
    const normal = sensors.filter(s => s.risk_level === 'normal').length;
    const alerta = sensors.filter(s => s.risk_level === 'alerta').length;
    const peligro = sensors.filter(s => s.risk_level === 'peligro').length;
    
    const values = document.querySelectorAll('.stat-card .value');
    if (values.length >= 4) {
        values[0].textContent = total;
        values[1].textContent = normal;
        values[2].textContent = alerta;
        values[3].textContent = peligro;
    }
}

// Iniciar simulación cada 5 segundos
setInterval(simulateReadings, 5000);

// Ejecutar inmediatamente al cargar
if (document.getElementById('dashboardView').style.display === 'block') {
    simulateReadings();
}