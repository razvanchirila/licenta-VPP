from vpp_core import evaluation, experiments, houses_report, sensitivity
from vpp_core.optimizer import LPController, MPCController
from vpp_core.reporting import COLORS, LABELS, SHORT_LABELS


def test_labels_cover_every_controller_name():
    names = set(evaluation.CONTROLLERS) | set(sensitivity.CONTROLLERS) | set(houses_report.CONTROLLERS)
    names |= {c.name for c in experiments.baseline_controllers()} | {MPCController().name, LPController().name}
    names |= {evaluation.make_controller(name, seed=0).name for name in evaluation.CONTROLLERS}
    assert names <= set(LABELS)
    assert set(SHORT_LABELS) == set(LABELS)
    assert set(COLORS) <= set(LABELS)
    assert len(set(LABELS.values())) == len(LABELS)
    assert LABELS["fara_baterie"].startswith("doar PV") and SHORT_LABELS["fara_baterie"] == "doar PV"


def test_summary_csv_round_trip(tmp_path):
    rows = [
        {"season": season, "seed": seed, "controller": controller, **dict.fromkeys(evaluation.METRICS, 1.5)}
        for season, _, _ in evaluation.SEASONS for seed in range(2) for controller in evaluation.CONTROLLERS
    ]
    summary = evaluation.summarize(rows, n_seeds=2)
    evaluation.write_summary_csv(summary, tmp_path / "summary.csv")
    reread = evaluation.read_summary_csv(tmp_path / "summary.csv")
    assert set(reread) == set(summary)
    assert reread[("iarna", "mpc")]["n"] == 2
    assert reread[("iarna", "mpc")]["cost_lei_mean"] == summary[("iarna", "mpc")]["cost_lei_mean"]
