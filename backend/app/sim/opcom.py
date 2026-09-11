"""
OPCOM API Integration - Fetch real electricity prices from Romanian energy market
"""
import pandas as pd
import requests
from datetime import datetime
from typing import List, Optional
import io


def fetch_opcom_prices(date: datetime = None) -> List[float]:
    """
    Fetch real electricity prices from OPCOM for a specific date
    
    OPCOM (Operatorul Pieței de Energie Electrică) is the Romanian electricity market operator.
    This function fetches the day-ahead market prices (PZU - Piața pentru Ziua Următoare).
    
    Args:
        date: Date to fetch prices for. If None, uses today's date.
    
    Returns:
        List of 24 hourly prices in lei/kWh (converted from lei/MWh)
        
    Raises:
        requests.HTTPError: If the API request fails
        ValueError: If the CSV data cannot be parsed
    """
    if date is None:
        date = datetime.now()
    
    # Format URL: DD/MM/YYYY
    url = f"https://www.opcom.ro/rapoarte-pzu-raportPIP-export-csv/{date.day:02d}/{date.month:02d}/{date.year}/ro"
    params = {"resolution": "60"}  # PT60M - hourly intervals
    
    try:
        # Fetch CSV data
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse CSV using pandas
        df = pd.read_csv(io.StringIO(response.text))
        
        # Extract prices column: "Pret mediu [lei/MWh]"
        if 'Pret mediu [lei/MWh]' not in df.columns:
            raise ValueError("Expected column 'Pret mediu [lei/MWh]' not found in OPCOM data")
        
        prices_lei_per_mwh = df['Pret mediu [lei/MWh]'].tolist()
        
        if len(prices_lei_per_mwh) != 24:
            raise ValueError(f"Expected 24 hourly prices, got {len(prices_lei_per_mwh)}")
        
        # Convert from lei/MWh to lei/kWh
        # 1 MWh = 1000 kWh
        prices_lei_per_kwh = [
            price_lei_mwh / 1000.0
            for price_lei_mwh in prices_lei_per_mwh
        ]
        
        return prices_lei_per_kwh
        
    except requests.RequestException as e:
        raise requests.HTTPError(f"Failed to fetch OPCOM prices: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse OPCOM data: {str(e)}")


def fetch_opcom_prices_raw(date: datetime = None) -> dict:
    """
    Fetch raw OPCOM data including prices in original lei/MWh format
    
    Args:
        date: Date to fetch prices for. If None, uses today's date.
    
    Returns:
        Dictionary with:
        - date: Date string (DD/MM/YYYY)
        - prices_lei_mwh: List of 24 prices in lei/MWh
        - prices_lei_kwh: List of 24 prices in lei/kWh (converted)
        - resolution: "PT60M"
        - min_price: Minimum price (lei/MWh)
        - max_price: Maximum price (lei/MWh)
        - avg_price: Average price (lei/MWh)
    """
    if date is None:
        date = datetime.now()
    
    url = f"https://www.opcom.ro/rapoarte-pzu-raportPIP-export-csv/{date.day:02d}/{date.month:02d}/{date.year}/ro"
    params = {"resolution": "60"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text))
        
        if 'Pret mediu [lei/MWh]' not in df.columns:
            raise ValueError("Expected column 'Pret mediu [lei/MWh]' not found in OPCOM data")
        
        prices_lei_mwh = df['Pret mediu [lei/MWh]'].tolist()
        
        if len(prices_lei_mwh) != 24:
            raise ValueError(f"Expected 24 hourly prices, got {len(prices_lei_mwh)}")
        
        # Convert to lei/kWh
        prices_lei_kwh = [
            price_lei_mwh / 1000.0
            for price_lei_mwh in prices_lei_mwh
        ]
        
        return {
            "date": f"{date.day:02d}/{date.month:02d}/{date.year}",
            "prices_lei_mwh": prices_lei_mwh,
            "prices_lei_kwh": prices_lei_kwh,
            "resolution": "PT60M",
            "min_price": min(prices_lei_mwh),
            "max_price": max(prices_lei_mwh),
            "avg_price": sum(prices_lei_mwh) / len(prices_lei_mwh)
        }
        
    except requests.RequestException as e:
        raise requests.HTTPError(f"Failed to fetch OPCOM prices: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse OPCOM data: {str(e)}")


def is_opcom_available(date: datetime = None) -> bool:
    """
    Check if OPCOM data is available for a given date
    
    Args:
        date: Date to check. If None, uses today's date.
    
    Returns:
        True if data is available, False otherwise
    """
    try:
        fetch_opcom_prices(date)
        return True
    except:
        return False
