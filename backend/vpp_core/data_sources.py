"""
Real 2023 input data (fetched once with --fetch into backend/data/, read offline afterwards).
Sources, licences and dates in backend/data/README.md:
    Ember   hourly day-ahead wholesale prices, Romania, EUR/MWh (CC-BY-4.0)
    PVGIS   hourly PV output for Bacău (46.57 N, 26.91 E), 1 kWp, 35 deg tilt, south, 14 % loss
    DEER    Electrica's 15-min household load profile weights (4 day types), ANRE order 232/2020

Time axis: local clock time (Europe/Bucharest) on a regular 365 x 24 grid: the DST gap on
26 March is interpolated and the duplicate hour on 29 October averaged, so the evening
price / load peaks stay at the same clock hour all year.
"""
from __future__ import annotations

import argparse
import csv
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
PRICES_CSV = DATA_DIR / "prices_ro_2023.csv"
PV_CSV = DATA_DIR / "pv_bacau_2023.csv"
DEER_CSV = DATA_DIR / "load_profile_deer.csv"

YEAR = 2023
TZ = ZoneInfo("Europe/Bucharest")
EUR_RON_2023 = 4.9465          # BNR annual average rate 2023 (lei/EUR)

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


def _local_grid() -> list[datetime]:
    """365 x 24 naive local clock hours, no DST gap or duplicate."""
    first_hour = datetime(YEAR, 1, 1)
    return [first_hour + timedelta(hours=i) for i in range(365 * 24)]


def _regularise(samples: dict[datetime, list[float]], fill_missing: bool) -> np.ndarray:
    """samples: local clock hour -> values seen. Returns (365, 24); duplicates averaged, gaps interpolated."""
    grid = _local_grid()
    out = np.full(len(grid), np.nan)
    for i, hour in enumerate(grid):
        values = samples.get(hour)
        if values:
            out[i] = float(np.mean(values))
    missing = np.isnan(out)
    if missing.any():
        if not fill_missing:
            raise DataFetchError(f"{int(missing.sum())} ore lipsa in serie")
        index = np.arange(len(out))
        out[missing] = np.interp(index[missing], index[~missing], out[~missing])
    return out.reshape(365, 24)


def _to_local_naive(utc: datetime) -> datetime:
    return utc.astimezone(TZ).replace(tzinfo=None)


def fetch_prices() -> np.ndarray:
    """Ember zip -> prices_ro_2023.csv. Returns (365, 24) lei/kWh."""
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
        if local.year == YEAR:
            samples.setdefault(local, []).append(float(row["Price (EUR/MWhe)"]))
    eur_mwh = _regularise(samples, fill_missing=True)
    lei_kwh = eur_mwh * EUR_RON_2023 / 1000
    _write_hourly_csv(PRICES_CSV, ["datetime_local", "price_eur_mwh", "price_lei_kwh"],
                      [eur_mwh.ravel(), lei_kwh.ravel()], ["%.2f", "%.5f"])
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
        is_valid_index = isinstance(cells[0], (int, float)) and 1 <= cells[0] <= 96 and float(cells[0]).is_integer()
        if len(cells) >= 5 and is_valid_index:
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


def _write_hourly_csv(path: Path, header: list[str], columns: list[np.ndarray], formats: list[str]) -> None:
    grid = _local_grid()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for i, hour in enumerate(grid):
            row_values = (fmt % col[i] for fmt, col in zip(formats, columns, strict=True))
            writer.writerow([hour.strftime("%Y-%m-%d %H:00"), *row_values])


def _read_hourly(path: Path, column: str) -> np.ndarray:
    """(365, 24): day of year x hour of day."""
    if not path.exists():
        raise FileNotFoundError(f"{path} lipseste; ruleaza `python -m vpp_core.data_sources --fetch`")
    with path.open(encoding="utf-8") as file:
        values = [float(row[column]) for row in csv.DictReader(file)]
    if len(values) != 365 * 24:
        raise ValueError(f"{path}: {len(values)} randuri, asteptam {365 * 24}")
    return np.array(values).reshape(365, 24)


def load_prices_lei_kwh() -> np.ndarray:
    """(365, 24) lei/kWh, day index = day of year - 1."""
    return _read_hourly(PRICES_CSV, "price_lei_kwh")


def load_pv_kw_per_kwp() -> np.ndarray:
    """(365, 24) kW per kWp installed."""
    return _read_hourly(PV_CSV, "pv_kw_per_kwp")


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
    prices = fetch_prices()
    print(
        f"PZU RO 2023: medie {prices.mean():.3f} lei/kWh, min {prices.min():.3f}, "
        f"max {prices.max():.3f} -> {PRICES_CSV}"
    )
    weights = fetch_deer()
    print(f"DEER: 96 x {weights.shape[1]} ponderi, varf {weights.max(axis=0)} -> {DEER_CSV}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Date reale 2023 pentru scenariul VPP")
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
