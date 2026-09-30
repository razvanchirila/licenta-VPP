"""Real-data scenario: works offline from the CSVs committed in backend/data/."""
from datetime import date, timedelta

import numpy as np
import pytest

from vpp_core import data_sources as ds
from vpp_core.experiments import baseline_controllers
from vpp_core.metrics import compute_metrics
from vpp_core.optimizer import LPController, MPCController
from vpp_core.params import default_community
from vpp_core.reporting import make_scenario, seasons_with_prices
from vpp_core.scenario_real import (
    NETWORK_ADDER,
    SUPPLY_MARGIN,
    VAT,
    generate_scenario_real,
    repeat_hourly,
    resample_hourly,
)
from vpp_core.simulator import simulate

C = default_community()


# ----------------------------------------------------------------------------- committed CSVs

def test_prices_csv_shape_and_range():
    p = ds.load_prices_lei_kwh(2023)
    assert p.shape == (365, 24)
    assert 0.35 < p.mean() < 0.75          # 2023 RO day-ahead average ~ 100 EUR/MWh
    assert p.min() > -0.5 and p.max() < 3.0
    assert (p < 0).sum() < 100             # a few negative hours exist in 2023, not many


def test_price_years_and_default():
    assert ds.PRICE_YEARS == (2023, 2025, 2026) and ds.DEFAULT_PRICE_YEAR == 2025
    assert set(ds.EUR_RON) == set(ds.PRICE_YEARS)
    np.testing.assert_array_equal(ds.load_prices_lei_kwh(), ds.load_prices_lei_kwh(2025))
    with pytest.raises(ValueError, match="2024"):
        ds.load_prices_lei_kwh(2024)
    with pytest.raises(ValueError):                      # cached array, shared by every caller
        ds.load_prices_lei_kwh(2025)[0, 0] = 1.0


def test_prices_2025_full_year():
    p = ds.load_prices_lei_kwh(2025)
    assert p.shape == (365, 24) and np.isfinite(p).all()
    assert ds.last_price_day(2025) == date(2025, 12, 31)
    assert 0.35 < p.mean() < 0.80
    assert 100 < (p < 0).sum() < 500        # midday negative prices are common by 2025
    assert p.min() > -0.7575                # never low enough to make the import price negative


def test_prices_2026_stop_in_september():
    p = ds.load_prices_lei_kwh(2026)
    last = ds.last_price_day(2026)
    assert date(2026, 9, 1) <= last < date(2026, 12, 31)
    n_days = last.timetuple().tm_yday
    assert np.isfinite(p[:n_days]).all() and np.isnan(p[n_days:]).all()
    assert 0.35 < np.nanmean(p) < 0.90
    assert ds.last_price_day(2023) == date(2023, 12, 31)


def test_partial_price_file_round_trip(tmp_path):
    path = tmp_path / "prices.csv"
    values = np.full(365 * 24, np.nan)
    values[: 3 * 24] = np.arange(72) / 100
    ds._write_hourly_csv(path, ["datetime_local", "price_lei_kwh"], [values], ["%.5f"], 2026)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 + 72 and lines[1].startswith("2026-01-01 00:00") and lines[-1].startswith("2026-01-03 23:00")
    back = ds._read_hourly(path, "price_lei_kwh", partial=True)
    assert np.allclose(back[:3].ravel(), values[:72]) and np.isnan(back[3:]).all()
    with pytest.raises(ValueError):
        ds._read_hourly(path, "price_lei_kwh")


def test_regularise_partial_year_keeps_whole_days_only():
    grid = ds._local_grid(2026)
    assert len(grid) == 365 * 24 and len(ds._local_grid(2024)) == 365 * 24      # 29 February left out
    samples = {hour: [1.0] for hour in grid[: 2 * 24 + 5]}
    del samples[grid[30]]
    out = ds._regularise(samples, fill_missing=True, year=2026, partial=True)
    assert np.allclose(out[:2], 1.0) and np.isnan(out[2:]).all()


def test_pv_csv_shape_and_annual_yield():
    pv = ds.load_pv_kw_per_kwp()
    assert pv.shape == (365, 24)
    assert (pv >= 0).all() and pv.max() < 1.0
    assert 1100 < pv.sum() < 1300           # kWh/kWp/year, PVGIS Bacau 35 deg south
    assert np.allclose(pv[:, [0, 1, 2, 23]], 0)          # night
    assert pv[150:240].sum() > 3 * pv[:45].sum()         # summer >> January


def test_deer_weights():
    w = ds.load_deer_weights()
    assert w.shape == (96, 4)
    assert (w > 0).all()
    assert np.allclose(w.sum(axis=0), 1.0, atol=1e-3)
    peak = w.argmax(axis=0)
    assert (peak >= 68).all() and (peak <= 88).all()     # evening peak, 17:00 - 22:00


