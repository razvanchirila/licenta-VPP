from datetime import date

import pytest

from vpp_core import compare_years as cy
from vpp_core import data_sources as ds
from vpp_core import evaluation
from vpp_core import houses_report as hr
from vpp_core.scenario_real import NETWORK_ADDER, SUPPLY_MARGIN, VAT

COSTS = {"fara_baterie": 70.0, "mpc": 35.0}      # lei per house per 7 days


def write_year(folder, seasons, factor=1.0):
    """summary.csv and case.csv of a 2-house community, the way evaluation and houses_report write them."""
    folder.mkdir(parents=True)
    rows = [{"season": season, "seed": 0, "controller": name, **dict.fromkeys(evaluation.METRICS, 0.0),
             "cost_lei": 2 * factor * COSTS.get(name, 50.0), "import_kwh": 100.0}
            for season in seasons for name in evaluation.CONTROLLERS]
    evaluation.write_summary_csv(evaluation.summarize(rows, n_seeds=1), folder / "summary.csv")
    case = [{"season": season, "controller": name, "house": house, "eticheta": f"Casa {house}", "module": 1,
             "baterie_kwh": 16.0, "n": 1, "days": 7.0, **{f"{key}_kwh_zi": 1.0 for key in hr.DAILY},
             "cost_lei": factor * COSTS.get(name, 50.0), "cost_luna_lei": hr.monthly(factor * COSTS.get(name, 50.0), 7)}
            for season in seasons for name in hr.CONTROLLERS for house in (1, 2)]
    hr.write_csv(case, hr.KEYS, folder / "case.csv")


def test_collect_rows_prices_and_missing_season(tmp_path):
    write_year(tmp_path / "2023", ("iarna", "vara", "toamna"))
    write_year(tmp_path / "2026", ("iarna", "vara"), factor=2.0)
    rows = cy.collect(tmp_path)
    assert [(r["season"], r["an"]) for r in rows] == [
        ("iarna", 2023), ("iarna", 2026), ("vara", 2023), ("vara", 2026), ("toamna", 2023)]
    first = rows[0]
    assert first["zile"] == 7
    assert first["cost_luna_casa_fara_baterie_lei"] == pytest.approx(300.0)
    assert first["cost_luna_casa_mpc_lei"] == pytest.approx(150.0) and first["economie_mpc_lei"] == pytest.approx(150.0)
    assert first["cost_comunitate_fara_baterie_lei"] == pytest.approx(140.0)
    assert rows[1]["cost_luna_casa_mpc_lei"] == pytest.approx(300.0)

    day = date(2023, 1, 10).timetuple().tm_yday - 1
    pzu = ds.load_prices_lei_kwh(2026)[day : day + 7]
    assert rows[1]["pzu_mediu_lei_kwh"] == pytest.approx(pzu.mean())
    import_mean = (pzu.mean() + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT)
    assert rows[1]["pret_import_mediu_lei_kwh"] == pytest.approx(import_mean)
    assert rows[1]["pret_export_mediu_lei_kwh"] == pytest.approx(pzu.mean() + SUPPLY_MARGIN)
    assert rows[1]["ore_pzu_negativ"] == int((pzu < 0).sum())


def test_csv_and_chart_are_written(tmp_path, capsys):
    write_year(tmp_path / "2023", ("iarna", "primavara", "vara", "toamna"))
    write_year(tmp_path / "2025", ("iarna", "primavara", "vara", "toamna"), factor=-1.0)
    write_year(tmp_path / "2026", ("iarna", "primavara", "vara"))
    cy.main(["--dir", str(tmp_path)])
    header = (tmp_path / "comparatie_ani.csv").read_text(encoding="utf-8").splitlines()
    assert header[0].split(",") == cy.KEYS and len(header) == 1 + 11
    assert (tmp_path / "comparatie_ani.png").stat().st_size > 0
    assert "toamna" in capsys.readouterr().out


def test_empty_folder_is_an_error(tmp_path):
    assert cy.collect(tmp_path) == []
    with pytest.raises(SystemExit):
        cy.main(["--dir", str(tmp_path)])
