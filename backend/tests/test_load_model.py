"""Bottom-up load: catalog parsing, weighted intervals, random houses, energy consistency, wiring into scenarios."""
from datetime import date

import numpy as np
import pytest

from vpp_core import load_model as lm
from vpp_core.params import CommunityParams, HouseParams, default_community
from vpp_core.scenario import generate_scenario
from vpp_core.scenario_real import generate_scenario_real

C = default_community()
HEADER = ";".join(lm.COLUMNS)


def write_csv(path, rows, header=HEADER):
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8-sig")
    return path


def energy_kwh_per_day(app, start=date(2023, 1, 2), n_days=28, dt_h=0.25, seed=0):
    crit, flex = lm.house_load_profile([app], start, n_days, dt_h, np.random.default_rng(seed))
    return (crit + flex).sum() * dt_h / n_days, crit, flex


def by_hour(series, dt_h=0.25):
    """kWh per hour of the day, summed over all days."""
    spd = round(24 / dt_h)
    return series.reshape(-1, spd).sum(axis=0).reshape(24, -1).sum(axis=1) * dt_h


def iv(text):
    return lm.parse_intervals(text)


# ----------------------------------------------------------------------------- CSV

def test_committed_catalog_parses():
    catalog = lm.load_catalog()
    names = [device.appliance.dispozitiv for device in catalog.devices]
    assert len(names) == len(set(names))
    assert {device.appliance.mod for device in catalog.devices} == set(lm.MODES)
    always = {device.appliance.dispozitiv for device in catalog.devices if device.probabilitate == 1}
    assert {"frigider", "router și standby"} <= always
    hob = next(device for device in catalog.devices if device.appliance.dispozitiv == "plită electrică")
    assert hob.appliance.ore_pe_zi == pytest.approx(0.25) and hob.pe_persoana       # written as 0,25 (Excel RO)
    lights = next(device.appliance for device in catalog.devices if device.appliance.dispozitiv == "iluminat")
    assert lights.intervale == ((6, 8, 20), (17, 24, 80))
    assert min(catalog.persoane) >= 1 and sum(catalog.ponderi) == pytest.approx(1)


def test_committed_houses_are_plausible():
    houses = lm.compose_houses(range(1, 11))
    annual = np.array([house.kwh_per_year() for house in houses])
    assert (annual > 800).all() and (annual < 12000).all()
    assert 2000 < annual.mean() < 7000


def test_parse_interval_and_wrap():
    assert lm.parse_interval("18-23") == (18.0, 23.0)
    assert lm.parse_interval("0-24") == (0.0, 24.0)
    assert lm.parse_interval("22-6") == (22.0, 30.0)
    with pytest.raises(ValueError):
        lm.parse_interval("18")
    with pytest.raises(ValueError):
        lm.parse_interval("25-3")


def test_parse_weighted_intervals():
    assert iv("8-12:40 17-22:60") == ((8, 12, 40), (17, 22, 60))
    assert iv("0-24") == ((0, 24, 100),)
    assert iv("18-24:40 0-7:60") == ((18, 24, 40), (0, 7, 60))
    assert iv("22-6:1,5  9-10") == ((22, 30, 1.5), (9, 10, 100))
    app = lm.Appliance("x", 100, "zilnic", 2, intervale=iv("8-12:40 17-22:60"))
    assert [share for _, _, share in app.windows] == pytest.approx([0.4, 0.6])
    for text in ("8-12:40 17-22:60", "22-6", "6-8:20 17-24:80", "7-9:1 12-14:2,5"):
        assert lm.parse_intervals(lm.format_intervals(iv(text))) == iv(text)
    assert lm.describe_intervals(iv("8-12:40 17-22:60")) == "8-12 (40%), 17-22 (60%)"
    assert lm.describe_intervals(iv("22-6")) == "22-6"
    for bad in ("", "8-12:0", "8-12:-1", "8-12:abc", "8-12 25-26"):
        with pytest.raises(ValueError):
            lm.parse_intervals(bad)


