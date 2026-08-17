"""
backend/app/telecom_tools.py
Proxy to workspace telecom_tools
"""
try:
    from telecom_tools import (
        track_network_status,
        detect_billing_anomalies,
        activate_sim_card,
        verify_kyc_status,
        dispatch_telecom_tools
    )
except ImportError:
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from telecom_tools import (
        track_network_status,
        detect_billing_anomalies,
        activate_sim_card,
        verify_kyc_status,
        dispatch_telecom_tools
    )
