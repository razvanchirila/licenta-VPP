"""
Real input data (fetched once with --fetch into backend/data/, read offline afterwards).
Sources, licences and dates in backend/data/README.md:
    Ember   hourly day-ahead wholesale prices, Romania, EUR/MWh (CC-BY-4.0), years PRICE_YEARS
    PVGIS   hourly PV output for Bacău (46.57 N, 26.91 E), 1 kWp, 35 deg tilt, south, 14 % loss, 2023
    DEER    Electrica's 15-min household load profile weights (4 day types), ANRE order 232/2020

Time axis: local clock time (Europe/Bucharest) on a regular 365 x 24 grid: the DST gap in
March is interpolated and the duplicate hour in October averaged, so the evening price / load
peaks stay at the same clock hour all year. A price year still in progress has NaN after its
last published day.
"""
from __future__ import annotations

import argparse
import csv
import functools
import io
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
PV_CSV = DATA_DIR / "pv_bacau_2023.csv"
DEER_CSV = DATA_DIR / "load_profile_deer.csv"

YEAR = 2023                     # PV and calendar year: PVGIS-SARAH3 ends in 2023
PRICE_YEARS = (2023, 2025, 2026)
DEFAULT_PRICE_YEAR = 2025
TZ = ZoneInfo("Europe/Bucharest")
# lei/EUR, BNR: mean of the monthly average rates of the year; 2026 = January - August
EUR_RON = {2023: 4.9465, 2025: 5.0415, 2026: 5.1677}

EMBER_URL = ("https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/price/outputs/"
             "european_wholesale_electricity_price_data_hourly.zip")
PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc"
PVGIS_PARAMS = dict(lat=46.57, lon=26.91, peakpower=1, loss=14, angle=35, aspect=0,
                    startyear=YEAR - 1, endyear=YEAR, pvcalculation=1, outputformat="json",
                    raddatabase="PVGIS-SARAH3")
DEER_URL = "https://www.distributie-energie.ro/wp-content/uploads/2024/08/Ponderi-aplicabile-grafic-Casnic-Urban.xlsx"

DEER_COLUMNS = ("ZL_SC", "ZNL_SC", "ZL_SR", "ZNL_SR")   # zi lucratoare / nelucratoare, sezon cald / rece

# Romanian public holidays 2023
HOLIDAYS_2023 = {
    date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 24), date(2023, 4, 14), date(2023, 4, 16),
    date(2023, 4, 17), date(2023, 5, 1), date(2023, 6, 1), date(2023, 6, 4), date(2023, 6, 5),
    date(2023, 8, 15), date(2023, 11, 30), date(2023, 12, 1), date(2023, 12, 25), date(2023, 12, 26),
}
WARM_SEASON_MONTHS = range(4, 10)   # April - September, DEER "sezon cald"


class DataFetchError(RuntimeError):
    """Download failed or the file did not have the expected content."""


