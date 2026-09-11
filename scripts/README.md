# scripts

Scripturi pentru Windows. Se pot rula cu dublu-click sau din terminal, din orice folder.

## Prima dată

1. `install.bat` creează mediul Python (`.venv` în rădăcina proiectului) și instalează pachetele. Se rulează o singură dată și din nou doar dacă se schimbă `backend/requirements.txt`.
2. Copiezi `backend\.env.example` în `backend\.env` și completezi parola de MySQL și `JWT_SECRET_KEY`.
3. Pornești MySQL, apoi `start_backend.bat` o dată. La prima pornire se creează baza de date, tabelele și cele 10 case.
4. Creezi conturile de utilizator (cu backend-ul pornit sau oprit, nu contează):

   ```
   .venv\Scripts\python.exe backend\scripts\seed_admin.py
   .venv\Scripts\python.exe backend\scripts\seed_users.py
   ```

   Numele de utilizator și parolele implicite sunt în cele două scripturi.

## De fiecare dată

| Script | Ce face |
|---|---|
| `start_all.bat` | pornește backend-ul (8000) și API-ul de utilizatori (8001) în două ferestre |
| `start_backend.bat` | doar backend-ul; cu `--dev` repornește singur la modificări în cod |
| `start_user_api.bat` | doar API-ul de utilizatori |
| `start_mobile.bat` | aplicația Flutter în Chrome; are nevoie de `start_all.bat` pornit |

Dashboard-ul se deschide în browser la http://localhost:8000.

## Fără bază de date

`run_tests.bat` și `run_experiments.bat` merg doar cu pasul 1 făcut, nu au nevoie de MySQL.
