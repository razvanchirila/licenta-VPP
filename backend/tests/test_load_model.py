"""Bottom-up load: catalog and neighbourhood parsing, the four device types, composition, wiring into scenarios."""
from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from vpp_core import load_model as lm
from vpp_core.params import CommunityParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.scenario_real import generate_scenario_real

C = default_community()
HEADER = ";".join(lm.COLUMNS)
HOUSE_HEADER = ";".join(lm.HOUSE_COLUMNS)
MONDAY = date(2023, 1, 2)


def write_csv(path, rows, header=HEADER):
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8-sig")
    return path


def energy_kwh_per_day(app, start=MONDAY, n_days=28, dt_h=0.25, seed=0):
    crit, flex = lm.house_load_profile([app], start, n_days, dt_h, np.random.default_rng(seed))
    return (crit + flex).sum() * dt_h / n_days, crit, flex


def by_hour(series, dt_h=0.25):
    """kWh per hour of the day, summed over all days."""
    spd = round(24 / dt_h)
    return series.reshape(-1, spd).sum(axis=0).reshape(24, -1).sum(axis=1) * dt_h


def prog(interval=None, durata=0.0, porniri=0.0, zile="toate", sezon="tot_anul"):
    return lm.Program("", lm.parse_interval(interval) if interval else None, durata, porniri, zile, sezon)


# ----------------------------------------------------------------------------- committed files

def test_committed_catalog_and_neighbourhood_parse():
    catalog = lm.load_catalog()
    assert {r.tip for r in catalog.rows} == set(lm.TIPURI)
    assert {"frigider", "router", "standby", "iluminat", "televizor"} == set(catalog.names("toti"))
    assert set(catalog.names("incalzire")) == {"pompa de caldura", "radiator electric"}
    plita = [r for r in catalog.rows if r.dispozitiv == "plita"]
    assert [(r.program.moment, r.acasa, r.program.zile) for r in plita] == [
        ("cina", "oricand", "toate"), ("pranz", "oricand", "weekend"), ("pranz", "da", "lucru")]
    washer = next(r for r in catalog.rows if r.dispozitiv == "masina de spalat")
    assert washer.program.porniri_pe_saptamana == pytest.approx(1.3) and washer.pe_persoana   # written as 1,3
    assert [h.casa for h in catalog.houses] == list(range(1, 11))


def test_committed_neighbourhood_covers_the_extremes():
    houses = lm.compose_houses(range(1, 11))
    annual = {h.casa: h.kwh_per_year() for h in houses}
    assert min(annual, key=annual.get) == 1 and max(annual, key=annual.get) == 7      # pensioner .. has everything
    assert 500 < annual[1] < 1500 and annual[7] > 4000
    ev = {h.casa for h in houses if any(a.dispozitiv == "masina electrica" for a in h.appliances)}
    assert ev == {7, 9}
    assert {h.casa for h in houses if h.acasa_ziua} == {1, 2, 6, 7, 8}


# ----------------------------------------------------------------------------- CSV

def test_parse_interval_and_wrap():
    assert lm.parse_interval("18-23") == (18.0, 23.0)
    assert lm.parse_interval("0-24") == (0.0, 24.0)
    assert lm.parse_interval("18-7") == (18.0, 31.0)
    assert lm.format_interval((18.0, 31.0)) == "18-7"
    for bad in ("18", "25-3", "a-b"):
        with pytest.raises(ValueError):
            lm.parse_interval(bad)


