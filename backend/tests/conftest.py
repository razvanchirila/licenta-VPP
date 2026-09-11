from datetime import date

import numpy as np

from vpp_core.scenario import Scenario


def make_scenario(pv, crit, flex=None, dt_h=1.0, price_import=None, price_export=None, price_p2p=None):
    """Scenario from explicit arrays. pv/crit/flex: (H, T); prices: (T,)."""
    pv = np.asarray(pv, dtype=float)
    crit = np.asarray(crit, dtype=float)
    flex = np.zeros_like(crit) if flex is None else np.asarray(flex, dtype=float)
    T = pv.shape[1]
    price_import = np.full(T, 1.0) if price_import is None else np.asarray(price_import, dtype=float)
    price_export = np.full(T, 0.3) if price_export is None else np.asarray(price_export, dtype=float)
    price_p2p = 0.7 * price_import if price_p2p is None else np.asarray(price_p2p, dtype=float)
    return Scenario(
        dt_h=dt_h, start=date(2025, 6, 1), pv_kw=pv, load_crit_kw=crit, load_flex_kw=flex,
        price_import=price_import, price_export=price_export, price_p2p=price_p2p,
    )


def const(H, T, value):
    return np.full((H, T), float(value))
