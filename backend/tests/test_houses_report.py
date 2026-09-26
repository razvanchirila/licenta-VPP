import pytest

from vpp_core import houses_report as hr
from vpp_core.metrics import compute_metrics
from vpp_core.params import CommunityParams, GridParams, HouseParams, deye_se_f16
from vpp_core.reporting import make_scenario
from vpp_core.simulator import simulate

TINY_COMMUNITY = CommunityParams(
    houses=(HouseParams(id=1, battery=deye_se_f16(1)), HouseParams(id=2, battery=deye_se_f16(2)), HouseParams(id=3)),
    grid=GridParams(import_max_kw=15.0, export_max_kw=12.0, internal_line_kw=9.0),
)
TINY = hr.Settings(n_seeds=2, n_days=2, dt_h=1.0, workers=0,
                   controllers=("fara_baterie", "baterie_locala", "vpp_reguli"),
                   seasons=("iarna", "vara"), community=TINY_COMMUNITY)


def test_house_labels_and_modules():
    assert [hr.house_label(h) for h in TINY_COMMUNITY.houses] == [
        "Casa 1 (1 modul, 16 kWh)", "Casa 2 (2 module, 32 kWh)", "Casa 3 (fără stocare)",
    ]
    assert [hr.modules_of(h) for h in TINY_COMMUNITY.houses] == [1, 2, 0]


def test_rows_are_per_day_and_monthly_factor():
    scenario = make_scenario("iarna", 0, TINY.n_days, TINY.dt_h, False, TINY_COMMUNITY)
    metrics = compute_metrics(simulate(TINY_COMMUNITY, scenario, hr.make_controller("vpp_reguli", 0)))
    rows = hr.house_rows(metrics, TINY_COMMUNITY, TINY.n_days)
    assert [r["house"] for r in rows] == [1, 2, 3]
    for row, m in zip(rows, metrics["houses"], strict=True):
        assert row["consum_kwh_zi"] == pytest.approx(m["demand_kwh"] / TINY.n_days)
        assert row["import_kwh_zi"] == pytest.approx(m["import_kwh"] / TINY.n_days)
        assert row["p2p_in_kwh_zi"] + row["p2p_out_kwh_zi"] == pytest.approx((m["p2p_in_kwh"] + m["p2p_out_kwh"]) / 2)
        assert row["cost_lei"] == pytest.approx(m["cost_lei"])
        assert row["cost_luna_lei"] == pytest.approx(m["cost_lei"] * hr.MONTH_DAYS / TINY.n_days)
    assert hr.monthly(70.0, 7) == pytest.approx(300.0)


def test_aggregate_shape_and_mean_over_seeds(tmp_path):
    rows = hr.run_all(TINY)
    n_runs = len(TINY.controllers) * len(TINY.seasons)
    assert len(rows) == n_runs * TINY.n_seeds * TINY_COMMUNITY.n_houses
    assert all(r["cost_lei"] is not None for r in rows)
    summary = hr.aggregate(rows)
    assert len(summary) == n_runs * TINY_COMMUNITY.n_houses
    assert all(r["n"] == TINY.n_seeds and set(hr.KEYS) <= set(r) for r in summary)
    blank = [r for r in summary if r["cost_luna_lei"] is None]
    assert {(r["controller"], r["house"]) for r in blank} == {("baterie_locala", 3)}
    assert all(r["cost_lei"] is None and r["import_kwh_zi"] is not None for r in blank)
    first = summary[0]
    seeds = [r for r in rows if (r["season"], r["controller"], r["house"]) == ("iarna", "fara_baterie", 1)]
    assert (first["season"], first["controller"], first["house"]) == ("iarna", "fara_baterie", 1)
    assert first["cost_luna_lei"] == pytest.approx(sum(r["cost_luna_lei"] for r in seeds) / TINY.n_seeds)
    hr.write_csv(summary, hr.KEYS, tmp_path / "case.csv")
    reread = hr.read_case_csv(tmp_path / "case.csv")
    assert [(r["season"], r["controller"]) for r in reread] == [(r["season"], r["controller"]) for r in summary]
    assert [r["house"] for r in reread] == [r["house"] for r in summary]
    assert reread[0]["cost_luna_lei"] == pytest.approx(first["cost_luna_lei"], rel=1e-5)
    assert [r["cost_luna_lei"] for r in reread if hr.same_as_pv(r)] == [None, None]
    hr.monthly_chart(reread, TINY, tmp_path / "case_luna.png")
    assert (tmp_path / "case_luna.png").stat().st_size > 0


def test_house_costs_sum_to_community_cost():
    scenario = make_scenario("vara", 1, TINY.n_days, TINY.dt_h, False, TINY_COMMUNITY)
    metrics = compute_metrics(simulate(TINY_COMMUNITY, scenario, hr.make_controller("vpp_reguli", 1)))
    rows = hr.house_rows(metrics, TINY_COMMUNITY, TINY.n_days)
    assert sum(r["cost_lei"] for r in rows) == pytest.approx(metrics["community"]["cost_lei"])
