# VicProj

Platformă școlară de management al resurselor și distribuire securizată de fișiere, cu autentificare **F-PAS** (Magic Link Single-Use) și control granular al stărilor unui link (`active` / `paused` / `blocked`).

Stivă tehnologică:
- **Backend**: Python + FastAPI + SQLAlchemy + JWT (`python-jose`) + `passlib` (bcrypt)
- **Bază de date**: PostgreSQL (Docker) / SQLite (dev local rapid)
- **Frontend**: HTML/CSS/JS vanilla, monocrom, conectat la API prin `fetch`
- **Infra**: Docker, docker-compose, GitHub Actions

---

## 1. Structura Proiectului

```
vicproj/
├── .github/workflows/deploy.yml   # CI/CD: lint, build imagini, deploy opțional pe VPS via SSH
├── backend/
│   ├── app/
│   │   ├── api/            # auth.py, files.py, share.py
│   │   ├── core/           # config.py, database.py, security.py (JWT + F-PAS)
│   │   ├── models/         # models.py (SQLAlchemy), schemas.py (Pydantic)
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── js/api-client.js    # clasa APIClient (fetch + Bearer token)
│   ├── js/app.js           # router de pagini + logica UI
│   ├── css/styles.css
│   ├── nginx/default.conf
│   └── Dockerfile
├── docker-compose.yml       # Postgres + Backend + Frontend (Nginx)
└── README.md
```

---

## 2. Rulare Locală Rapidă (fără Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Generează hash-ul PIN-ului tău de admin și pune-l în `.env` la `ADMIN_PIN_HASH`:

```bash
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('PIN-UL-TAU'))"
```

Pornește serverul (implicit folosește SQLite local, `vicproj.db`):

```bash
uvicorn app.main:app --reload --port 8000
```

Documentația interactivă a API-ului: `http://localhost:8000/docs`

### Frontend

Fișierele din `frontend/` sunt statice — orice server simplu funcționează:

```bash
cd frontend
python -m http.server 8080
```

Deschide `http://localhost:8080`. Dacă backend-ul rulează pe alt host/port, editează în `index.html`:

```html
<script>window.VICPROJ_API_BASE_URL = 'http://localhost:8000';</script>
```

---

## 3. Rulare cu Docker Compose (recomandat pentru producție/VPS)

1. Generează hash-ul PIN-ului și un `JWT_SECRET` puternic:

   ```bash
   python -c "from passlib.hash import bcrypt; print(bcrypt.hash('PIN-UL-TAU'))"
   openssl rand -hex 32
   ```

2. Creează un fișier `.env` în rădăcina proiectului (lângă `docker-compose.yml`):

   ```env
   ADMIN_PIN_HASH=$2b$12$...hash-ul-generat-mai-sus...
   JWT_SECRET=...secretul-generat-mai-sus...
   CORS_ORIGINS=http://localhost:8080
   ```

3. Pornește totul:

   ```bash
   docker compose up -d --build
   ```

   - Backend API: `http://localhost:8000`
   - Frontend: `http://localhost:8080`
   - Postgres: expus intern doar către `backend` (nu e publicat pe host)

4. Verifică starea serviciilor:

   ```bash
   docker compose ps
   docker compose logs -f backend
   ```

> **Notă despre `ADMIN_PIN_HASH` cu `$` în `.env`**: dacă `docker compose` interpretează greșit `$` din hash-ul bcrypt, dublează fiecare `$` (`$$`) în fișierul `.env`, sau setează variabila direct în shell înainte de `docker compose up`.

---

## 4. Fluxul F-PAS (Magic Link Single-Use) — Cum Funcționează

1. Adminul, deja logat (PIN sau sesiune existentă), apasă **„Generează Jeton Unic”** în Dashboard.
2. Backend-ul (`POST /api/v1/auth/magic-generate`):
   - generează un token criptografic random (32 bytes, `secrets.token_urlsafe`);
   - salvează în DB **doar hash-ul SHA-256** al jetonului, cu `is_used=False` și `expires_at = now + 15 min` (configurabil via `MAGIC_TOKEN_EXPIRE_MINUTES`);
   - returnează jetonul în clar **o singură dată**, pentru a fi pus în URL (`?magic_token=...`).
