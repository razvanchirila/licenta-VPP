# Date reale

Fișierele CSV de aici sunt intrările „reale” ale simulatorului (`vpp_core/scenario_real.py`), alternative la generatorul sintetic din `vpp_core/scenario.py`. Producția PV și calendarul (sărbători, zile lucrătoare) sunt din 2023, ultimul an acoperit de seria PV din satelit (PVGIS SARAH3 se oprește la 2023). Prețurile PZU există pentru trei ani, 2023, 2025 și 2026, și se aleg cu `price_year` în `generate_scenario_real` (implicit 2025) sau cu `--price-year` la modulele de evaluare; ora `h` din ziua `z` a anului de preț se pune peste aceeași lună, zi și oră din 2023. Așa se poate compara aceeași comunitate, cu aceeași vreme, pe prețurile unor ani diferiți. Fișierele sunt mici (sub 1 MB în total) și se comit în git, ca testele și evaluarea să meargă fără internet. Fișierele brute descărcate stau în `raw/`, care este ignorat de git.

Regenerare (are nevoie de internet și de `openpyxl`, din `requirements.txt`):

```
cd backend
..\.venv\Scripts\python.exe -m vpp_core.data_sources --fetch
```

Descărcările sunt păstrate în `raw/`; pentru a lua din nou fișierele de la sursă se șterge folderul. Dacă rețeaua nu răspunde, scriptul se oprește cu un mesaj clar, nu lasă CSV-uri pe jumătate scrise.

Toate seriile orare sunt pe ora locală (Europe/București, cu ora de vară), reindexate pe o grilă regulată de 365 × 24: ora care lipsește la trecerea la ora de vară (ultima duminică din martie) e completată prin interpolare între vecine, ora dublă din ultima duminică din octombrie e mediată. Astfel fiecare zi are exact 24 de ore și vârfurile de seară (preț, consum) rămân la aceeași oră de ceas tot anul.

## prices_ro_2023.csv, prices_ro_2025.csv, prices_ro_2026.csv

Prețuri day-ahead (PZU) orare pentru România, din setul „European Wholesale Electricity Price Data” publicat de Ember (agregat din ENTSO-E). Coloane: `datetime_local`, `price_eur_mwh` (valoarea originală), `price_lei_kwh` (convertită cu cursul mediu anual BNR al anului respectiv). Cursul este media cursurilor medii lunare publicate de BNR și e constanta `EUR_RON` din `vpp_core/data_sources.py`:

| An | lei/EUR | Ore | PZU mediu | Minim / maxim | Ore cu preț negativ |
|---|---|---|---|---|---|
| 2023 | 4,9465 | 8760 (tot anul) | 0,513 lei/kWh (104 EUR/MWh) | −0,12 / 2,16 lei/kWh | 32 |
| 2025 | 5,0415 | 8760 (tot anul) | 0,545 lei/kWh (108 EUR/MWh) | −0,51 / 3,04 lei/kWh | 196 |
| 2026 | 5,1677 (ianuarie–august) | 6048 (1 ianuarie – 9 septembrie) | 0,628 lei/kWh (121 EUR/MWh) | −0,50 / 4,93 lei/kWh | 168 |

2025 e ultimul an complet și anul implicit. Fișierul 2026 se oprește la ultima zi publicată la data descărcării; zilele de după au `NaN` în `load_prices_lei_kwh(2026)`, iar un scenariu care ar cădea pe ele (de exemplu săptămâna de toamnă din 10 octombrie) se oprește cu un mesaj care spune până când există prețuri. De aceea în `results/real/2026/` lipsește toamna. Cursul pentru 2026 e media lunilor ianuarie–august, singurele publicate complet.

Orele cu preț negativ sunt păstrate ca atare. Cu formulele de mai jos importul rămâne pozitiv la orice preț peste −0,7575 lei/kWh (minimul din date e −0,51), iar exportul devine negativ, adică prosumatorul plătește ca să livreze, doar sub −0,223 lei/kWh: 10 ore în 2025 și 14 în 2026, niciuna în săptămânile simulate. Optimizarea (LP, MPC) ar limita atunci PV-ul în loc să exporte; strategiile pe reguli ar exporta și ar plăti.

- Sursă: https://ember-energy.org/data/european-wholesale-electricity-price-data/ (arhiva orară, fișierul `Romania.csv`)
- Curs: Banca Națională a României, cursurile medii lunare EUR/RON
- Licență: CC-BY-4.0 (Ember)
- Descărcat: 11.09.2026 (aceeași arhivă pentru toți anii; de aici și sfârșitul seriei 2026 pe 9 septembrie)

