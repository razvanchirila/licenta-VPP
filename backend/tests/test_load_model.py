"""Bottom-up load from dispozitive.csv: parsing, energy consistency, intervals, seasons, wiring into scenarios."""
from datetime import date

import numpy as np
import pytest

from vpp_core import load_model as lm
from vpp_core.params import CommunityParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.scenario_real import generate_scenario_real

C = default_community()
HEADER = ";".join(lm.COLUMNS)


def write_csv(path, rows):
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8-sig")
    return path


def energy_kwh_per_day(app, start=date(2023, 1, 2), n_days=28, dt_h=0.25, seed=0):
    crit, flex = lm.house_load_profile([app], start, n_days, dt_h, np.random.default_rng(seed))
    return (crit + flex).sum() * dt_h / n_days, crit, flex


# ----------------------------------------------------------------------------- CSV

def test_committed_csv_parses_ten_houses():
    apps = lm.load_appliances()
    groups = lm.by_house(apps)
    assert sorted(groups) == list(range(1, 11))
    assert {app.mod for app in apps} == set(lm.MODES)
    assert all(2 <= app.persoane <= 5 for app in apps)
    assert all(len({app.persoane for app in group}) == 1 for group in groups.values())
    hob = next(app for app in groups[1] if app.dispozitiv == "plită electrică")
    assert hob.ore_pe_zi == pytest.approx(0.8)                    # written as 0,8 (Excel RO)
    for house_id, group in groups.items():
        annual = sum(app.kwh_per_year() for app in group)
        assert 1900 < annual < 5100, house_id


def test_parse_interval_and_wrap():
    assert lm.parse_interval("18-23") == (18.0, 23.0)
    assert lm.parse_interval("0-24") == (0.0, 24.0)
    assert lm.parse_interval("22-6") == (22.0, 30.0)
    with pytest.raises(ValueError):
        lm.parse_interval("18")
    with pytest.raises(ValueError):
        lm.parse_interval("25-3")


def test_bad_rows_report_the_line(tmp_path):
    ok = "1;frigider;45;continuu;;;;0-24;tot_anul;nu;2"
    for bad, text in [
        ("1;tv;100;uneori;2;;;18-23;tot_anul;nu;2", "mod"),
        ("1;tv;100;zilnic;8;;;18-23;tot_anul;nu;2", "ore_pe_zi"),
        ("1;tv;100;zilnic;2;;;18-23;tot_anul;poate;2", "flexibil"),
        ("1;masina;700;ciclic;;0;90;8-21;tot_anul;da;2", "ciclic"),
        ("1;tv;abc;zilnic;2;;;18-23;tot_anul;nu;2", "numar"),
    ]:
        with pytest.raises(ValueError, match=f"randul 3.*{text}"):
            lm.load_appliances(write_csv(tmp_path / "d.csv", [ok, bad]))
    (tmp_path / "h.csv").write_text("casa;dispozitiv\n1;frigider\n", encoding="utf-8")
    with pytest.raises(ValueError, match="antetul"):
        lm.load_appliances(tmp_path / "h.csv")


def test_blank_lines_and_comma_decimals(tmp_path):
    apps = lm.load_appliances(write_csv(tmp_path / "d.csv", [
        "1;plită;1500;zilnic;0,8;;;11-21;tot_anul;nu;3", ";;;;;;;;;;", "2;boiler;2000;ciclic;;3,5;45;6-22;;da;2",
    ]))
    assert len(apps) == 2
    assert apps[0].ore_pe_zi == pytest.approx(0.8) and apps[1].cicluri_pe_saptamana == pytest.approx(3.5)
    assert apps[1].sezon == "tot_anul" and apps[1].flexibil


# ----------------------------------------------------------------------------- energy consistency

def test_continuous_is_constant():
    app = lm.Appliance(1, "frigider", 45, "continuu")
    kwh, crit, flex = energy_kwh_per_day(app, n_days=3)
    assert np.allclose(crit, 0.045) and np.allclose(flex, 0)
    assert kwh == pytest.approx(0.045 * 24)


@pytest.mark.parametrize("dt_h", [0.25, 1.0])
def test_daily_block_energy(dt_h):
    app = lm.Appliance(1, "iluminat", 100, "zilnic", ore_pe_zi=5, interval=(17, 23))
    kwh, crit, _ = energy_kwh_per_day(app, dt_h=dt_h)
    assert kwh == pytest.approx(0.5, rel=0.05)                       # 100 W x 5 h
    spd = round(24 / dt_h)
    by_hour = crit.reshape(-1, spd).sum(axis=0)
    assert by_hour[: round(17 / dt_h)].sum() == 0 and by_hour[round(23 / dt_h):].sum() == 0


def test_cyclic_energy_and_count():
    app = lm.Appliance(1, "mașină de spălat", 700, "ciclic", cicluri_pe_saptamana=4, durata_ciclu_min=90,
                       interval=(8, 21), flexibil=True)
    kwh, crit, flex = energy_kwh_per_day(app)
    assert kwh == pytest.approx(0.7 * 4 / 7 * 1.5, rel=0.05)
    assert crit.sum() == 0 and (flex >= 0).all()


