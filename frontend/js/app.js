/**
 * VicProj - logica de aplicatie (Router simplu de pagini + apeluri reale catre API).
 * Inlocuieste complet vechiul demo bazat pe array local `filesData` si sessionStorage.
 */

// ---------------- Toast Notifications ----------------

function showToast(message, type = 'error') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;top:16px;right:16px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const isError = type === 'error';
    toast.textContent = message;
    toast.style.cssText = `
        background:${isError ? '#1a0000' : '#111111'};
        color:#ffffff;
        border:1px solid ${isError ? '#ff4444' : '#ffffff'};
        padding:12px 16px;
        border-radius:6px;
        font-size:13px;
        max-width:320px;
        box-shadow:0 4px 12px rgba(0,0,0,0.5);
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

// ---------------- Router ----------------

function switchPage(pageId) {
    const pages = ['presentation', 'admin-login', 'admin-dashboard', 'magic-link-page', 'shared-link'];
    pages.forEach(p => {
        document.getElementById('page-' + p).classList.add('hidden');
        document.getElementById('btn-tab-' + p)?.classList.remove('active');
    });

    document.getElementById('page-' + pageId).classList.remove('hidden');
    document.getElementById('btn-tab-' + pageId)?.classList.add('active');

    if (pageId === 'admin-dashboard') {
        if (!apiClient.isAuthenticated()) {
            showToast('Trebuie sa te autentifici pentru a accesa Dashboard-ul.');
            switchPage('admin-login');
            return;
        }
        renderAdminTable();
    }
}

// La incarcarea paginii: daca URL-ul contine ?magic_token=..., deschide direct pagina F-PAS.
window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const magicToken = params.get('magic_token') || params.get('token');

    // Suport pentru link public direct: https://domeniu/share/x8f9a2
    // (necesita o regula de rewrite pe serverul static care trimite /share/* catre index.html)
    const shareMatch = window.location.pathname.match(/\/share\/([a-zA-Z0-9_-]+)/);

    if (shareMatch) {
        openSharedDemo(shareMatch[1]);
    } else if (magicToken) {
        pendingMagicToken = magicToken;
        switchPage('magic-link-page');
        document.getElementById('magic-status-box').innerText = 'Jeton detectat in URL. Apasa "Proceseaza Magic Link" pentru validare.';
    } else if (apiClient.isAuthenticated()) {
        switchPage('admin-dashboard');
    } else {
        switchPage('presentation');
    }
});

// ---------------- Autentificare Admin (PIN clasic) ----------------

async function loginAdmin() {
    const pinInput = document.getElementById('admin-pin-input');
    const pin = pinInput.value;
    if (!pin) {
        showToast('Introdu PIN-ul de securitate.');
        return;
    }
    try {
        const data = await apiClient.loginPin(pin);
        apiClient.setToken(data.access_token);
        pinInput.value = '';
        showToast('Autentificare reusita!', 'success');
        switchPage('admin-dashboard');
    } catch (err) {
        showToast(err.message || 'PIN incorect.');
    }
}

function logoutAdmin() {
    apiClient.setToken(null);
    switchPage('presentation');
}

// ---------------- F-PAS: Generare & Validare Magic Link ----------------

let pendingMagicToken = null;

async function generateMagicLink() {
    try {
        const data = await apiClient.magicGenerate();
        const url = `${window.location.origin}${window.location.pathname}?magic_token=${data.token}`;
        document.getElementById('magic-link-url').innerText = url;
        document.getElementById('magic-link-container').classList.remove('hidden');
        pendingMagicToken = data.token;
        showToast(`Link generat. Expira la ${new Date(data.expires_at).toLocaleTimeString()}.`, 'success');
    } catch (err) {
        showToast(err.message || 'Nu am putut genera Magic Link.');
    }
}

function simulateMagicClick() {
    // Simuleaza deschiderea link-ului pe alt dispozitiv (in productie, adminul chiar
    // deschide URL-ul complet cu ?magic_token=... pe celalalt dispozitiv).
    switchPage('magic-link-page');
    document.getElementById('magic-status-box').innerText = pendingMagicToken
        ? `Jeton pregatit pentru verificare. Apasa "Proceseaza Magic Link".`
        : 'Niciun jeton in asteptare.';
}

async function executeMagicAuth() {
    const statusBox = document.getElementById('magic-status-box');
    if (!pendingMagicToken) {
        statusBox.innerText = 'Eroare: niciun jeton de procesat.';
        return;
    }
    try {
        const data = await apiClient.magicVerify(pendingMagicToken);
        apiClient.setToken(data.access_token);
        statusBox.innerText = 'Jeton validat si distrus cu succes (single-use)!';
        pendingMagicToken = null;
        // Curata token-ul din URL pentru a preveni re-trimiterea accidentala.
        window.history.replaceState({}, document.title, window.location.pathname);
        setTimeout(() => {
            showToast('Autentificat cu succes prin Magic Link!', 'success');
            switchPage('admin-dashboard');
        }, 500);
    } catch (err) {
        statusBox.innerText = `Eroare: ${err.message || 'Jeton invalid sau deja utilizat.'}`;
    }
}

// ---------------- Management Fisiere ----------------

async function addNewFile() {
    const nameInput = document.getElementById('file-name-input');
    const materiaSelect = document.getElementById('file-materia-select');
    const fileInput = document.getElementById('file-upload-input');

    const materia = materiaSelect.value;
    const file = fileInput?.files?.[0];

    if (!file) {
        showToast('Selecteaza un fisier de incarcat.');
        return;
    }

    try {
        await apiClient.uploadFile({ materia, file });
        nameInput.value = '';
        if (fileInput) fileInput.value = '';
        showToast('Fisier publicat cu succes!', 'success');
        renderAdminTable();
    } catch (err) {
        showToast(err.message || 'Eroare la publicarea fisierului.');
    }
}

async function updateStatus(fileId, newStatus) {
    try {
        await apiClient.updateFileStatus(fileId, newStatus);
        showToast('Stare actualizata.', 'success');
        renderAdminTable();
    } catch (err) {
        showToast(err.message || 'Nu am putut actualiza starea (posibil link blocat definitiv).');
    }
}

async function renderAdminTable() {
    const tbody = document.getElementById('files-table-body');
    const search = document.getElementById('search-input').value;
    const filter = document.getElementById('filter-select').value;

    try {
        const items = await apiClient.listFiles({ search, status: filter });
        tbody.innerHTML = '';

        items.forEach(item => {
            const tr = document.createElement('tr');

            let badgeHtml = `<span class="badge badge-active"><svg class="icon" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg> Activ</span>`;
            if (item.status === 'paused') {
                badgeHtml = `<span class="badge badge-paused"><svg class="icon" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Anulat Temporar</span>`;
            } else if (item.status === 'blocked') {
                badgeHtml = `<span class="badge badge-blocked"><svg class="icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Blocat Definitiv</span>`;
            }

            tr.innerHTML = `
                <td>
                    <strong>${item.filename}</strong><br>
                    <small style="color: var(--text-muted);">${item.materia}</small>
                </td>
                <td>${badgeHtml}</td>
                <td><code style="color: var(--text-muted);">/share/${item.shared_code}</code></td>
                <td>
                    <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                        <button class="btn btn-outline" style="padding: 4px 8px;" onclick="openSharedDemo('${item.shared_code}')">Vizualizeaza</button>
                        ${item.status === 'active' ? `<button class="btn btn-outline" style="padding: 4px 8px;" onclick="updateStatus('${item.id}', 'paused')">Anuleaza Temp.</button>` : ''}
                        ${item.status === 'paused' ? `<button class="btn btn-outline" style="padding: 4px 8px;" onclick="updateStatus('${item.id}', 'active')">Reactiveaza</button>` : ''}
                        ${item.status !== 'blocked' ? `<button class="btn btn-outline" style="padding: 4px 8px; border-color: #555;" onclick="updateStatus('${item.id}', 'blocked')">Blocheaza Definitiv</button>` : ''}
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        showToast(err.message || 'Nu am putut incarca lista de fisiere.');
        if (err.status === 401) {
            apiClient.setToken(null);
            switchPage('admin-login');
        }
    }
}

// ---------------- Pagina Publica Shared Link ----------------

async function openSharedDemo(code) {
    switchPage('shared-link');

    const iconArea = document.getElementById('shared-status-icon');
    const titleEl = document.getElementById('shared-file-title');
    const metaEl = document.getElementById('shared-file-meta');
    const actionArea = document.getElementById('shared-action-area');

    titleEl.innerText = 'Se incarca...';
    metaEl.innerText = '';
    actionArea.innerHTML = '';
    iconArea.innerHTML = '';

    try {
        const data = await apiClient.getShareStatus(code);
        titleEl.innerText = data.filename;
        metaEl.innerText = `Materie: ${data.materia} • Cod Unic: ${code}`;

        if (data.status === 'active') {
            iconArea.innerHTML = `<svg class="icon icon-xl" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;
            actionArea.innerHTML = `<a class="btn" href="${apiClient.getDownloadUrl(code)}">Descarca Fisierul</a>`;
        } else if (data.status === 'paused') {
            iconArea.innerHTML = `<svg class="icon icon-xl" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
            actionArea.innerHTML = `<p style="font-size: 14px; color: var(--text-muted);">Accesul la acest link este <strong>anulat temporar</strong> de catre administrator.</p>`;
        } else if (data.status === 'blocked') {
            iconArea.innerHTML = `<svg class="icon icon-xl" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>`;
            actionArea.innerHTML = `<p style="font-size: 14px; color: var(--text-muted);">Acest link a fost <strong>blocat definitiv</strong> si nu mai poate fi accesat.</p>`;
        }
    } catch (err) {
        iconArea.innerHTML = `<svg class="icon icon-xl" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
        titleEl.innerText = 'Link Inexistent (404)';
        metaEl.innerText = 'Resursa solicitata nu a fost gasita pe serverul VicProj.';
    }
}