def test_bad_rows_report_the_line(tmp_path):
    ok = "frigider;45;continuu;;;;0-24;tot_anul;1;nu;nu"
    for bad, text in [
        ("tv;100;uneori;2;;;18-23;tot_anul;1;nu;nu", "mod"),
        ("tv;100;zilnic;8;;;18-23;tot_anul;1;nu;nu", "intervalul 18-23"),
        ("tv;100;zilnic;5;;;8-18:10 18-19:90;tot_anul;1;nu;nu", "4.5 h din ore_pe_zi cad in intervalul 18-19"),
        ("tv;100;zilnic;2;;;18-23;tot_anul;1;nu;poate", "flexibil"),
        ("tv;100;zilnic;2;;;18-23;tot_anul;1;poate;nu", "pe_persoana"),
        ("tv;100;zilnic;2;;;18-23;tot_anul;1,5;nu;nu", "probabilitate"),
        ("tv;100;zilnic;2;;;18-23;tot_anul;;nu;nu", "probabilitate"),
        ("tv;100;zilnic;2;;;18-23:0;tot_anul;1;nu;nu", "ponderea"),
        ("masina;700;ciclic;;0;90;8-21;tot_anul;1;da;da", "ciclic"),
        ("tv;abc;zilnic;2;;;18-23;tot_anul;1;nu;nu", "numar"),
    ]:
        with pytest.raises(ValueError, match=f"randul 3.*{text}"):
            lm.load_devices(write_csv(tmp_path / "d.csv", [ok, bad]))
    (tmp_path / "h.csv").write_text("casa;dispozitiv\n1;frigider\n", encoding="utf-8")
    with pytest.raises(ValueError, match="antetul"):
        lm.load_devices(tmp_path / "h.csv")


def test_per_person_hours_must_fit_for_the_largest_household(tmp_path):
    row = "laptop;60;zilnic;0,5;;;18-20;tot_anul;1;da;nu"
    path = write_csv(tmp_path / "d.csv", [row])
    assert lm.load_devices(path, max_people=4)
    with pytest.raises(ValueError, match="randul 2: pentru 5 persoane: 2.5 h"):
        lm.load_devices(path, max_people=5)
    households = write_csv(tmp_path / "g.csv", ["1;50", "5;50"], header="persoane;pondere")
    with pytest.raises(ValueError, match="pentru 5 persoane"):
        lm.load_catalog(path, households)


def test_households_file(tmp_path):
    people, weights = lm.load_households(write_csv(tmp_path / "g.csv", ["1;25", "2;75", ";"], "persoane;pondere"))
    assert people == (1, 2) and weights == pytest.approx((0.25, 0.75))
    for bad, text in [("0;10", "persoane"), ("2,5;10", "persoane"), ("2;0", "pondere"), ("1;5", "de doua ori")]:
        with pytest.raises(ValueError, match=f"randul 3.*{text}"):
            lm.load_households(write_csv(tmp_path / "g.csv", ["1;25", bad], "persoane;pondere"))
    with pytest.raises(ValueError, match="antetul"):
        lm.load_households(write_csv(tmp_path / "g.csv", ["1;25"], "pers;pondere"))


def test_blank_lines_and_comma_decimals(tmp_path):
    devices = lm.load_devices(write_csv(tmp_path / "d.csv", [
        "plită;1500;zilnic;0,8;;;11-21;tot_anul;0,6;da;nu", ";;;;;;;;;;", "boiler;2000;ciclic;;3,5;45;6-22;;1;;da",
    ]))
    assert len(devices) == 2
    assert devices[0].appliance.ore_pe_zi == pytest.approx(0.8) and devices[0].probabilitate == pytest.approx(0.6)
    boiler = devices[1]
    assert boiler.appliance.cicluri_pe_saptamana == pytest.approx(3.5)
    assert boiler.appliance.sezon == "tot_anul" and boiler.appliance.flexibil and not boiler.pe_persoana


# ----------------------------------------------------------------------------- energy consistency

def test_continuous_is_constant():
    app = lm.Appliance("frigider", 45, "continuu")
    kwh, crit, flex = energy_kwh_per_day(app, n_days=3)
    assert np.allclose(crit, 0.045) and np.allclose(flex, 0)
    assert kwh == pytest.approx(0.045 * 24)


@pytest.mark.parametrize("dt_h", [0.25, 1.0])
def test_daily_block_energy(dt_h):
    app = lm.Appliance("iluminat", 100, "zilnic", ore_pe_zi=5, intervale=iv("17-23"))
    kwh, crit, _ = energy_kwh_per_day(app, dt_h=dt_h)
    assert kwh == pytest.approx(0.5, rel=0.05)                       # 100 W x 5 h
    hourly = by_hour(crit, dt_h)
    assert hourly[:17].sum() == 0 and hourly[23:].sum() == 0