## pv_bacau_2023.csv

Producție PV orară simulată de PVGIS 5.3 (`seriescalc`, baza de radiație PVGIS-SARAH3) pentru Bacău, 46,57 N / 26,91 E, cu parametrii: `peakpower=1` kWp, `loss=14` %, `angle=35` grade, `aspect=0` (sud), `pvcalculation=1`. Coloane: `datetime_local`, `pv_kw_per_kwp` (puterea medie pe oră, în kW per kWp instalat; se înmulțește cu puterea fiecărei case), `g_i_w_m2` (iradianța în planul panourilor), `t2m_c` (temperatura aerului). PVGIS marchează orele în UTC la minutul 10; valoarea este luată ca media orei respective. Cererea a fost făcută pentru 2022–2023 ca să existe și primele ore ale anului 2023 în ora locală. Randamentul anual rezultat: 1232 kWh/kWp, vârf 0,91 kW/kWp.

- Sursă: https://re.jrc.ec.europa.eu/api/v5_3/seriescalc (JRC, Comisia Europeană)
- Licență: reutilizare liberă cu citarea sursei (politica de date a JRC)
- Descărcat: 11.09.2026

## load_profile_deer.csv

Ponderile profilului specific de consum „Clienți casnici zona urbană” publicat de Distribuție Energie Electrică România (DEER, grupul Electrica), conform Ordinului ANRE 232/2020. 96 de intervale de decontare de 15 minute × 4 tipuri de zi: `ZL_SC` (zi lucrătoare, sezon cald), `ZNL_SC` (zi nelucrătoare, sezon cald), `ZL_SR` și `ZNL_SR` (sezon rece). Fiecare coloană însumează 1, deci consumul unei zile se obține înmulțind ponderile cu energia zilnică a casei. În simulator sezonul cald este aprilie–septembrie, zilele nelucrătoare sunt weekendurile și sărbătorile legale din 2023 (lista este în `data_sources.py`). Zona Bacău e operată de Delgaz Grid, ale cărui profiluri sunt doar cu cod de acces; profilul DEER este public și are aceeași formă (vârf de seară la 19–21). De când consumul se construiește din lista de dispozitive (secțiunea următoare), profilul DEER rămâne varianta de comparație (`load_source="deer"` în `generate_scenario_real`) și rezerva pentru casele care nu apar în `dispozitive.csv`.

- Sursă: https://www.distributie-energie.ro/profiluri-de-consum-deer/ (fișierul `Ponderi-aplicabile-grafic-Casnic-Urban.xlsx`)
- Licență: date publice ale operatorului de distribuție, publicate prin obligație de reglementare
- Descărcat: 11.09.2026

## Consum din dispozitive (`dispozitive.csv`)

Consumul fiecărei case nu mai vine dintr-o curbă statistică, ci din lista aparatelor din casă și din felul în care sunt folosite. Fișierul `dispozitive.csv` are un rând pentru fiecare aparat din fiecare casă și este gândit să fie editat de mână: este salvat în UTF-8 cu BOM și cu separator `;`, deci Excel în română îl deschide direct cu diacritice și coloane separate (dublu-clic pe fișier; la salvare se păstrează formatul „CSV (delimitat prin virgulă)”, care în setările românești folosește tot `;`). Zecimalele se pot scrie cu virgulă sau cu punct, ambele sunt citite. Rândurile goale sunt ignorate. Codul care îl citește și construiește profilul este `vpp_core/load_model.py`.

| Coloană | Ce înseamnă |
|---|---|
| `casa` | numărul casei (1–10 în comunitatea standard); casa `i` din simulare folosește rândurile cu `casa = i` |
| `dispozitiv` | numele aparatului, text liber (apare doar în rapoarte) |
| `putere_w` | puterea medie cât timp aparatul merge, în W; pentru mașina de spălat sau de vase nu se pune puterea de pe etichetă (rezistența de 2 kW merge doar o parte din ciclu), ci energia unui ciclu împărțită la durata lui: 1 kWh în 90 de minute înseamnă 700 W |
| `mod` | `continuu`, `zilnic`, `ciclic` sau `termic` (mai jos) |
| `ore_pe_zi` | pentru `zilnic` și `termic`: ore de funcționare pe zi (la `termic`, în sezonul de vârf) |
| `cicluri_pe_saptamana`, `durata_ciclu_min` | pentru `ciclic`: câte porniri pe săptămână și cât durează una, în minute |
| `interval` | orele între care aparatul poate porni, `18-23`, `0-24` sau `22-6` (trece peste miezul nopții) |
| `sezon` | pentru `termic`: `iarna`, `vara` sau `tot_anul` |
| `flexibil` | `da` pentru aparatele care pot fi mutate sau întrerupte de VPP (mașină de spălat, de vase, uscător, boiler, mașină electrică); ele intră în `load_flex_kw`, restul în `load_crit_kw` |
| `persoane` | câte persoane locuiesc în casă, repetat pe fiecare rând al casei; deocamdată doar informativ (apare în grafice), nu scalează consumul |

