"""
Global state management for the API
"""
from typing import Optional, List


class VPPState:
    """Global state for the VPP simulation"""
    
    def __init__(self):
        self.vpp: Optional['VPP'] = None  # The VPP instance
        self.profiles: Optional[dict] = None  # Generated profiles (PV, price, load)
        self.current_hour: int = 0  # Current simulation hour (0-23)
        self.simulation_history: List[dict] = []  # History of simulation steps


# Global singleton
vpp_state = VPPState()