def test_bad_rows_report_the_line(tmp_path):
    ok = "frigider;;toti;nu;oricand;permanent;21;;;;toate;tot_anul;nu;x"
    for bad, text in [
        ("tv;;toti;nu;oricand;uneori;60;18-23;;;toate;tot_anul;nu;x", "tip"),
        ("tv;;cativa;nu;oricand;interval;60;18-23;;;toate;tot_anul;nu;x", "cine"),
        ("tv;;toti;nu;mereu;interval;60;18-23;;;toate;tot_anul;nu;x", "acasa"),
        ("tv;;toti;nu;oricand;interval;60;18-23;;;luni;tot_anul;nu;x", "zile"),
        ("tv;;toti;nu;oricand;interval;60;18-23;;;toate;toamna;nu;x", "sezon"),
        ("tv;;toti;nu;oricand;interval;60;;;;toate;tot_anul;nu;x", "trebuie interval"),
        ("tv;;toti;nu;oricand;interval;60;18-23;30;;toate;tot_anul;nu;x", "fara durata_min"),
        ("tv;;toti;da;oricand;interval;60;18-23;;;toate;tot_anul;nu;x", "pe_persoana"),
        ("cuptor;;ales;nu;oricand;durata;2000;17-20;;2;toate;tot_anul;nu;x", "durata_min"),
        ("cuptor;;ales;nu;oricand;durata;2000;17-20;30;0;toate;tot_anul;nu;x", "porniri"),
        ("pompa;;incalzire;nu;oricand;termic;2500;0-24;;;toate;tot_anul;da;x", "raman goale"),
        ("tv;;toti;nu;oricand;interval;abc;18-23;;;toate;tot_anul;nu;x", "numar"),
        ("tv;;toti;nu;oricand;interval;0;18-23;;;toate;tot_anul;nu;x", "putere_w"),
        ("tv;;toti;nu;oricand;interval;60;18-23;;;toate;tot_anul;poate;x", "flexibil"),
        ("sauna;;ales;nu;oricand;termic;6000;;;;toate;tot_anul;da;x", "modelul termic stie doar"),
        ("frigider;;toti;nu;oricand;permanent;30;;;;toate;tot_anul;nu;x", "putere_w difera"),
    ]:
        with pytest.raises(ValueError, match=f"randul 3.*{text}"):
            lm.load_rows(write_csv(tmp_path / "d.csv", [ok, bad]))
    with pytest.raises(ValueError, match="antetul"):
        lm.load_rows(write_csv(tmp_path / "d.csv", [ok], header="dispozitiv;putere_w"))


def test_blank_lines_case_and_comma_decimals(tmp_path):
    rows = lm.load_rows(write_csv(tmp_path / "d.csv", [
        "Masina de spalat;;ales;da;oricand;durata;130;9-21;219;1,3;;;nu;x", ";;;;;;;;;;;;;",
    ]))
    assert len(rows) == 1
    washer = rows[0]
    assert washer.dispozitiv == "masina de spalat" and washer.acasa == "oricand"
    assert washer.program == lm.Program("", (9.0, 21.0), 219.0, 1.3, "toate", "tot_anul")


def test_houses_file_is_checked_against_the_catalog(tmp_path):
    rows = lm.load_rows(write_csv(tmp_path / "d.csv", [
        "frigider;;toti;nu;oricand;permanent;21;;;;toate;tot_anul;nu;x",
        "laptop;;ales;da;oricand;durata;30;17-23;150;7;toate;tot_anul;nu;x",
        "pompa de caldura;;incalzire;nu;oricand;termic;2500;;;;toate;tot_anul;da;x",
    ]))
    ok = "1;pensionar;1;da;gaz;veche;"
    couple = "2;cuplu;2;nu;pompa de caldura;;laptop"
    houses = lm.load_houses(rows, write_csv(tmp_path / "c.csv", [ok, couple], HOUSE_HEADER))
    assert houses[1] == lm.HouseSpec(2, "cuplu", 2, False, "pompa de caldura", "medie", ("laptop",))
    for bad, text in [
        ("3;x;1;da;gaz;;", "astept 2"),
        ("2;x;0;da;gaz;;", "persoane"),
        ("2;x;1,5;da;gaz;;", "persoane"),
        ("2;x;1;poate;gaz;;", "acasa_ziua"),
        ("2;x;1;da;lemne;;", "incalzire"),
        ("2;x;1;da;gaz;;laptop,sauna", "sauna"),
        ("2;x;1;da;gaz;paie;", "izolatie"),
        ("2;x;1;da;gaz;;frigider", "frigider"),
    ]:
        with pytest.raises(ValueError, match=f"randul 3.*{text}"):
            lm.load_houses(rows, write_csv(tmp_path / "c.csv", [ok, bad], HOUSE_HEADER))
    with pytest.raises(ValueError, match="nicio casa"):
        lm.load_houses(rows, write_csv(tmp_path / "c.csv", [], HOUSE_HEADER))


def test_programs_round_trip_through_json():
    programs = (prog("18-7", 200, 3), prog("17-23", sezon="iarna"), lm.Program("cina", (18.0, 20.0), 30, 7))
    assert lm.programs_from_json(lm.programs_to_json(programs)) == programs
    assert lm.programs_from_json(lm.programs_to_json((lm.Program(),))) == (lm.Program(),)