def test_daily_hours_are_split_over_the_intervals_by_weight():
    app = lm.Appliance("iluminat", 100, "zilnic", ore_pe_zi=5, intervale=iv("6-8:20 17-24:80"))
    kwh, crit, _ = energy_kwh_per_day(app, n_days=56)
    assert kwh == pytest.approx(0.5, rel=0.03)
    hourly = by_hour(crit) / 56
    assert hourly[6:8].sum() == pytest.approx(0.1, rel=0.05)          # 20 % of 5 h x 100 W, every day
    assert hourly[17:24].sum() == pytest.approx(0.4, rel=0.05)
    assert hourly[:6].sum() == 0 and hourly[8:17].sum() == 0
    days = crit.reshape(56, -1)
    assert (days[:, 24:32].sum(axis=1) > 0).all() and (days[:, 68:].sum(axis=1) > 0).all()   # one block in each


def test_cyclic_energy_and_count():
    app = lm.Appliance("mașină de spălat", 700, "ciclic", cicluri_pe_saptamana=4, durata_ciclu_min=90,
                       intervale=iv("8-21"), flexibil=True)
    kwh, crit, flex = energy_kwh_per_day(app)
    assert kwh == pytest.approx(0.7 * 4 / 7 * 1.5, rel=0.05)
    assert crit.sum() == 0 and (flex >= 0).all()


def test_cycles_pick_an_interval_with_its_weight():
    app = lm.Appliance("boiler", 1000, "ciclic", cicluri_pe_saptamana=14, durata_ciclu_min=30,
                       intervale=iv("6-9:25 18-21:75"), flexibil=True)
    n_days = 364
    kwh, _, flex = energy_kwh_per_day(app, n_days=n_days)
    assert kwh == pytest.approx(1.0, rel=0.03)                       # 2 cycles x 0.5 h x 1 kW
    hourly = by_hour(flex)
    morning, evening = hourly[6:10].sum(), hourly[18:22].sum()
    assert morning + evening == pytest.approx(hourly.sum())
    assert morning / (morning + evening) == pytest.approx(0.25, abs=0.03)   # 728 cycles, sd ~ 0.016


def test_thermal_energy_follows_the_season():
    app = lm.Appliance("pompă de căldură", 2500, "termic", ore_pe_zi=6, intervale=iv("0-24"), sezon="iarna")
    winter, _, _ = energy_kwh_per_day(app, start=date(2023, 1, 2))
    shoulder, _, _ = energy_kwh_per_day(app, start=date(2023, 4, 3))
    summer, _, _ = energy_kwh_per_day(app, start=date(2023, 7, 3))
    assert winter == pytest.approx(15.0, rel=0.05)
    assert shoulder == pytest.approx(7.5, rel=0.05)
    assert summer == 0
    ac = lm.Appliance("aer condiționat", 1200, "termic", ore_pe_zi=4, intervale=iv("12-23"), sezon="vara")
    assert energy_kwh_per_day(ac, start=date(2023, 7, 3))[0] == pytest.approx(4.8, rel=0.05)
    assert energy_kwh_per_day(ac, start=date(2023, 1, 2))[0] == 0
    assert app.kwh_per_year() == pytest.approx(15 * 151 + 7.5 * 122)


def test_thermal_hours_are_split_over_the_intervals_by_weight():
    app = lm.Appliance("radiator", 1500, "termic", ore_pe_zi=3, intervale=iv("6-9:30 17-23:70"), sezon="iarna")
    kwh, crit, _ = energy_kwh_per_day(app, n_days=56)
    assert kwh == pytest.approx(4.5, rel=0.03)
    hourly = by_hour(crit) / 56
    assert hourly[6:9].sum() == pytest.approx(0.3 * 4.5, rel=0.05)
    assert hourly[17:23].sum() == pytest.approx(0.7 * 4.5, rel=0.05)


def test_season_and_factor():
    assert [lm.season_of(date(2023, m, 15)) for m in (1, 3, 4, 5, 6, 8, 9, 10, 11, 12)] == [
        "iarna", "iarna", "intermediar", "intermediar", "vara", "vara", "intermediar", "intermediar", "iarna", "iarna",
    ]
    assert lm.thermal_factor("tot_anul", "vara") == 1.0
    assert lm.thermal_factor("iarna", "intermediar") == 0.5
    assert lm.thermal_factor("vara", "iarna") == 0.0