def test_day_type():
    assert ds.deer_day_type(date(2023, 7, 10)) == 0       # Monday, warm
    assert ds.deer_day_type(date(2023, 7, 9)) == 1        # Sunday, warm
    assert ds.deer_day_type(date(2023, 1, 10)) == 2       # Tuesday, cold
    assert ds.deer_day_type(date(2023, 1, 24)) == 3       # public holiday, cold


# ----------------------------------------------------------------------------- resampling

def test_resample_hourly_preserves_energy_and_is_smooth():
    x = np.random.default_rng(0).uniform(0, 1, (3, 24))
    y = resample_hourly(x, 0.25)
    assert y.shape == (3 * 96,)
    assert np.allclose(y.reshape(-1, 4).mean(axis=1), x.ravel())
    assert (y >= 0).all()
    assert np.allclose(resample_hourly(x, 1.0), x.ravel())
    assert np.allclose(resample_hourly(x, 2.0), x.reshape(-1, 2).mean(axis=1))
    assert np.allclose(repeat_hourly(x, 0.5), np.repeat(x.ravel(), 2))


# ----------------------------------------------------------------------------- scenario

def test_real_scenario_shapes_and_signs():
    s = generate_scenario_real(C, start=date(2023, 4, 10), n_days=3, dt_h=0.25, seed=1)
    assert s.pv_kw.shape == (10, 288) and s.price_import.shape == (288,)
    assert (s.pv_kw >= 0).all() and (s.load_kw > 0).all()
    assert (s.price_import > s.price_export).all()
    assert np.allclose(s.price_p2p, 0.7 * s.price_import)
    assert s.pv_kw.max() < 10.0


def test_same_seed_same_scenario_and_seeds_differ():
    a = generate_scenario_real(C, seed=3, n_days=2)
    b = generate_scenario_real(C, seed=3, n_days=2)
    np.testing.assert_array_equal(a.pv_kw, b.pv_kw)
    np.testing.assert_array_equal(a.load_flex_kw, b.load_flex_kw)
    assert not np.array_equal(a.load_flex_kw, generate_scenario_real(C, seed=4, n_days=2).load_flex_kw)


def test_pv_follows_pvgis_per_kwp():
    s = generate_scenario_real(C, start=date(2023, 6, 1), n_days=10, dt_h=0.25, seed=0)
    ref = ds.load_pv_kw_per_kwp()[151:161].sum() * 10          # kWh over 10 days per house
    per_house = s.pv_kw.sum(axis=1) * s.dt_h
    assert (per_house > 0.9 * ref).all() and (per_house < 1.06 * ref).all()


def test_annual_pv_yield_bacau():
    s = generate_scenario_real(C, start=date(2023, 1, 1), n_days=365, dt_h=1.0, seed=0)
    per_kwp = s.pv_kw.sum(axis=1) * s.dt_h / 10.0
    assert (per_kwp > 1000).all() and (per_kwp < 1350).all()
    assert 1100 < per_kwp.mean() / 0.985 < 1300         # undo the mean orientation scale


def test_daily_load_energy_matches_target():
    """DEER source: every day's energy is exactly the house's daily target (annual / 365 x seasonal factor)."""
    s = generate_scenario_real(C, start=date(2023, 3, 20), n_days=5, dt_h=0.25, seed=2,
                               annual_kwh_lo=3650, annual_kwh_hi=3650, load_source="deer")
    daily = s.load_kw.reshape(10, 5, 96).sum(axis=2) * s.dt_h
    doy = np.arange(79, 84)                                   # 20 March = day 79
    assert np.allclose(daily, 10.0 * (1 - 0.15 * np.cos(2 * np.pi * (doy - 172) / 365)), atol=1e-6)
    assert (s.load_crit_kw > 0).all()


def test_load_shape_has_evening_peak():
    s = generate_scenario_real(C, start=date(2023, 10, 10), n_days=14, dt_h=1.0, seed=5)
    hourly = s.load_kw.sum(axis=0).reshape(14, 24).mean(axis=0)
    assert hourly[18:22].mean() > 1.5 * hourly[2:5].mean()


@pytest.mark.parametrize("price_year", ds.PRICE_YEARS)
def test_prices_formula_and_range(price_year):
    s = generate_scenario_real(C, start=date(2023, 7, 10), n_days=7, dt_h=0.25, seed=0, price_year=price_year)
    pzu = repeat_hourly(ds.load_prices_lei_kwh(price_year)[190:197], 0.25)
    assert np.allclose(s.price_import, (pzu + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT))
    assert np.allclose(s.price_export, pzu + SUPPLY_MARGIN)
    assert 0.3 < s.price_import.min() and s.price_import.max() < 5.0
    assert 1.2 < s.price_import.mean() < 2.2
    s2 = generate_scenario_real(C, start=date(2023, 7, 10), n_days=7, seed=0, export_rule="pzu",
                                price_year=price_year)
    assert np.allclose(s2.price_export, pzu)