def test_thermal_energy_follows_the_season():
    app = lm.Appliance(1, "pompă de căldură", 2500, "termic", ore_pe_zi=6, interval=(0, 24), sezon="iarna")
    winter, _, _ = energy_kwh_per_day(app, start=date(2023, 1, 2))
    shoulder, _, _ = energy_kwh_per_day(app, start=date(2023, 4, 3))
    summer, _, _ = energy_kwh_per_day(app, start=date(2023, 7, 3))
    assert winter == pytest.approx(15.0, rel=0.05)
    assert shoulder == pytest.approx(7.5, rel=0.05)
    assert summer == 0
    ac = lm.Appliance(1, "aer condiționat", 1200, "termic", ore_pe_zi=4, interval=(12, 23), sezon="vara")
    assert energy_kwh_per_day(ac, start=date(2023, 7, 3))[0] == pytest.approx(4.8, rel=0.05)
    assert energy_kwh_per_day(ac, start=date(2023, 1, 2))[0] == 0
    assert app.kwh_per_year() == pytest.approx(15 * 151 + 7.5 * 122)


def test_season_and_factor():
    assert [lm.season_of(date(2023, m, 15)) for m in (1, 3, 4, 5, 6, 8, 9, 10, 11, 12)] == [
        "iarna", "iarna", "intermediar", "intermediar", "vara", "vara", "intermediar", "intermediar", "iarna", "iarna",
    ]
    assert lm.thermal_factor("tot_anul", "vara") == 1.0
    assert lm.thermal_factor("iarna", "intermediar") == 0.5
    assert lm.thermal_factor("vara", "iarna") == 0.0


def test_interval_wrapping_midnight():
    ev = lm.Appliance(1, "EV", 7000, "ciclic", cicluri_pe_saptamana=7, durata_ciclu_min=60, interval=(22, 30),
                      flexibil=True)
    kwh, _, flex = energy_kwh_per_day(ev)
    assert kwh == pytest.approx(7.0, rel=0.05)
    by_step = flex.reshape(-1, 96).sum(axis=0)
    assert by_step[4 * 7 : 4 * 22].sum() == 0                          # nothing between 07:00 and 22:00
    assert by_step[: 4 * 6].sum() > 0 and by_step[4 * 22 :].sum() > 0  # runs on both sides of midnight
    night = lm.Appliance(1, "veioză", 50, "zilnic", ore_pe_zi=3, interval=(22, 30))
    kwh, crit, _ = energy_kwh_per_day(night)
    assert kwh == pytest.approx(0.15, rel=0.05)
    assert crit.reshape(-1, 96).sum(axis=0)[4 * 7 : 4 * 22].sum() == 0


def test_flexible_split_and_house_profile():
    apps = [lm.Appliance(1, "frigider", 100, "continuu"),
            lm.Appliance(1, "boiler", 2000, "ciclic", cicluri_pe_saptamana=7, durata_ciclu_min=60, flexibil=True)]
    crit, flex = lm.house_load_profile(apps, date(2023, 1, 2), 7, 0.25, np.random.default_rng(1))
    assert crit.shape == flex.shape == (7 * 96,)
    assert np.allclose(crit, 0.1)
    assert flex.sum() * 0.25 == pytest.approx(7 * 2.0, rel=0.05)


def test_profile_is_seeded():
    apps = lm.load_appliances()
    a = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(3))
    b = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(3))
    c = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(4))
    np.testing.assert_array_equal(a[1], b[1])
    assert not np.array_equal(a[1], c[1])


# ----------------------------------------------------------------------------- community

def test_community_load_shapes_and_house_independence():
    crit, flex = lm.community_load(C, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 3, 0.5, seed=0)
    assert crit.shape == flex.shape == (10, 144)
    assert (crit > 0).all() and (flex >= 0).all()
    assert (crit + flex).sum(axis=1).min() * 0.5 > 3 * 3          # every house above 3 kWh/day
    only_two = CommunityParams(houses=(HouseParams(id=4), HouseParams(id=2)))
    crit2, flex2 = lm.community_load(only_two, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 3, 0.5, seed=0)
    np.testing.assert_array_equal(crit2[0], crit[3])
    np.testing.assert_array_equal(flex2[1], flex[1])


def test_missing_house_uses_fallback_with_a_warning():
    community = CommunityParams(houses=(HouseParams(id=1), HouseParams(id=99)))
    fallback = (np.full((2, 48), 0.3), np.full((2, 48), 0.2))
    with pytest.warns(UserWarning, match="99"):
        crit, flex = lm.community_load(community, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 2, 1.0, 0, fallback)
    assert np.allclose(crit[1], 0.3) and np.allclose(flex[1], 0.2)
    assert not np.allclose(crit[0], 0.3)
    with pytest.raises(ValueError, match="99"):
        lm.community_load(community, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 2, 1.0, 0)


