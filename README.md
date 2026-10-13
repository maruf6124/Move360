# Move360 — Full Frontend + FastAPI + MySQL + Gmail OTP

## Windows / XAMPP setup (Git Bash)

1. Start **MySQL** in XAMPP Control Panel. Start **Apache** if you want phpMyAdmin.
2. Open http://localhost/phpmyadmin and create a database named `move360_db` (utf8mb4_unicode_ci). **No manual tables needed**: FastAPI creates `users`, `email_otps`, `properties` on startup.
3. In VS Code open this extracted `Move360-Full-OTP-Project` folder. In Git Bash:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

4. Copy `backend/.env.example` to `backend/.env`. Set your Gmail address, Gmail App Password, and DB credentials. For `JWT_SECRET`, generate a secret by running:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the result in `JWT_SECRET`. **Never share `.env` or upload it to GitHub.** The Gmail App Password must belong to the same Gmail address used as `SMTP_EMAIL`.

5. From `backend` directory start:

```bash
python -m uvicorn main:app --reload
```

6. Open **http://127.0.0.1:8000/** (not VS Code Live Server). API docs: http://127.0.0.1:8000/docs . Health: http://127.0.0.1:8000/api/health .

7. Register -> receive OTP in Gmail -> enter OTP -> login. After verification, phpMyAdmin `users.is_verified` becomes 1. Landlord activation and newly posted properties are saved in MySQL.

## Notes

- Gmail App Password requires Google 2-Step Verification. Gmail may not offer App Passwords on some accounts.
- OTP expires in 5 minutes, has a 60-second resend cooldown and 5 incorrect attempts. New OTP invalidates old ones.
- The homepage includes 6 **sample demo properties** (not database records). New landlord properties are saved in MySQL.
- This is a local development project, not production-hardened. JWT is stored in sessionStorage; logout removes it from this browser, but existing JWTs remain valid until expiry. Production deployment needs HTTPS, stronger abuse/rate protections, secure session design, CSRF/security review, SMTP service configuration, and migrations.
- The previous localStorage-based user/password demo was removed from the new JS; old demo data in a browser's localStorage is not used for authentication.
- If Python 3.14 dependency installation fails, use Python 3.13.
