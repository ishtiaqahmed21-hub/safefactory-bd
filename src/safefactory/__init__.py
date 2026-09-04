"""SafeFactory BD — an ISO 45001-aligned HSE management and site risk intelligence
system for Bangladeshi food and dairy manufacturing.

Modules
-------
risk        5x5 HIRA/JSA scoring, hierarchy of controls, risk-reduction analytics
incidents   Incident register, classification, LTIFR / TRIR / DART / severity rate
ptw         Permit-to-Work and Lockout-Tagout workflow with validity and audit logic
compliance  ISO 45001:2018 x Bangladesh legal compliance matrix and audit scoring
exposure    Ambient air-quality exposure analytics from the national hourly dataset
siteindex   Composite Site HSE Risk Index for industrial locations
quality     Automated integrity screening of the source air-quality dataset
"""

__version__ = "1.0.0"
__author__ = "Ishtiaq Ahmed"

from . import compliance, exposure, incidents, ptw, quality, risk, siteindex  # noqa: F401

__all__ = [
    "risk",
    "incidents",
    "ptw",
    "compliance",
    "exposure",
    "siteindex",
    "quality",
]
