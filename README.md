# licenta-VPP

[![CI](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml/badge.svg)](https://github.com/razvanchirila/licenta-VPP/actions/workflows/ci.yml)

Centrală electrică virtuală (VPP) pentru o comunitate de 10 case cu panouri fotovoltaice și baterii. Proiect de licență.

```
backend/   simulare, optimizare (LP, MPC) și API (FastAPI, PostgreSQL)
admin/     panoul operatorului (React)
mobile/    aplicația utilizatorilor (Flutter)
web/       nginx pentru aplicație și panou
deploy/    serverul
scripts/   scripturi Windows
```

## Pornire

Cu Docker Desktop instalat: `start.bat`.

| | Adresă | Cont |
|---|---|---|
| Aplicația | http://localhost:13000 | `user1` / `123` |
| Panoul operatorului | http://localhost:13000/admin | `admin` / `123` |
| API | http://localhost:18000/docs | |

`start.bat --reset` pornește cu o bază de date nouă.

## Online

- https://vpp-licenta.switzerlandnorth.cloudapp.azure.com
- staging: https://staging.51.107.88.91.nip.io