def test_price_year_changes_only_the_prices():
    kwargs = dict(start=date(2023, 4, 10), n_days=3, dt_h=0.25, seed=1)
    default = generate_scenario_real(C, **kwargs)
    by_year = {year: generate_scenario_real(C, price_year=year, **kwargs) for year in ds.PRICE_YEARS}
    np.testing.assert_array_equal(default.price_import, by_year[2025].price_import)
    for year in (2023, 2026):
        np.testing.assert_array_equal(by_year[year].pv_kw, by_year[2025].pv_kw)
        np.testing.assert_array_equal(by_year[year].load_kw, by_year[2025].load_kw)
        assert not np.allclose(by_year[year].price_import, by_year[2025].price_import)
    assert all(s.start == date(2023, 4, 10) for s in by_year.values())


def test_negative_pzu_keeps_import_positive_but_not_export():
    """import = (PZU + 0.7575) x 1.21 stays positive down to PZU = -0.7575 lei/kWh; export = PZU + 0.223
    goes negative below -0.223, which happens for a few hours in 2025 and 2026."""
    for year in (2025, 2026):
        pzu = ds.load_prices_lei_kwh(year)
        day = int(np.nanargmin(pzu.min(axis=1)))
        assert pzu[day].min() < -SUPPLY_MARGIN
        s = generate_scenario_real(C, start=date(2023, 1, 1) + timedelta(days=day), n_days=1, dt_h=1.0, seed=0,
                                   price_year=year)
        assert s.price_import.min() > 0 and s.price_export.min() < 0
        lp = compute_metrics(simulate(C, s, LPController()))["community"]
        assert lp["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)


def test_dates_outside_2023_rejected():
    with pytest.raises(ValueError):
        generate_scenario_real(C, start=date(2025, 1, 10))
    with pytest.raises(ValueError):
        generate_scenario_real(C, start=date(2023, 12, 30), n_days=3)
    with pytest.raises(ValueError):
        generate_scenario_real(C, export_rule="gratis")


def test_window_without_prices_is_rejected_with_the_last_day():
    last = ds.last_price_day(2026)
    with pytest.raises(ValueError, match=f"2026.*{last:%d.%m.%Y}"):
        generate_scenario_real(C, start=date(2023, 10, 10), n_days=7, price_year=2026)
    with pytest.raises(ValueError, match="se termina"):                       # window straddling the last day
        generate_scenario_real(C, start=last.replace(year=2023), n_days=2, price_year=2026)
    generate_scenario_real(C, start=last.replace(year=2023), n_days=1, dt_h=1.0, price_year=2026)
    with pytest.raises(ValueError, match="2024"):
        generate_scenario_real(C, price_year=2024)


def test_seasons_with_prices_and_make_scenario():
    assert seasons_with_prices(2023, 7) == seasons_with_prices(2025, 7) == ("iarna", "primavara", "vara", "toamna")
    assert seasons_with_prices(2026, 7) == ("iarna", "primavara", "vara")
    a = make_scenario("vara", 0, 1, 1.0, True, C, 2026)
    b = make_scenario("vara", 0, 1, 1.0, True, C)
    np.testing.assert_array_equal(a.pv_kw, b.pv_kw)
    pzu_2026 = ds.load_prices_lei_kwh(2026)[date(2023, 7, 10).timetuple().tm_yday - 1]
    assert np.allclose(a.price_export, pzu_2026 + SUPPLY_MARGIN)
    assert np.allclose(b.price_export, ds.load_prices_lei_kwh(2025)[190] + SUPPLY_MARGIN)


def test_lp_and_mpc_run_on_real_data():
    s = generate_scenario_real(C, start=date(2023, 1, 10), n_days=2, dt_h=0.25, seed=0)
    lp = compute_metrics(simulate(C, s, LPController()))["community"]      # DispatchError if infeasible
    assert lp["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    s1 = generate_scenario_real(C, start=date(2023, 7, 10), n_days=2, dt_h=1.0, seed=0)
    mpc = compute_metrics(simulate(C, s1, MPCController(horizon_h=12)))["community"]
    assert mpc["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6)
    assert mpc["ssr"] > 0.5                                                 # July: mostly self-supplied


@pytest.mark.parametrize("start", [date(2023, 1, 10), date(2023, 7, 10)])
def test_baselines_pass_strict_simulator_on_real_data(start):
    s = generate_scenario_real(C, start=start, n_days=2, dt_h=0.25, seed=0)
    for ctl in baseline_controllers():
        res = simulate(C, s, ctl)                    # DispatchError on any battery / inverter / grid violation
        assert compute_metrics(res)["community"]["balance_error_kwh"] == pytest.approx(0.0, abs=1e-6), ctl.name
