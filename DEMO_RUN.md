# Chopp Mineiro Mobile Demo Runbook

## 1. Start Backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Test:

```text
http://127.0.0.1:8000/docs
```

## 2. Start Frontend

```powershell
cd frontend
python -m http.server 5500
```

Local staff panel:

```text
http://127.0.0.1:5500/staff-painel/
```

## 3. Start Public Tunnels

Backend tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Frontend tunnel:

```powershell
cloudflared tunnel --url http://127.0.0.1:5500
```

Copy both `https://...trycloudflare.com` URLs.

## 4. Open Demo URLs

```text
FRONTEND_URL/staff-painel/?api_base_url=BACKEND_URL
FRONTEND_URL/admin-dashboard/?api_base_url=BACKEND_URL
```

Example:

```text
https://frontend.trycloudflare.com/staff-painel/?api_base_url=https%3A%2F%2Fbackend.trycloudflare.com
```

The bottom-right badge must show the backend URL.

## 5. Mobile Flow Test

1. Open staff panel public URL.
2. Open a tab.
3. Copy/open the generated customer session link on the phone.
4. Add order to cart from staff panel and confirm order.
5. Mark order delivered.
6. Request close from customer/session view.
7. Confirm close and close tab from staff panel.
8. Open owner dashboard public URL and confirm summary updates.

## Notes

- Local development works without `?api_base_url=`.
- Public demo must use `?api_base_url=BACKEND_URL`.
- Switching backend URLs requires only changing the URL.
- No API URL is stored in `localStorage`, `sessionStorage`, or cookies.
