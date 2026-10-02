# scripts

Scripturi pentru Windows. Se pot rula cu dublu-click sau din terminal, din orice folder.

Pentru o demonstrație nu e nevoie de nimic de aici: `start.bat` din rădăcina proiectului pornește totul în Docker (vezi `README.md` din rădăcină). Scripturile de aici sunt pentru lucru pe cod, cu backend-ul rulat din `.venv`.

Baza de date este întotdeauna PostgreSQL din containerul `db` al `docker-compose.yml`. Scripturile care au nevoie de ea îl pornesc singure (`docker compose up -d db`), deci Docker Desktop trebuie să fie instalat și pornit.

## Prima dată

1. `install.bat` creează mediul Python (`.venv` în rădăcina proiectului) și instalează pachetele. Se rulează o singură dată și din nou doar dacă se schimbă `backend/requirements.txt`.
2. `seed_users.bat` creează conturile demo: `admin` (fără casă) și `user1`..`user10` (casele 1-10), toate cu parola `123` (sau cu parola dată ca argument, ori cu `DEMO_PASSWORD` din mediu). Conturile demo care există deja primesc din nou această parolă, restul datelor lor rămân neschimbate. Pentru un singur cont, cu containerul `db` pornit:

   ```
   .venv\Scripts\python.exe backend\scripts\seed.py admin nume parola
   .venv\Scripts\python.exe backend\scripts\seed.py user nume parola 3
   ```

`backend\.env` se creează din `backend\.env.example` la prima rulare a `start_backend.bat`; valorile din el sunt suficiente pentru rulare locală.

## De fiecare dată

| Script | Ce face |
|---|---|
| `start_all.bat` | același lucru ca `start.bat` din rădăcină |
| `start_backend.bat` | containerul `db` și backend-ul din `.venv` (8000); cu `--dev` repornește singur la modificări în cod |
| `start_mobile.bat` | aplicația Flutter în Chrome; are nevoie de Flutter și de backend-ul pornit |
| `seed_users.bat` | containerul `db` și conturile demo (vezi mai sus) |

Înainte de `start_backend.bat` se oprește containerul `api` (`docker compose stop api web`), ca simularea să nu ruleze de două ori pe aceeași bază de date. Documentația API e la http://localhost:8000/docs. Panoul operatorului nu mai e servit de backend: în Docker e la http://localhost:13000/admin, iar din cod se pornește din `admin/` cu `npm run dev` (vezi `README.md` din rădăcină), cu `API_TARGET=http://localhost:8000` ca să vorbească cu backend-ul din `.venv`.

## Teste

`run_tests.bat` pornește containerul `db` dacă Docker rulează și apoi toate testele. Testele API folosesc baza `vpp_test` de pe același server, creată automat dacă lipsește; ele șterg și recreează toate tabelele, de aceea numele bazei trebuie să conțină `test`, iar baza aplicației (`vpp`) nu e atinsă. Altă bază de test se alege cu variabila `TEST_DATABASE_URL`. Fără Docker rulează doar testele nucleului de simulare, iar fișierele de teste cu baza de date apar ca sărite (`skipped`, cu motivul „PostgreSQL nu ruleaza”).

## Fără bază de date

`run_experiments.bat`, `run_evaluation.bat` și `run_results.bat` merg doar cu pasul 1 făcut, fără backend și fără Docker. `run_evaluation.bat` durează câteva minute și scrie tabelele și graficele în `results\`. Aceeași evaluare pe datele reale (`backend\data\`) se face cu `python -m vpp_core.evaluation --real [--price-year 2023|2025|2026]` din `backend\` și scrie în `results\real\<an>\`; fără `--price-year` se folosesc prețurile din 2025. Studiile de sensibilitate (eroare de prognoză, cost de degradare, P2P, număr de case) se rulează cu `python -m vpp_core.sensitivity [--real --price-year <an>] [--study forecast|deg|p2p|scale]` din `backend\` și scriu în `results\sensitivity\`, respectiv `results\real\<an>\sensitivity\`. Factura pe casă și pe lună (`case.csv`, `case_luna.png`) se obține cu `python -m vpp_core.houses_report [--real --price-year <an>]`, iar comparația dintre ani (`results\real\comparatie_ani.png` și `.csv`) cu `python -m vpp_core.compare_years`, după ce există evaluarea și factura pe casă pentru anii de comparat.

`run_results.bat` reface tot folderul `results\` într-o singură rulare, în ordinea în care se sprijină pașii unii pe alții: experimentele de bază, evaluarea sintetică și pe prețurile 2023, 2025 și 2026, curbele cost / vârf (sintetic și 2025), factura pe casă pentru toate variantele, studiile de sensibilitate (sintetic, apoi pe prețurile 2025), raportul de consum și la final comparația pe ani. La sfârșit afișează cât a durat fiecare pas. Durează cam o oră pe un procesor cu multe nuclee, cea mai mare parte fiind studiul de scalare; dacă un pas eșuează, scriptul se oprește și spune la care. Se rulează după orice schimbare în model sau în `backend\data\dispozitive.csv`, ca graficele să corespundă codului.