def _download(url: str, dest: Path, params: dict | None = None, timeout: int = 180) -> bytes:
    if dest.exists():
        return dest.read_bytes()
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    print(f"descarc {full}", flush=True)
    try:
        req = urllib.request.Request(full, headers={"User-Agent": "licenta-VPP/1.0 (python urllib)"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
    except Exception as error:
        raise DataFetchError(f"nu am putut descarca {full}: {error}") from error
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def prices_csv(year: int) -> Path:
    return DATA_DIR / f"prices_ro_{year}.csv"


def _local_grid(year: int = YEAR) -> list[datetime]:
    """365 x 24 naive local clock hours, no DST gap or duplicate; 29 February is left out."""
    first_hour = datetime(year, 1, 1)
    hours = (first_hour + timedelta(hours=i) for i in range(366 * 24))
    return [h for h in hours if h.year == year and (h.month, h.day) != (2, 29)]


def _regularise(
    samples: dict[datetime, list[float]], fill_missing: bool, year: int = YEAR, partial: bool = False
) -> np.ndarray:
    """samples: local clock hour -> values seen. Returns (365, 24); duplicates averaged, gaps interpolated.
    partial: the series may stop before 31 December; everything after its last whole day stays NaN."""
    grid = _local_grid(year)
    out = np.full(len(grid), np.nan)
    for i, hour in enumerate(grid):
        values = samples.get(hour)
        if values:
            out[i] = float(np.mean(values))
    n_hours = len(out)
    if partial:
        known = np.flatnonzero(~np.isnan(out))
        n_hours = (known[-1] + 1) // 24 * 24 if len(known) else 0
        if n_hours == 0:
            raise DataFetchError(f"nicio zi completa in serie pentru {year}")
        out[n_hours:] = np.nan
    head = out[:n_hours]
    missing = np.isnan(head)
    if missing.any():
        if not fill_missing:
            raise DataFetchError(f"{int(missing.sum())} ore lipsa in serie")
        index = np.arange(n_hours)
        head[missing] = np.interp(index[missing], index[~missing], head[~missing])
    return out.reshape(365, 24)


def _to_local_naive(utc: datetime) -> datetime:
    return utc.astimezone(TZ).replace(tzinfo=None)


def fetch_prices(year: int = DEFAULT_PRICE_YEAR) -> np.ndarray:
    """Ember zip -> prices_ro_<year>.csv. Returns (365, 24) lei/kWh, NaN after the last published day."""
    raw = _download(EMBER_URL, RAW_DIR / "ember_hourly.zip")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        name = next(n for n in archive.namelist() if n.endswith("Romania.csv"))
        text = archive.read(name).decode("utf-8")
    except Exception as error:
        raise DataFetchError(f"arhiva Ember nu contine Romania.csv: {error}") from error
    (RAW_DIR / "ember_romania.csv").write_text(text, encoding="utf-8")

    samples: dict[datetime, list[float]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        utc = datetime.strptime(row["Datetime (UTC)"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        local = _to_local_naive(utc)
        if local.year == year:
            samples.setdefault(local, []).append(float(row["Price (EUR/MWhe)"]))
    eur_mwh = _regularise(samples, fill_missing=True, year=year, partial=True)
    lei_kwh = eur_mwh * EUR_RON[year] / 1000
    _write_hourly_csv(prices_csv(year), ["datetime_local", "price_eur_mwh", "price_lei_kwh"],
                      [eur_mwh.ravel(), lei_kwh.ravel()], ["%.2f", "%.5f"], year)
    _read_prices.cache_clear()
    return lei_kwh


def fetch_pv() -> np.ndarray:
    """PVGIS seriescalc (UTC) -> pv_bacau_2023.csv. Returns (365, 24) kW/kWp."""
    import json
    raw = _download(PVGIS_URL, RAW_DIR / "pvgis_bacau_2022_2023.json", PVGIS_PARAMS)
    try:
        hourly = json.loads(raw)["outputs"]["hourly"]
    except Exception as error:
        raise DataFetchError(f"raspuns PVGIS neasteptat: {raw[:200]!r}") from error
    power: dict[datetime, list[float]] = {}
    irradiance: dict[datetime, list[float]] = {}
    temperature: dict[datetime, list[float]] = {}
    for row in hourly:
        utc = datetime.strptime(row["time"][:11], "%Y%m%d:%H").replace(tzinfo=UTC)   # PVGIS stamps HH:10, hour average
        local = _to_local_naive(utc)
        if local.year == YEAR:
            power.setdefault(local, []).append(float(row["P"]) / 1000)   # W per kWp -> kW per kWp
            irradiance.setdefault(local, []).append(float(row["G(i)"]))
            temperature.setdefault(local, []).append(float(row["T2m"]))
    pv = _regularise(power, fill_missing=True)
    g_i = _regularise(irradiance, fill_missing=True)
    t2m = _regularise(temperature, fill_missing=True)
    _write_hourly_csv(PV_CSV, ["datetime_local", "pv_kw_per_kwp", "g_i_w_m2", "t2m_c"],
                      [pv.ravel(), g_i.ravel(), t2m.ravel()], ["%.5f", "%.1f", "%.2f"])
    return pv


def fetch_deer() -> np.ndarray:
    """DEER XLSX -> load_profile_deer.csv. Returns (96, 4)."""
    raw = _download(DEER_URL, RAW_DIR / "deer_casnic_urban.xlsx")
    try:
        import openpyxl
    except ImportError as error:
        raise DataFetchError("openpyxl lipseste (pip install openpyxl), necesar doar pentru --fetch") from error
    workbook = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
    rows = [list(row) for row in workbook.worksheets[0].iter_rows(values_only=True)]
    weights = np.full((96, 4), np.nan)
    for row in rows:
        cells = [cell for cell in row if cell is not None]
        if len(cells) < 5:
            continue
        if isinstance(cells[0], (int, float)) and 1 <= cells[0] <= 96 and float(cells[0]).is_integer():
            try:
                weights[int(cells[0]) - 1] = [float(cell) for cell in cells[1:5]]
            except (TypeError, ValueError):
                continue
    if np.isnan(weights).any():
        raise DataFetchError("nu am recunoscut tabelul de 96 x 4 ponderi in fisierul DEER")
    if not np.allclose(weights.sum(axis=0), 1.0, atol=0.02):
        raise DataFetchError(f"ponderile DEER nu insumeaza 1 pe coloana: {weights.sum(axis=0)}")
    weights = weights / weights.sum(axis=0)
    with DEER_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["interval", *DEER_COLUMNS])
        for i in range(96):
            writer.writerow([i + 1, *(f"{x:.6f}" for x in weights[i])])
    return weights


def _write_hourly_csv(
    path: Path, header: list[str], columns: list[np.ndarray], formats: list[str], year: int = YEAR
) -> None:
    """Hours where the first column is NaN (not published yet) are not written."""
    grid = _local_grid(year)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for i, hour in enumerate(grid):
            if np.isnan(columns[0][i]):
                continue
            row_values = (fmt % col[i] for fmt, col in zip(formats, columns, strict=True))
            writer.writerow([hour.strftime("%Y-%m-%d %H:00"), *row_values])


def _read_hourly(path: Path, column: str, partial: bool = False) -> np.ndarray:
    """(365, 24): day of year x hour of day. partial: the file may stop after any whole day, the rest is NaN."""
    if not path.exists():
        raise FileNotFoundError(f"{path} lipseste; ruleaza `python -m vpp_core.data_sources --fetch`")
    with path.open(encoding="utf-8") as file:
        values = [float(row[column]) for row in csv.DictReader(file)]
    whole_days = bool(values) and len(values) % 24 == 0 and len(values) < 365 * 24
    if len(values) != 365 * 24 and not (partial and whole_days):
        raise ValueError(f"{path}: {len(values)} randuri, asteptam {365 * 24}")
    out = np.full(365 * 24, np.nan)
    out[: len(values)] = values
    return out.reshape(365, 24)


@functools.cache
def _read_prices(path: Path) -> np.ndarray:
    prices = _read_hourly(path, "price_lei_kwh", partial=True)
    prices.setflags(write=False)
    return prices


def load_prices_lei_kwh(year: int = DEFAULT_PRICE_YEAR) -> np.ndarray:
    """(365, 24) lei/kWh at EUR_RON[year], day index = day of year - 1; NaN on the days not published yet.
    The array is cached and read-only."""
    if year not in PRICE_YEARS:
        raise ValueError(f"nu exista preturi pentru {year}; ani disponibili: {PRICE_YEARS}")
    return _read_prices(prices_csv(year))


def last_price_day(year: int) -> date:
    """Last day of `year` with prices (31 December for a complete year)."""
    n_days = int(np.isfinite(load_prices_lei_kwh(year)).all(axis=1).sum())
    return date(year, 1, 1) + timedelta(days=n_days - 1)


def load_pv_kw_per_kwp() -> np.ndarray:
    """(365, 24) kW per kWp installed."""
    return _read_hourly(PV_CSV, "pv_kw_per_kwp")


def load_temperature_c() -> np.ndarray:
    """(365, 24) air temperature at 2 m, °C (PVGIS, same hours as the PV)."""
    return _read_hourly(PV_CSV, "t2m_c")


def load_irradiance_w_m2() -> np.ndarray:
    """(365, 24) irradiance on the panels' plane, W/m2."""
    return _read_hourly(PV_CSV, "g_i_w_m2")


def load_deer_weights() -> np.ndarray:
    """(96, 4) quarter-hour weights in DEER_COLUMNS order; each column sums to 1."""
    if not DEER_CSV.exists():
        raise FileNotFoundError(f"{DEER_CSV} lipseste; ruleaza `python -m vpp_core.data_sources --fetch`")
    with DEER_CSV.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    weights = np.array([[float(row[col]) for col in DEER_COLUMNS] for row in rows])
    if weights.shape != (96, 4):
        raise ValueError(f"{DEER_CSV}: forma {weights.shape}, asteptam (96, 4)")
    return weights


def deer_day_type(day: date) -> int:
    """Column index into DEER_COLUMNS."""
    working = day.weekday() < 5 and day not in HOLIDAYS_2023
    warm = day.month in WARM_SEASON_MONTHS
    return (0 if working else 1) + (0 if warm else 2)


def fetch_all() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pv = fetch_pv()
    print(f"PV Bacau 2023: {pv.sum():.0f} kWh/kWp/an, varf {pv.max():.3f} kW/kWp -> {PV_CSV}")
    for year in PRICE_YEARS:
        prices = fetch_prices(year)
        n_days = int(np.isfinite(prices).all(axis=1).sum())
        print(
            f"PZU RO {year}: {n_days} zile, medie {np.nanmean(prices):.3f} lei/kWh, min {np.nanmin(prices):.3f}, "
            f"max {np.nanmax(prices):.3f}, {int((prices < 0).sum())} ore negative -> {prices_csv(year)}"
        )
    weights = fetch_deer()
    print(f"DEER: 96 x {weights.shape[1]} ponderi, varf {weights.max(axis=0)} -> {DEER_CSV}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Date reale pentru scenariul VPP")
    parser.add_argument(
        "--fetch", action="store_true", help="descarca sursele si regenereaza CSV-urile din backend/data/"
    )
    args = parser.parse_args(argv)
    if not args.fetch:
        parser.print_help()
        return
    try:
        fetch_all()
    except DataFetchError as error:
        print(f"EROARE: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