# ----------------------------------------------------------------------------- energy

def test_permanent_is_constant():
    app = lm.Appliance("frigider", 45, "permanent")
    kwh, crit, flex = energy_kwh_per_day(app, n_days=3)
    assert np.allclose(crit, 0.045) and np.allclose(flex, 0)
    assert kwh == pytest.approx(0.045 * 24)


@pytest.mark.parametrize("dt_h", [0.25, 1.0])
def test_interval_runs_the_whole_interval_with_moving_ends(dt_h):
    app = lm.Appliance("televizor", 100, "interval", (prog("18-23"),))
    kwh, crit, _ = energy_kwh_per_day(app, n_days=56, dt_h=dt_h)
    assert kwh == pytest.approx(0.5, rel=0.03)                              # 100 W x 5 h
    hourly = by_hour(crit, dt_h) / 56
    assert hourly[:17].sum() == 0 and hourly[0] == 0                        # ends move by at most 30 min
    assert hourly[19:22] == pytest.approx(0.1)                              # always on in the middle
    assert 0 < hourly[17] < 0.1 and 0 < hourly[23] < 0.1


def test_days_and_seasons_restrict_a_program():
    office = lm.Appliance("calculator", 100, "interval", (prog("9-17", zile="lucru"),))
    kwh, crit, _ = energy_kwh_per_day(office, n_days=28)
    assert kwh == pytest.approx(0.8 * 5 / 7, rel=0.02)
    week = crit.reshape(28, -1).sum(axis=1).reshape(4, 7)                   # starts on a Monday
    assert (week[:, :5] > 0).all() and (week[:, 5:] == 0).all()
    lights = lm.Appliance("iluminat", 100, "interval", (prog("17-23", sezon="iarna"), prog("21-23", sezon="vara")))
    assert energy_kwh_per_day(lights, start=MONDAY)[0] == pytest.approx(0.6, rel=0.03)
    assert energy_kwh_per_day(lights, start=date(2023, 7, 3))[0] == pytest.approx(0.2, rel=0.05)
    assert energy_kwh_per_day(lights, start=date(2023, 4, 3))[0] == 0
    assert lights.kwh_per_year() == pytest.approx(0.6 * 151 + 0.2 * 92)


def test_durata_energy_count_and_window():
    app = lm.Appliance("masina de spalat", 700, "durata", (prog("8-21", 90, 4),))
    kwh, crit, _ = energy_kwh_per_day(app, n_days=70)
    assert kwh == pytest.approx(0.7 * 4 / 7 * 1.5, rel=0.03)
    assert app.kwh_per_day("iarna") == pytest.approx(0.7 * 4 / 7 * 1.5)
    hourly = by_hour(crit)
    assert hourly[:8].sum() == 0 and hourly[23:].sum() == 0                 # starts 8-21, runs <= 1.65 h
    weekend = lm.Appliance("aspirator", 900, "durata", (prog("9-13", 45, 1, zile="weekend"),))
    _, crit, _ = energy_kwh_per_day(weekend, n_days=28)
    days = crit.reshape(28, -1).sum(axis=1).reshape(4, 7)
    assert (days[:, :5] == 0).all() and (days[:, 5:].sum(axis=1) > 0).all() # one run every weekend


def test_runs_of_a_week_never_pile_up_at_the_window_edge():
    ev = lm.Appliance("masina electrica", 7400, "durata", (prog("18-7", 200, 3),), flexibil=True)
    for start in (MONDAY, date(2023, 1, 5), date(2023, 1, 7)):
        for n_days in (1, 2, 9):
            for seed in range(20):
                _, _, flex = energy_kwh_per_day(ev, start=start, n_days=n_days, seed=seed)
                assert flex.max() <= 7.4 + 1e-9


def test_interval_wrapping_midnight():
    ev = lm.Appliance("EV", 7000, "durata", (prog("22-6", 60, 7),), flexibil=True)
    kwh, _, flex = energy_kwh_per_day(ev)
    assert kwh == pytest.approx(7.0, rel=0.05)
    by_step = flex.reshape(-1, 96).sum(axis=0)
    assert by_step[4 * 8 : 4 * 22].sum() == 0
    assert by_step[: 4 * 6].sum() > 0 and by_step[4 * 22 :].sum() > 0
    night = lm.Appliance("veioza", 50, "interval", (prog("22-6"),))
    kwh, crit, _ = energy_kwh_per_day(night)
    assert kwh == pytest.approx(0.4, rel=0.03)


