# scripts

Scripturi pentru Windows. Se pot rula cu dublu-click sau din terminal, din orice folder.

Pentru o demonstrație nu e nevoie de nimic de aici: `start.bat` din rădăcina proiectului face toți pașii de mai jos și pornește tot. Scripturile de aici sunt pentru lucru pe bucăți.

## Prima dată

1. `install.bat` creează mediul Python (`.venv` în rădăcina proiectului) și instalează pachetele. Se rulează o singură dată și din nou doar dacă se schimbă `backend/requirements.txt`.
2. Copiezi `backend\.env.example` în `backend\.env`; valorile din el sunt suficiente pentru rulare locală. Baza de date e un fișier SQLite (`backend\vpp.db`), creat automat.
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

`run_tests.bat`, `run_experiments.bat`, `run_evaluation.bat` și `run_results.bat` merg doar cu pasul 1 făcut, nu au nevoie de backend. `run_evaluation.bat` durează câteva minute și scrie tabelele și graficele în `results\`. Aceeași evaluare pe datele reale (`backend\data\`) se face cu `python -m vpp_core.evaluation --real [--price-year 2023|2025|2026]` din `backend\` și scrie în `results\real\<an>\`; fără `--price-year` se folosesc prețurile din 2025. Studiile de sensibilitate (eroare de prognoză, cost de degradare, P2P, număr de case) se rulează cu `python -m vpp_core.sensitivity [--real --price-year <an>] [--study forecast|deg|p2p|scale]` din `backend\` și scriu în `results\sensitivity\`, respectiv `results\real\<an>\sensitivity\`. Factura pe casă și pe lună (`case.csv`, `case_luna.png`) se obține cu `python -m vpp_core.houses_report [--real --price-year <an>]`, iar comparația dintre ani (`results\real\comparatie_ani.png` și `.csv`) cu `python -m vpp_core.compare_years`, după ce există evaluarea și factura pe casă pentru anii de comparat.

`run_results.bat` reface tot folderul `results\` într-o singură rulare, în ordinea în care se sprijină pașii unii pe alții: experimentele de bază, evaluarea sintetică și pe prețurile 2023, 2025 și 2026, curbele cost / vârf (sintetic și 2025), factura pe casă pentru toate variantele, studiile de sensibilitate (sintetic, apoi pe prețurile 2025), raportul de consum și la final comparația pe ani. La sfârșit afișează cât a durat fiecare pas. Durează cam o oră pe un procesor cu multe nuclee, cea mai mare parte fiind studiul de scalare; dacă un pas eșuează, scriptul se oprește și spune la care. Se rulează după orice schimbare în model sau în `backend\data\dispozitive.csv`, ca graficele să corespundă codului.