3. Adminul deschide acel URL pe alt dispozitiv → frontend-ul detectează parametrul și afișează pagina de verificare.
4. La apăsarea „Procesează Magic Link”, frontend-ul cheamă `POST /api/v1/auth/magic-verify`, iar backend-ul:
   - caută hash-ul jetonului;
   - verifică `is_used == False` și `expires_at > now`;
   - **marchează imediat `is_used = True`** înainte de a emite JWT-ul de sesiune — astfel, orice a doua încercare cu același jeton eșuează garantat (401).

---

## 5. Stările Fișierelor Distribuite

| Stare | Efect pe `/share/{code}` | Poate fi schimbată? |
|---|---|---|
| `active` | Fișierul poate fi descărcat | Da → `paused` sau `blocked` |
| `paused` | Pagina publică arată „resursă suspendată” | Da → `active` sau `blocked` |
| `blocked` | Link dezactivat ireversibil | **Nu** — backend-ul respinge orice PATCH ulterior (409) |

---

## 6. Ghid de Deployment

### Backend → Render / Fly.io / VPS

**Render / Fly.io** (containere):
1. Conectează repo-ul GitHub în platforma aleasă.
2. Indică `backend/Dockerfile` ca sursă de build.
3. Setează variabilele de mediu: `JWT_SECRET`, `ADMIN_PIN_HASH`, `DATABASE_URL` (Postgres oferit de platformă), `CORS_ORIGINS` (domeniul frontend-ului tău).
4. Publică. Endpoint-ul va fi ceva de forma `https://vicproj-backend.onrender.com`.

**VPS propriu (Docker Compose)**:
1. `git clone` repo-ul pe server, în `/opt/vicproj`.
2. Creează `.env` cu secretele (vezi secțiunea 3).
3. `docker compose up -d --build`.
4. Recomandat: pune un reverse proxy (Nginx/Caddy/Traefik) în fața serviciilor pentru HTTPS (Let's Encrypt).

### Frontend → Netlify / GitHub Pages

1. În `frontend/index.html`, setează `VICPROJ_API_BASE_URL` cu URL-ul public al backend-ului deployat (pasul anterior).
2. **Netlify**: „New site from Git” → build command: (niciunul, sunt fișiere statice) → publish directory: `frontend`.
3. **GitHub Pages**: activează Pages pe branch-ul `main`, folder `/frontend` (sau mută conținutul într-un branch `gh-pages`).
4. Dacă vrei ca link-urile `/share/{code}` să funcționeze direct (fără hash routing), configurează un rewrite `/share/* -> /index.html` (Netlify: fișier `_redirects` cu `/share/* /index.html 200`; GitHub Pages nu suportă rewrite nativ — folosește Netlify sau un VPS cu Nginx pentru acest caz).

### CI/CD (GitHub Actions)

Workflow-ul din `.github/workflows/deploy.yml`:
1. Rulează lint + un test de „smoke import” pe backend la fiecare push/PR.
2. Construiește imaginile Docker pentru backend și frontend.
3. Opțional, face deploy pe un VPS prin SSH — activează-l setând variabila de repo `ENABLE_SSH_DEPLOY=true` și secretele `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` din **Settings → Secrets and variables → Actions**.

---

## 7. Pași Următori Recomandați

- Rulează `docker compose up -d --build` local ca să validezi tot fluxul end-to-end.
- Schimbă `JWT_SECRET` și `ADMIN_PIN_HASH` cu valori proprii, puternice — nu folosi cele din `.env.example`.
- Dacă vrei stocare de fișiere pe S3/Cloud în loc de disc local, înlocuiește logica din `backend/app/api/files.py` (`upload_file`) și `share.py` (`download_shared_file`) cu un client S3 (`boto3`), păstrând restul logicii F-PAS neschimbată.
- Pentru migrații reale de schemă (nu doar `create_all`), adaugă Alembic în backend.
- Pune HTTPS în fața API-ului (Render/Fly.io oferă asta automat; pe VPS, folosește Caddy sau Nginx + certbot).