def test_thermal_draws_nothing_here():
    pump = lm.Appliance("pompa de caldura", 2500, "termic", flexibil=True)
    kwh, crit, flex = energy_kwh_per_day(pump)
    assert kwh == 0 and pump.kwh_per_year() == 0


def test_flexible_split_and_seeding():
    apps = [lm.Appliance("frigider", 100, "permanent"),
            lm.Appliance("boiler", 2000, "durata", (prog("6-22", 60, 7),), flexibil=True)]
    crit, flex = lm.house_load_profile(apps, MONDAY, 7, 0.25, np.random.default_rng(1))
    assert crit.shape == flex.shape == (7 * 96,)
    assert np.allclose(crit, 0.1)
    assert flex.sum() * 0.25 == pytest.approx(7 * 2.0, rel=0.1)
    a = lm.house_load_profile(apps, MONDAY, 2, 0.25, np.random.default_rng(3))
    b = lm.house_load_profile(apps, MONDAY, 2, 0.25, np.random.default_rng(3))
    c = lm.house_load_profile(apps, MONDAY, 2, 0.25, np.random.default_rng(4))
    np.testing.assert_array_equal(a[1], b[1])
    assert not np.array_equal(a[1], c[1])


def test_season_of():
    assert [lm.season_of(date(2023, m, 15)) for m in (1, 3, 4, 5, 6, 8, 9, 10, 11, 12)] == [
        "iarna", "iarna", "intermediar", "intermediar", "vara", "vara", "intermediar", "intermediar", "iarna", "iarna",
    ]


# ----------------------------------------------------------------------------- composition

def test_composition_follows_the_house_row():
    catalog = lm.load_catalog()
    retired = lm.compose_house(1, catalog)
    assert retired.persoane == 1 and retired.acasa_ziua and retired.incalzire == "gaz"
    assert [a.dispozitiv for a in retired.appliances] == [
        "frigider", "router", "standby", "iluminat", "televizor", "microunde", "masina de spalat", "aspirator"]
    tv = next(a for a in retired.appliances if a.dispozitiv == "televizor")
    assert len(tv.programe) == 3                                            # evening, weekend, workday at home
    family = lm.compose_house(5, catalog)
    tv = next(a for a in family.appliances if a.dispozitiv == "televizor")
    assert len(tv.programe) == 2
    washer = next(a for a in family.appliances if a.dispozitiv == "masina de spalat")
    assert washer.programe[0].porniri_pe_saptamana == pytest.approx(1.3 * 4)
    office = next(a for a in lm.compose_house(9, catalog).appliances if a.dispozitiv == "calculator birou")
    assert [p.moment for p in office.programe] == ["seara"]                 # nobody home in the day
    assert "pompa de caldura" in [a.dispozitiv for a in lm.compose_house(7, catalog).appliances]


def test_larger_communities_repeat_the_neighbourhood():
    catalog = lm.load_catalog()
    for k in (11, 23, 200):
        twin = lm.compose_house(k, catalog)
        base = lm.compose_house((k - 1) % 10 + 1, catalog)
        assert twin.casa == k and twin.appliances == base.appliances and twin.persoane == base.persoane
    assert lm.compose_house(0, catalog).appliances == lm.compose_house(10, catalog).appliances


# ----------------------------------------------------------------------------- community

def test_community_load_shapes_and_house_independence():
    crit, flex = lm.community_load(C, date(2023, 1, 10), 3, 0.5, seed=0)
    assert crit.shape == flex.shape == (10, 144)
    assert (crit > 0).all() and (flex >= 0).all()
    assert (crit + flex).sum(axis=1).min() * 0.5 > 3 * 1.5                  # every house above 1.5 kWh/day
    only_two = CommunityParams(houses=(HouseParams(id=4), HouseParams(id=2)))
    crit2, flex2 = lm.community_load(only_two, date(2023, 1, 10), 3, 0.5, seed=0)
    np.testing.assert_array_equal(crit2[0], crit[3])
    np.testing.assert_array_equal(flex2[1], flex[1])