Cele patru moduri:

- `continuu` – aparatul merge tot timpul la `putere_w` (frigider, congelator, router, standby);
- `zilnic` – în fiecare zi un bloc de `ore_pe_zi` ore (± 10 % aleator), pornit la o oră aleatoare din `interval` (iluminat, televizor, calculator, plită);
- `ciclic` – `cicluri_pe_saptamana` porniri pe săptămână, în zile alese aleator, fiecare de `durata_ciclu_min` minute (± 10 %), cu ora de pornire aleatoare în `interval`; ciclul poate depăși capătul intervalului (cuptor, mașină de spălat, mașină de vase, boiler, încărcarea mașinii electrice);
- `termic` – încălzire sau răcire: `ore_pe_zi` ore în sezonul lui (`sezon`), jumătate în cele două anotimpuri de tranziție și zero în anotimpul opus, împărțite în blocuri de câte jumătate de oră răspândite uniform în `interval`, cu o mică deplasare aleatoare, ca un termostat (pompă de căldură, panouri radiante, aer condiționat). Anotimpurile se iau după lună: iarnă noiembrie–martie, vară iunie–august, restul tranziție.

Regula de energie este aceeași pentru toate: un aparat de `P` W care merge `h` ore pe zi consumă în medie `P × h` Wh pe zi, deci consumul anual al unei case se poate verifica cu un calcul de mână din tabel (coloana `kwh_an_calculat` din raport) și iese la fel cu ce produce simularea. Numerele aleatoare pornesc dintr-un seed pe casă (seed-ul scenariului și numărul casei), așa că o casă are același profil indiferent câte alte case sunt simulate, iar două rulări cu același seed dau exact același consum. Blocurile care trec peste miezul nopții (interval `22-6`) sunt generate și pentru ziua dinaintea ferestrei simulate, ca prima noapte să nu fie goală.

Profilul intră în amândouă generatoarele de scenarii: `generate_scenario(..., load_source="dispozitive" | "sintetic")` și `generate_scenario_real(..., load_source="dispozitive" | "deer")`, cu `dispozitive` implicit. Producția PV și prețurile nu depind de sursa de consum (la același seed sunt identice), deci cele două surse se pot compara direct. Cele 10 case din fișier servesc și ca șabloane: `HouseParams.profile_id` spune ale cărei case aparate le are o casă (implicit propriul număr). `params.random_community`, folosit în studiul de scalare cu 10–200 de case, trage pentru fiecare casă un șablon la întâmplare dintre cele 10; numerele aleatoare vin în continuare din numărul casei simulate, deci două case cu același șablon au aceleași aparate, dar nu pornesc la aceleași ore. Doar dacă o casă nu are nici șablon, nici rânduri în fișier se folosește sursa veche, cu un singur avertisment.

Raportul de verificare se obține cu:

```
cd backend
..\.venv\Scripts\python.exe -m vpp_core.load_model
```

și scrie în `results/consum/`: `consum_case.csv` (kWh pe zi pe anotimp, kWh pe an, împărțirea pe categorii, cota flexibilă), `profil_zi.png` (profilul zilnic mediu al caselor 1, 2 și 4 în zilele lucrătoare de iarnă, cu profilul DEER scalat la aceeași energie, punctat) și `consum_anual.png` (kWh pe an pe casă, pe categorii). Cele 10 case din prima versiune a fișierului, cu consumul anual rezultat din simularea anului 2023 la pas de 15 minute:

| Casă | Cine locuiește | Ce o deosebește | kWh/zi iarnă | kWh/zi vară | kWh/an | Flexibil |
|---|---|---|---|---|---|---|
| 1 | familie, 4 persoane | plită și cuptor electrice, boiler, mașină de vase | 10,3 | 10,2 | 3743 | 43 % |
| 2 | cuplu, 2 persoane | pompă de căldură 2,5 kW, 5,5 h/zi iarna | 18,7 | 5,0 | 4735 | 9 % |
| 3 | familie, 5 persoane | două aparate de aer condiționat vara | 10,5 | 17,7 | 4924 | 31 % |
| 4 | familie, 3 persoane | mașină electrică, 3 încărcări pe săptămână noaptea (7 kW, 2 h) | 13,3 | 13,5 | 4845 | 69 % |
| 5 | familie, 3 persoane | panouri radiante electrice 3 kW, 4 h/zi iarna | 18,2 | 6,1 | 4793 | 15 % |
| 6 | cuplu tânăr, 2 persoane | apartament mic, plecați ziua, aer condiționat mic | 4,5 | 7,2 | 2054 | 23 % |
| 7 | pensionari, 2 persoane | acasă ziua, televizor mult, radiator electric iarna | 12,6 | 8,1 | 3908 | 18 % |
| 8 | familie, 4 persoane | uscător de rufe și aer condiționat | 11,1 | 14,8 | 4616 | 41 % |
| 9 | familie, 3 persoane | birou acasă: calculator 9 h/zi, aer condiționat în birou | 9,3 | 14,2 | 4151 | 26 % |
| 10 | doi tineri | plecați ziua, consum doar seara, radiator mic | 6,4 | 4,4 | 2038 | 23 % |

Media pe casă este 3981 kWh pe an, iar iarna 11,5 kWh pe zi, foarte aproape de cei 11,4–12,2 kWh pe zi pe care îi dădea profilul DEER scalat la 3000–4500 kWh pe an, deci rezultatele vechi ale evaluării rămân comparabile ca ordin de mărime. Ce se schimbă este forma: vârful de seară e mai ascuțit decât în profilul DEER (care e o medie pe mii de clienți), casele cu încălzire electrică au iarna dublu față de vară, iar partea flexibilă are acum un sens fizic (aparatele marcate `da`), nu o împărțire fixă între o bază constantă și rest.

## Tarif și prosumatori

Componentele tarifului final sunt constante în `scenario_real.py` și sunt valorile din 2026, aplicate la fel peste PZU din oricare an (2023, 2025 sau 2026). Prețurile din simulare sunt deci „anul de piață X cu structura de tarif de azi”, nu factura efectivă din acel an: în 2023 și în prima jumătate a lui 2025 prețul casnic era plafonat, iar tarifele de rețea s-au schimbat de mai multe ori între timp. Diferențele dintre ani din `results/real/` vin astfel numai din PZU și din cursul de schimb.

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

Valoarea este `LPWeights.deg_cost` din `vpp_core/optimizer.py`, penalizarea pe fiecare kWh încărcat sau descărcat cu care LP-ul și MPC-ul decid dacă merită să folosească bateria. Valori mai mari, de exemplu 0,45 lei/kWh, apar în literatură din prețuri de retail din alte țări și sunt folosite în studiul de sensibilitate doar ca margine superioară.

### Module și invertor

În simulator (`vpp_core/params.py`, funcția `deye_se_f16`) o casă are 0, 1 sau 2 module SE-F16 legate în paralel:

| Module | Capacitate | SOC minim | Încărcare / descărcare | Ce limitează puterea |
|---|---|---|---|---|
| 1 | 16 kWh | 10 % (1,6 kWh) | 8 kW / 8 kW | curentul de încărcare al modulului: 160 A × 51,2 V ≈ 8,2 kW |
| 2 | 32 kWh | 10 % (3,2 kWh) | 10 kW / 10 kW | portul de baterie al invertorului hibrid de 10 kW |

Descărcarea unui singur modul ar permite 230 A (≈ 11,8 kW), dar se păstrează 8 kW în ambele sensuri: fișa recomandă același curent (157 A) la încărcare și descărcare, iar invertorul de 10 kW nu ar trece oricum mai mult; diferența 8 / 10 kW la descărcare nu ar schimba rezultatele. Randamentul este 95 % pe fiecare sens (≈ 90 % dus-întors). Comunitatea standard din evaluare are 10 case cu câte 10 kWp: 2 fără baterie, 5 cu un modul și 3 cu două (176 kWh în total).

Fiecare casă are un invertor hibrid de 10 kW (`HouseParams.inverter_kw`), care limitează puterea netă în curent alternativ a casei, în ambele sensuri, la fiecare pas de timp:

```
(PV - PV limitat) + descărcare - încărcare <= 10 kW
încărcare - descărcare - (PV - PV limitat) <= 10 kW
```

Regula este impusă în programul liniar (două rânduri pe casă și pas), verificată de simulator (`DispatchError` la orice depășire) și respectată de controlerul pe reguli. Consecința practică: o casă nu poate trimite în rețea PV plus baterie peste 10 kW, chiar dacă bateria ar mai avea putere; vârful PV (până la 9,1 kW pe 10 kWp în datele PVGIS) trece singur prin invertor, dar nu împreună cu descărcarea.
