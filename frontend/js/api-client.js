/**
 * APIClient - modul central pentru comunicarea cu backend-ul VicProj.
 * Gestioneaza URL-ul de baza, header-ul Authorization (Bearer JWT)
 * si aruncarea unor erori uniforme (consumate de toast-uri in app.js).
 */
class APIClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.token = localStorage.getItem('vicproj_token') || null;
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('vicproj_token', token);
        } else {
            localStorage.removeItem('vicproj_token');
        }
    }

    isAuthenticated() {
        return !!this.token;
    }

    async _request(method, path, { body, isForm = false, auth = true } = {}) {
        const headers = {};
        if (!isForm) headers['Content-Type'] = 'application/json';
        if (auth && this.token) headers['Authorization'] = `Bearer ${this.token}`;

        const res = await fetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: isForm ? body : (body ? JSON.stringify(body) : undefined),
        });

        let data = null;
        try {
            data = await res.json();
        } catch (_) {
            data = null;
        }

        if (!res.ok) {
            const message = (data && (data.error || data.detail)) || `Eroare server (${res.status})`;
            const err = new Error(message);
            err.status = res.status;
            throw err;
        }
        return data;
    }

    // ---------- Auth ----------
    loginPin(pin) {
        return this._request('POST', '/api/v1/auth/login-pin', { body: { pin }, auth: false });
    }

    magicGenerate() {
        return this._request('POST', '/api/v1/auth/magic-generate', {});
    }

    magicVerify(token) {
        return this._request('POST', '/api/v1/auth/magic-verify', { body: { token }, auth: false });
    }

    // ---------- Files (Admin) ----------
    listFiles({ search = '', status = 'all' } = {}) {
        const params = new URLSearchParams();
        if (search) params.set('search', search);
        if (status && status !== 'all') params.set('status_filter', status);
        const qs = params.toString();
        return this._request('GET', `/api/v1/files${qs ? `?${qs}` : ''}`, {});
    }

    uploadFile({ materia, file }) {
        const form = new FormData();
        form.append('materia', materia);
        form.append('file', file);
        return this._request('POST', '/api/v1/files/upload', { body: form, isForm: true });
    }

    updateFileStatus(fileId, newStatus) {
        return this._request('PATCH', `/api/v1/files/${fileId}/status`, { body: { status: newStatus } });
    }

    // ---------- Share (Public) ----------
    getShareStatus(code) {
        return this._request('GET', `/api/v1/share/${code}`, { auth: false });
    }

    getDownloadUrl(code) {
        return `${this.baseUrl}/api/v1/share/${code}/download`;
    }
}

// Configureaza aici URL-ul backend-ului (schimba pentru productie / docker-compose).
const API_BASE_URL = window.VICPROJ_API_BASE_URL || 'http://localhost:8000';
const apiClient = new APIClient(API_BASE_URL);
