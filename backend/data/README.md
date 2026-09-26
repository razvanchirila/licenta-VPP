# Date reale 2023

Fișierele CSV de aici sunt intrările „reale” ale simulatorului (`vpp_core/scenario_real.py`), alternative la generatorul sintetic din `vpp_core/scenario.py`. Toate acoperă anul 2023, singurul an pentru care există simultan prețuri PZU orare și seria PV din satelit (PVGIS SARAH3 se oprește la 2023). Sunt mici (sub 1 MB în total) și se comit în git, ca testele și evaluarea să meargă fără internet. Fișierele brute descărcate stau în `raw/`, care este ignorat de git.

Regenerare (are nevoie de internet și de `openpyxl`, din `requirements.txt`):

```
cd backend
..\.venv\Scripts\python.exe -m vpp_core.data_sources --fetch
```

Descărcările sunt păstrate în `raw/`; pentru a lua din nou fișierele de la sursă se șterge folderul. Dacă rețeaua nu răspunde, scriptul se oprește cu un mesaj clar, nu lasă CSV-uri pe jumătate scrise.

Toate seriile orare sunt pe ora locală (Europe/București, cu ora de vară), reindexate pe o grilă regulată de 365 × 24: ora care lipsește pe 26 martie e completată prin interpolare între vecine, ora dublă din 29 octombrie e mediată. Astfel fiecare zi are exact 24 de ore și vârfurile de seară (preț, consum) rămân la aceeași oră de ceas tot anul.

## prices_ro_2023.csv

Prețuri day-ahead (PZU) orare pentru România, din setul „European Wholesale Electricity Price Data” publicat de Ember (agregat din ENTSO-E). Coloane: `datetime_local`, `price_eur_mwh` (valoarea originală), `price_lei_kwh` (convertită cu cursul mediu anual BNR 2023, 4,9465 lei/EUR). Media anuală este 0,513 lei/kWh (≈ 104 EUR/MWh); există 32 de ore cu preț negativ, păstrate ca atare.

- Sursă: https://ember-energy.org/data/european-wholesale-electricity-price-data/ (arhiva orară, fișierul `Romania.csv`)
- Licență: CC-BY-4.0
- Descărcat: 11.09.2026

## pv_bacau_2023.csv

Producție PV orară simulată de PVGIS 5.3 (`seriescalc`, baza de radiație PVGIS-SARAH3) pentru Bacău, 46,57 N / 26,91 E, cu parametrii: `peakpower=1` kWp, `loss=14` %, `angle=35` grade, `aspect=0` (sud), `pvcalculation=1`. Coloane: `datetime_local`, `pv_kw_per_kwp` (puterea medie pe oră, în kW per kWp instalat; se înmulțește cu puterea fiecărei case), `g_i_w_m2` (iradianța în planul panourilor), `t2m_c` (temperatura aerului). PVGIS marchează orele în UTC la minutul 10; valoarea este luată ca media orei respective. Cererea a fost făcută pentru 2022–2023 ca să existe și primele ore ale anului 2023 în ora locală. Randamentul anual rezultat: 1232 kWh/kWp, vârf 0,91 kW/kWp.

- Sursă: https://re.jrc.ec.europa.eu/api/v5_3/seriescalc (JRC, Comisia Europeană)
- Licență: reutilizare liberă cu citarea sursei (politica de date a JRC)
- Descărcat: 11.09.2026

## load_profile_deer.csv

Ponderile profilului specific de consum „Clienți casnici zona urbană” publicat de Distribuție Energie Electrică România (DEER, grupul Electrica), conform Ordinului ANRE 232/2020. 96 de intervale de decontare de 15 minute × 4 tipuri de zi: `ZL_SC` (zi lucrătoare, sezon cald), `ZNL_SC` (zi nelucrătoare, sezon cald), `ZL_SR` și `ZNL_SR` (sezon rece). Fiecare coloană însumează 1, deci consumul unei zile se obține înmulțind ponderile cu energia zilnică a casei. În simulator sezonul cald este aprilie–septembrie, zilele nelucrătoare sunt weekendurile și sărbătorile legale din 2023 (lista este în `data_sources.py`). Zona Bacău e operată de Delgaz Grid, ale cărui profiluri sunt doar cu cod de acces; profilul DEER este public și are aceeași formă (vârf de seară la 19–21).

- Sursă: https://www.distributie-energie.ro/profiluri-de-consum-deer/ (fișierul `Ponderi-aplicabile-grafic-Casnic-Urban.xlsx`)
- Licență: date publice ale operatorului de distribuție, publicate prin obligație de reglementare
- Descărcat: 11.09.2026

## Tarif și prosumatori

Componentele tarifului final sunt constante în `scenario_real.py` și sunt valorile din 2025–2026, aplicate peste PZU 2023. Prețurile din simulare sunt deci „anul de piață 2023 cu structura de tarif de azi”, nu factura efectivă din 2023, care era plafonată.

Valori pentru zona Delgaz Grid (Bacău), lei/kWh fără TVA, din oferta Electrica Furnizare pentru prosumatori (martie 2026):

| Componentă | lei/kWh |
|---|---|
| Energie activă (achiziție + marjă furnizor) | 0,759 |
| Transport | 0,036 |
| Servicii de sistem | 0,015 |
| Distribuție JT Delgaz Grid | 0,388 |
| Certificate verzi | 0,074 |
| Cogenerare | 0,014 |
| Acciză | 0,008 |
| Total fără TVA | 1,294 |
| Cu TVA 21% | 1,566 |

Formula din simulator: `import = (PZU + marjă 0,223 + tarife de rețea 0,535) × 1,21`, după modelul ofertelor cu preț dinamic (Hidroelectrica „Hidro DINAMIC C”, ianuarie 2025). Tarifele de transport și servicii de sistem: https://www.transelectrica.ro/ro/web/tel/tarife (Ordinele ANRE 73/2026 și 74/2026); distribuție: https://delgaz.ro/energie-electrica/tarife-distributie. Niciun tarif casnic nu are componentă de putere (kW).

Prosumatori (https://anre.ro/qa-despre-prosumatori-dupa-1-iulie-2025/): sub 200 kW se aplică compensarea cantitativă lunară, iar surplusul rămas se plătește la prețul energiei active din contract, fără tarife de rețea. În simulator, `export = PZU + 0,223`, adică regula luată la nivel orar. Alternativa `export_rule="pzu"` corespunde regimului peste 200 kW. Legea 160/2026 cere stocare pentru prosumatorii peste 10,8 kW începând cu 2027.

## Baterie

Parametrii bateriei urmează fișa tehnică Deye SE-F16 (LiFePO4, 16 kWh, 51,2 V, DoD recomandat 90%, încărcare 160 A, descărcare 230 A, cel puțin 6000 de cicluri la 70% EOL, garanție 10 ani sau 50 MWh energie tranzitată), preț de listă 10.010 lei (ofertă din România, septembrie 2026). Costul de degradare pe kWh trecut prin baterie:

```
c_deg = preț / energie garantată = 10.010 lei / 50.000 kWh = 0,20 lei/kWh
```

Calculul din cicluri, 10.010 / (6000 × 16 × 0,9), dă 0,12 lei/kWh; se folosește valoarea prudentă din garanție. Metoda: He et al., „Power System Dispatch with Marginal Degradation Cost of Battery Storage”, IEEE Transactions on Power Systems, 2020.
