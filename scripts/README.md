# scripts

Scripturi pentru Windows. Se pot rula cu dublu-click sau din terminal, din orice folder.

## Prima dată

1. `install.bat` creează mediul Python (`.venv` în rădăcina proiectului) și instalează pachetele. Se rulează o singură dată și din nou doar dacă se schimbă `backend/requirements.txt`.
2. Copiezi `backend\.env.example` în `backend\.env`; valorile din el sunt suficiente pentru rulare locală. Baza de date e un fișier SQLite (`backendpp.db`), creat automat.
3. `seed_users.bat` creează conturile demo: `admin` (fără casă) și `user1`..`user10` (casele 1-10), toate cu parola `123` (sau cu parola dată ca argument). Pentru un singur cont:

   ```
   .venv\Scripts\python.exe backend\scripts\seed.py admin nume parola
   .venv\Scripts\python.exe backend\scripts\seed.py user nume parola 3
   ```

## De fiecare dată

| Script | Ce face |
|---|---|
| `start_all.bat` | pornește backend-ul (8000) într-o fereastră și aplicația Flutter în Chrome |
| `start_backend.bat` | doar backend-ul; cu `--dev` repornește singur la modificări în cod |
| `start_mobile.bat` | aplicația Flutter în Chrome; are nevoie de backend-ul pornit |
| `seed_users.bat` | conturile demo (vezi mai sus) |

Dashboard-ul se deschide în browser la http://localhost:8000 (`admin` / `123`), documentația API la http://localhost:8000/docs.

## Fără bază de date

`run_tests.bat`, `run_experiments.bat` și `run_evaluation.bat` merg doar cu pasul 1 făcut, nu au nevoie de backend. `run_evaluation.bat` durează câteva minute și scrie tabelele și graficele în `results\`. Aceeași evaluare pe datele reale din 2023 (`backend\data\`) se face cu `python -m vpp_core.evaluation --real` din `backend\` și scrie în `results\real\`. Studiile de sensibilitate (eroare de prognoză, cost de degradare, P2P, număr de case) se rulează cu `python -m vpp_core.sensitivity [--real] [--study forecast|deg|p2p|scale]` din `backend\` și scriu în `results\sensitivity\`. Factura pe casă și pe lună (`results\case.csv`, `results\case_luna.png`) se obține cu `python -m vpp_core.houses_report [--real]` din `backend\`.
