"""
Configuration API routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import app.config as config

router = APIRouter(prefix="/config", tags=["configuration"])


class ConfigUpdate(BaseModel):
    """Model for updating configuration values"""
    price_low_threshold: Optional[float] = Field(None, ge=0, description="Low price threshold (lei/kWh)")
    price_high_threshold: Optional[float] = Field(None, ge=0, description="High price threshold (lei/kWh)")
    p_grid_import_max_kw: Optional[float] = Field(None, ge=0, description="Max grid import power (kW)")
    p_grid_export_max_kw: Optional[float] = Field(None, ge=0, description="Max grid export power (kW)")
    p_internal_line_limit_kw: Optional[float] = Field(None, ge=0, description="Internal line limit (kW)")
    battery_capacity_kwh: Optional[float] = Field(None, ge=0, description="Battery capacity (kWh)")
    battery_soc_min_ratio: Optional[float] = Field(None, ge=0, le=1, description="Battery min SOC ratio (0-1)")
    battery_p_ch_max_kw: Optional[float] = Field(None, ge=0, description="Battery max charge power (kW)")
    battery_p_dis_max_kw: Optional[float] = Field(None, ge=0, description="Battery max discharge power (kW)")
    pv_capacity_kw: Optional[float] = Field(None, ge=0, description="PV capacity (kW)")
    internal_price_discount: Optional[float] = Field(None, ge=0, le=1, description="Internal price discount ratio (0-1)")


@router.get("")
def get_config():
    """
    Get current configuration values
    
    Returns:
        Dictionary with all configuration parameters
    """
    return {
        "price_thresholds": {
            "price_low_threshold": config.PRICE_LOW_THRESHOLD,
            "price_high_threshold": config.PRICE_HIGH_THRESHOLD
        },
        "vpp_grid_limits": {
            "p_grid_import_max_kw": config.P_GRID_IMPORT_MAX_KW,
            "p_grid_export_max_kw": config.P_GRID_EXPORT_MAX_KW,
            "p_internal_line_limit_kw": config.P_INTERNAL_LINE_LIMIT_KW
        },
        "battery_defaults": {
            "battery_capacity_kwh": config.BATTERY_CAPACITY_KWH,
            "battery_soc_min_ratio": config.BATTERY_SOC_MIN_RATIO,
            "battery_p_ch_max_kw": config.BATTERY_P_CH_MAX_KW,
            "battery_p_dis_max_kw": config.BATTERY_P_DIS_MAX_KW
        },
        "pv_defaults": {
            "pv_capacity_kw": config.PV_CAPACITY_KW
        },
        "trading": {
            "internal_price_discount": config.INTERNAL_PRICE_DISCOUNT
        }
    }


@router.put("")
def update_config(updates: ConfigUpdate):
    """
    Update configuration values
    
    Only provided values will be updated. Others remain unchanged.
    
    Args:
        updates: Configuration values to update
    
    Returns:
        Dictionary with updated configuration
    """
    updated_fields = []
    
    # Update price thresholds
    if updates.price_low_threshold is not None:
        config.PRICE_LOW_THRESHOLD = updates.price_low_threshold
        updated_fields.append("price_low_threshold")
    
    if updates.price_high_threshold is not None:
        config.PRICE_HIGH_THRESHOLD = updates.price_high_threshold
        updated_fields.append("price_high_threshold")
    
    # Update VPP grid limits
    if updates.p_grid_import_max_kw is not None:
        config.P_GRID_IMPORT_MAX_KW = updates.p_grid_import_max_kw
        updated_fields.append("p_grid_import_max_kw")
    
    if updates.p_grid_export_max_kw is not None:
        config.P_GRID_EXPORT_MAX_KW = updates.p_grid_export_max_kw
        updated_fields.append("p_grid_export_max_kw")
    
    if updates.p_internal_line_limit_kw is not None:
        config.P_INTERNAL_LINE_LIMIT_KW = updates.p_internal_line_limit_kw
        updated_fields.append("p_internal_line_limit_kw")
    
    # Update battery defaults
    if updates.battery_capacity_kwh is not None:
        config.BATTERY_CAPACITY_KWH = updates.battery_capacity_kwh
        updated_fields.append("battery_capacity_kwh")
    
    if updates.battery_soc_min_ratio is not None:
        config.BATTERY_SOC_MIN_RATIO = updates.battery_soc_min_ratio
        updated_fields.append("battery_soc_min_ratio")
    
    if updates.battery_p_ch_max_kw is not None:
        config.BATTERY_P_CH_MAX_KW = updates.battery_p_ch_max_kw
        updated_fields.append("battery_p_ch_max_kw")
    
    if updates.battery_p_dis_max_kw is not None:
        config.BATTERY_P_DIS_MAX_KW = updates.battery_p_dis_max_kw
        updated_fields.append("battery_p_dis_max_kw")
    
    # Update PV defaults
    if updates.pv_capacity_kw is not None:
        config.PV_CAPACITY_KW = updates.pv_capacity_kw
        updated_fields.append("pv_capacity_kw")
    
    # Update trading
    if updates.internal_price_discount is not None:
        config.INTERNAL_PRICE_DISCOUNT = updates.internal_price_discount
        updated_fields.append("internal_price_discount")
    
    # Validate thresholds
    if config.PRICE_LOW_THRESHOLD >= config.PRICE_HIGH_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail="price_low_threshold must be less than price_high_threshold"
        )
    
    return {
        "message": f"Configuration updated successfully. {len(updated_fields)} field(s) changed.",
        "updated_fields": updated_fields,
        "current_config": get_config()
    }


@router.post("/reset")
def reset_config():
    """
    Reset all configuration values to defaults
    
    Returns:
        Dictionary with default configuration values
    """
    # Price thresholds
    config.PRICE_LOW_THRESHOLD = 0.50
    config.PRICE_HIGH_THRESHOLD = 1.50
    
    # VPP Grid Limits
    config.P_GRID_IMPORT_MAX_KW = 2000.0
    config.P_GRID_EXPORT_MAX_KW = 1500.0
    config.P_INTERNAL_LINE_LIMIT_KW = 1000.0
    
    # Battery defaults
    config.BATTERY_CAPACITY_KWH = 20.0
    config.BATTERY_SOC_MIN_RATIO = 0.2
    config.BATTERY_P_CH_MAX_KW = 5.0
    config.BATTERY_P_DIS_MAX_KW = 5.0
    
    # PV defaults
    config.PV_CAPACITY_KW = 10.0
    
    # Trading
    config.INTERNAL_PRICE_DISCOUNT = 0.8
    
    return {
        "message": "Configuration reset to default values",
        "current_config": get_config()
    }
