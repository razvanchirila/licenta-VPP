# Configuration for VPP Simulator

# All configuration values can now be modified from the web interface!


# Price thresholds (lei/kWh)
PRICE_LOW_THRESHOLD = 0.50   # ~500 lei/MWh
PRICE_HIGH_THRESHOLD = 1.50  # ~1500 lei/MWh

# VPP Grid Limits (kW)
P_GRID_IMPORT_MAX_KW = 2000.0
P_GRID_EXPORT_MAX_KW = 1500.0
P_INTERNAL_LINE_LIMIT_KW = 1000.0

# Battery defaults
BATTERY_CAPACITY_KWH = 20.0
BATTERY_SOC_MIN_RATIO = 0.2  # 20%
BATTERY_P_CH_MAX_KW = 5.0
BATTERY_P_DIS_MAX_KW = 5.0

# PV defaults
PV_CAPACITY_KW = 10.0

# Simulation
DT_HOURS = 1.0  # Time step in hours

# Trading
INTERNAL_PRICE_DISCOUNT = 0.8  # 20% discount for internal trading