def test_community_load_runs_the_composition_on_the_timing_stream():
    start = date(2023, 1, 10)
    community = CommunityParams(houses=(HouseParams(id=57), HouseParams(id=2)))
    crit, flex = lm.community_load(community, start, 14, 0.25, seed=0)
    house = lm.compose_house(57, lm.load_catalog())
    expected = lm.house_load_profile(house.appliances, start, 14, 0.25, lm.house_rng(0, 57))
    np.testing.assert_array_equal(crit[0], expected[0])
    np.testing.assert_array_equal(flex[0], expected[1])
    always_on = sum(app.kw for app in house.appliances if app.tip == "permanent")
    assert (crit[0] + flex[0]).min() >= always_on - 1e-9
    daily = (crit[0] + flex[0]).sum() * 0.25 / 14
    assert daily == pytest.approx(house.kwh_per_day("iarna"), rel=0.25)


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
    assert 1 < daily.min() and daily.max() < 40
    with pytest.raises(ValueError):
        generate_scenario_real(C, load_source="sintetic")


# ----------------------------------------------------------------------------- report

def test_year_report_matches_the_table():
    houses = [
        lm.House(1, "a", 2, True, "gaz", "medie", (
            lm.Appliance("frigider", 45, "permanent"),
            lm.Appliance("boiler", 2000, "durata", (prog("6-9", 45, 10),), flexibil=True))),
        lm.House(2, "b", 3, False, "pompa de caldura", "noua", (
            lm.Appliance("frigider", 45, "permanent"),
            lm.Appliance("iluminat", 90, "interval", (prog("6-8", sezon="iarna"), prog("17-23"))),
            lm.Appliance("masina de vase", 900, "durata", (prog("19-23", 120, 4),), flexibil=True),
            lm.Appliance("pompa de caldura", 2500, "termic", flexibil=True))),
    ]
    year = lm.simulate_year(houses, 1.0, seed=0)
    rows = lm.house_rows(houses, year, 1.0)
    assert [(row["casa"], row["persoane"], row["dispozitive"]) for row in rows] == [(1, 2, 2), (2, 3, 4)]
    assert rows[1]["lista"] == "frigider, iluminat, masina de vase, pompa de caldura"
    for row in rows:
        assert row["kwh_an"] == pytest.approx(row["kwh_an_calculat"], rel=0.03)
        assert row["kwh_an"] == pytest.approx(sum(row[f"kwh_an_{tip}"] for tip in lm.TIPURI))
    assert rows[1]["kwh_an_termic"] == 0
    devices = lm.device_rows(houses)
    assert [d["program"] for d in devices[3:5]] == ["6-8 iarnă; 17-23", "4×120 min/săpt. 19-23"]


def test_phases_shape_a_run_and_keep_its_energy(tmp_path):
    rows = lm.load_rows(write_csv(tmp_path / "d.csv", [
        "masina de spalat;;ales;da;oricand;durata;2000;9-21;219;1,3;toate;tot_anul;nu;x;10:2000 209:40",
    ]))
    washer = rows[0].program
    assert washer.faze == ((10.0, 2000.0), (209.0, 40.0))
    assert washer.run_kwh(2000) == pytest.approx((10 * 2000 + 209 * 40) / 60_000)
    app = lm.Appliance("masina de spalat", 2000, "durata", (replace(washer, porniri_pe_saptamana=7),))
    kwh, crit, _ = energy_kwh_per_day(app, n_days=56, dt_h=1 / 12)
    assert kwh == pytest.approx(washer.run_kwh(2000), rel=0.03)
    assert crit.max() == pytest.approx(2.0, abs=0.05) and np.mean(crit[crit > 0] < 0.1) > 0.8   # mostly the motor
    assert lm.programs_from_json(lm.programs_to_json((washer,))) == (washer,)
    for bad, text in [("10:2000 200:40", "durata_min"), ("10:3000 209:40", "putere_w"), ("10:abc 209:40", "numar")]:
        with pytest.raises(ValueError, match=text):
            lm.load_rows(write_csv(tmp_path / "d.csv", [
                f"masina de spalat;;ales;da;oricand;durata;2000;9-21;219;1,3;toate;tot_anul;nu;x;{bad}"]))
    tv = "tv;;toti;nu;oricand;interval;60;18-23;;;toate;tot_anul;nu;x;5:60"
    with pytest.raises(ValueError, match="doar pentru tip = durata"):
        lm.load_rows(write_csv(tmp_path / "d.csv", [tv]))