def test_profile_id_picks_the_appliances_and_the_house_id_the_random_stream():
    start, args = date(2023, 1, 10), (date(2023, 1, 10), 14, 0.25)
    own = CommunityParams(houses=(HouseParams(id=2), HouseParams(id=4)))
    same = CommunityParams(houses=(HouseParams(id=2, profile_id=2), HouseParams(id=4, profile_id=4)))
    crit_own, flex_own = lm.community_load(own, lm.DISPOZITIVE_CSV, *args, seed=0)
    crit_same, flex_same = lm.community_load(same, lm.DISPOZITIVE_CSV, *args, seed=0)
    np.testing.assert_array_equal(crit_own, crit_same)                # profile_id = id is today's behaviour
    np.testing.assert_array_equal(flex_own, flex_same)

    copies = CommunityParams(houses=(HouseParams(id=57, profile_id=2), HouseParams(id=58, profile_id=2),
                                     HouseParams(id=2)))
    crit, flex = lm.community_load(copies, lm.DISPOZITIVE_CSV, *args, seed=0)     # ids 57, 58 are not in the CSV
    total = crit + flex
    assert not np.array_equal(total[0], total[1]) and not np.array_equal(total[0], total[2])
    daily = total.sum(axis=1) * 0.25 / 14
    assert daily[0] == pytest.approx(daily[2], rel=0.1) and daily[1] == pytest.approx(daily[2], rel=0.1)
    always_on = sum(app.kw for app in lm.by_house(lm.load_appliances())[2] if app.mod == "continuu")
    assert (total.min(axis=1) >= always_on - 1e-9).all()
    rng = lm.house_rng(0, 57)
    expected = lm.house_load_profile(lm.by_house(lm.load_appliances())[2], start, 14, 0.25, rng)
    np.testing.assert_array_equal(crit[0], expected[0])
    np.testing.assert_array_equal(flex[0], expected[1])


def test_unknown_profile_id_falls_back_like_a_missing_house():
    community = CommunityParams(houses=(HouseParams(id=1, profile_id=99), HouseParams(id=2)))
    with pytest.raises(ValueError, match=r"\[1\]"):
        lm.community_load(community, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 1, 1.0, 0)
    fallback = (np.full((2, 24), 0.3), np.full((2, 24), 0.2))
    with pytest.warns(UserWarning, match="1 case lipsesc"):
        crit, _ = lm.community_load(community, lm.DISPOZITIVE_CSV, date(2023, 1, 10), 1, 1.0, 0, fallback)
    assert np.allclose(crit[0], 0.3) and not np.allclose(crit[1], 0.3)


# ----------------------------------------------------------------------------- scenarios

def test_synthetic_scenario_load_sources():
    new = generate_scenario(C, start=date(2025, 1, 10), n_days=2, dt_h=0.5, seed=1)
    old = generate_scenario(C, start=date(2025, 1, 10), n_days=2, dt_h=0.5, seed=1, load_source="sintetic")
    assert new.load_kw.shape == old.load_kw.shape == (10, 96)
    np.testing.assert_array_equal(new.pv_kw, old.pv_kw)               # same PV and prices, only the load differs
    np.testing.assert_array_equal(new.price_import, old.price_import)
    assert not np.allclose(new.load_kw, old.load_kw)
    assert (new.load_kw > 0).all()
    with pytest.raises(ValueError):
        generate_scenario(C, load_source="deer")


def test_real_scenario_load_sources():
    new = generate_scenario_real(C, start=date(2023, 1, 10), n_days=2, dt_h=0.25, seed=1)
    old = generate_scenario_real(C, start=date(2023, 1, 10), n_days=2, dt_h=0.25, seed=1, load_source="deer")
    assert new.load_kw.shape == old.load_kw.shape == (10, 192)
    np.testing.assert_array_equal(new.pv_kw, old.pv_kw)
    np.testing.assert_array_equal(new.price_import, old.price_import)
    assert not np.allclose(new.load_kw, old.load_kw)
    daily = new.load_kw.sum(axis=1) * 0.25 / 2
    assert 3 < daily.min() and daily.max() < 25
    assert 9 < daily.mean() < 15                                      # winter: ~11.6 kWh/day/house
    with pytest.raises(ValueError):
        generate_scenario_real(C, load_source="sintetic")


# ----------------------------------------------------------------------------- report

def test_year_report_matches_the_table(tmp_path):
    apps = [app for app in lm.load_appliances() if app.casa in (1, 2)]
    year = lm.simulate_year(apps, 1.0, seed=0)
    rows = lm.house_rows(apps, year, 1.0)
    assert [row["casa"] for row in rows] == [1, 2]
    for row in rows:
        assert row["kwh_an"] == pytest.approx(row["kwh_an_calculat"], rel=0.03)
        assert row["kwh_an"] == pytest.approx(sum(row[f"kwh_an_{mode}"] for mode in lm.MODES))
        assert 0 < row["cota_flexibil"] < 1
    assert rows[1]["kwh_zi_iarna"] > 2 * rows[1]["kwh_zi_vara"]        # heat pump
    lm.daily_profile_chart(year, 1.0, tmp_path / "profil.png")
    lm.annual_chart(rows, tmp_path / "anual.png")
    assert (tmp_path / "profil.png").stat().st_size > 0 and (tmp_path / "anual.png").stat().st_size > 0