def test_interval_wrapping_midnight():
    ev = lm.Appliance("EV", 7000, "ciclic", cicluri_pe_saptamana=7, durata_ciclu_min=60, intervale=iv("22-6"),
                      flexibil=True)
    kwh, _, flex = energy_kwh_per_day(ev)
    assert kwh == pytest.approx(7.0, rel=0.05)
    by_step = flex.reshape(-1, 96).sum(axis=0)
    assert by_step[4 * 7 : 4 * 22].sum() == 0                          # nothing between 07:00 and 22:00
    assert by_step[: 4 * 6].sum() > 0 and by_step[4 * 22 :].sum() > 0  # runs on both sides of midnight
    night = lm.Appliance("veioză", 50, "zilnic", ore_pe_zi=3, intervale=iv("22-6"))
    kwh, crit, _ = energy_kwh_per_day(night)
    assert kwh == pytest.approx(0.15, rel=0.05)
    assert crit.reshape(-1, 96).sum(axis=0)[4 * 7 : 4 * 22].sum() == 0


def test_flexible_split_and_house_profile():
    apps = [lm.Appliance("frigider", 100, "continuu"),
            lm.Appliance("boiler", 2000, "ciclic", cicluri_pe_saptamana=7, durata_ciclu_min=60, flexibil=True)]
    crit, flex = lm.house_load_profile(apps, date(2023, 1, 2), 7, 0.25, np.random.default_rng(1))
    assert crit.shape == flex.shape == (7 * 96,)
    assert np.allclose(crit, 0.1)
    assert flex.sum() * 0.25 == pytest.approx(7 * 2.0, rel=0.05)


def test_profile_is_seeded():
    apps = lm.compose_house(1, lm.load_catalog()).appliances
    a = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(3))
    b = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(3))
    c = lm.house_load_profile(apps, date(2023, 1, 2), 2, 0.25, np.random.default_rng(4))
    np.testing.assert_array_equal(a[0], b[0])
    assert not np.array_equal(a[0], c[0])


# ----------------------------------------------------------------------------- composition

def test_per_person_values_are_multiplied():
    washer = lm.CatalogDevice(lm.Appliance("mașină de spălat", 700, "ciclic", cicluri_pe_saptamana=1.2,
                                           durata_ciclu_min=90), pe_persoana=True)
    laptop = lm.CatalogDevice(lm.Appliance("laptop", 60, "zilnic", ore_pe_zi=1.5), pe_persoana=True)
    tv = lm.CatalogDevice(lm.Appliance("televizor", 100, "zilnic", ore_pe_zi=3))
    assert washer.for_people(3).cicluri_pe_saptamana == pytest.approx(3.6)
    assert washer.for_people(3).durata_ciclu_min == 90
    assert laptop.for_people(4).ore_pe_zi == pytest.approx(6.0)
    assert tv.for_people(5) == tv.appliance
    catalog = lm.load_catalog()
    for house in lm.compose_houses(range(1, 31), catalog):
        for app in house.appliances:
            device = next(d for d in catalog.devices if d.appliance.dispozitiv == app.dispozitiv)
            factor = house.persoane if device.pe_persoana else 1
            assert app.ore_pe_zi == pytest.approx(device.appliance.ore_pe_zi * factor)
            assert app.cicluri_pe_saptamana == pytest.approx(device.appliance.cicluri_pe_saptamana * factor)
            assert app.kwh_per_year() == pytest.approx(device.for_people(house.persoane).kwh_per_year())


def test_composition_depends_only_on_the_house_id():
    catalog = lm.load_catalog()
    assert lm.compose_house(3, catalog) == lm.compose_house(3, lm.load_catalog())
    many = lm.compose_houses(range(1, 201), catalog)
    assert many[2] == lm.compose_house(3, catalog) and many[156] == lm.compose_house(157, catalog)
    assert len({(h.persoane, tuple(a.dispozitiv for a in h.appliances)) for h in many}) > 50
    assert lm.composition_rng(5).random() != lm.house_rng(lm.COMPOSITION_SEED, 5).random()


