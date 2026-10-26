# Date

Datele reale folosite de simulator. Se regenerează cu:

```
python -m vpp_core.data_sources --fetch
```

| Fișier | Conținut | Sursă |
|---|---|---|
| `prices_ro_2023/2025/2026.csv` | prețuri PZU orare | [Ember](https://ember-energy.org/data/european-wholesale-electricity-price-data/), CC-BY-4.0 |
| `pv_bacau_2023.csv` | producție PV orară, Bacău | [PVGIS, JRC](https://re.jrc.ec.europa.eu/) |
| `load_profile_deer.csv` | profil de consum casnic | [Distribuție Energie Electrică România](https://www.distributie-energie.ro/profiluri-de-consum-deer/) |
| `dispozitive.csv` | catalogul de dispozitive: cine le are, tip, putere, program | `surse.csv` |
| `case.csv` | cele 10 case: persoane, acasă ziua, încălzire, dispozitive | propriu |
| `surse.csv` | sursa fiecărei valori din `dispozitive.csv` (coloana `sursa`) | |

Prețul de import: `(PZU + 0,223 + 0,535) × 1,21` lei/kWh, după tarifele din 2026. Bateria: Deye SE-F16, 16 kWh pe modul, cost de uzură 0,20 lei/kWh.