def test_composition_follows_the_probabilities():
    catalog = lm.load_catalog()
    houses = lm.compose_houses(range(1, 3001), catalog)
    people = np.array([house.persoane for house in houses])
    assert people.min() >= 1
    for count, weight in zip(catalog.persoane, catalog.ponderi, strict=True):
        assert np.mean(people == count) == pytest.approx(weight, abs=0.03)
    for device in catalog.devices:
        name = device.appliance.dispozitiv
        owned = np.mean([any(app.dispozitiv == name for app in house.appliances) for house in houses])
        if device.probabilitate == 1:
            assert owned == 1, name
        assert owned == pytest.approx(device.probabilitate, abs=0.03), name


def test_probability_zero_and_one(tmp_path):
    devices = write_csv(tmp_path / "d.csv", ["frigider;45;continuu;;;;0-24;tot_anul;1;nu;nu",
                                             "sauna;6000;zilnic;1;;;18-22;tot_anul;0;nu;nu"])
    catalog = lm.load_catalog(devices, write_csv(tmp_path / "g.csv", ["2;1"], "persoane;pondere"))
    for house in lm.compose_houses(range(1, 101), catalog):
        assert house.persoane == 2 and [app.dispozitiv for app in house.appliances] == ["frigider"]


# ----------------------------------------------------------------------------- community

def test_community_load_shapes_and_house_independence():
    crit, flex = lm.community_load(C, date(2023, 1, 10), 3, 0.5, seed=0)
    assert crit.shape == flex.shape == (10, 144)
    assert (crit > 0).all() and (flex >= 0).all()
    assert (crit + flex).sum(axis=1).min() * 0.5 > 3 * 1.5          # every house above 1.5 kWh/day
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
    always_on = sum(app.kw for app in house.appliances if app.mod == "continuu")
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
    expected = np.array([house.kwh_per_day("iarna") for house in lm.compose_houses(range(1, 11))])
    assert 1.5 < daily.min() and daily.max() < 40
    assert daily.mean() == pytest.approx(expected.mean(), rel=0.2)
    with pytest.raises(ValueError):
        generate_scenario_real(C, load_source="sintetic")


# ----------------------------------------------------------------------------- report

def test_year_report_matches_the_table(tmp_path):
    houses = [
        lm.House(1, 2, (lm.Appliance("frigider", 45, "continuu"),
                        lm.Appliance("boiler", 2000, "ciclic", cicluri_pe_saptamana=10, durata_ciclu_min=45,
                                     intervale=iv("6-9:50 18-23:50"), flexibil=True))),
        lm.House(2, 3, (lm.Appliance("frigider", 45, "continuu"),
                        lm.Appliance("iluminat", 90, "zilnic", ore_pe_zi=5, intervale=iv("6-8:20 17-24:80")),
                        lm.Appliance("mașină de vase", 900, "ciclic", cicluri_pe_saptamana=4, durata_ciclu_min=120,
                                     intervale=iv("13-15:20 19-23:80"), flexibil=True),
                        lm.Appliance("pompă de căldură", 2500, "termic", ore_pe_zi=6, sezon="iarna"))),
    ]
    year = lm.simulate_year(houses, 1.0, seed=0)
    rows = lm.house_rows(houses, year, 1.0)
    assert [(row["casa"], row["persoane"], row["dispozitive"]) for row in rows] == [(1, 2, 2), (2, 3, 4)]
    assert rows[1]["lista"] == "frigider, iluminat, mașină de vase, pompă de căldură"
    for row in rows:
        assert row["kwh_an"] == pytest.approx(row["kwh_an_calculat"], rel=0.03)
        assert row["kwh_an"] == pytest.approx(sum(row[f"kwh_an_{mode}"] for mode in lm.MODES))
        assert 0 < row["cota_flexibil"] < 1
    assert rows[1]["kwh_zi_iarna"] > 2 * rows[1]["kwh_zi_vara"]        # heat pump
    devices = lm.device_rows(houses)
    assert len(devices) == 6 and devices[1]["intervale"] == "6-9 (50%), 18-23 (50%)"
    assert sum(d["kwh_an"] for d in devices if d["casa"] == 2) == pytest.approx(rows[1]["kwh_an_calculat"])
    lm.daily_profile_chart(year, 1.0, tmp_path / "profil.png")
    lm.annual_chart(rows, tmp_path / "anual.png")
    assert (tmp_path / "profil.png").stat().st_size > 0 and (tmp_path / "anual.png").stat().st_size > 0
