"""NSW Fuel Check API."""

from .client import (
    NSWFuelApiClient,
    NSWFuelApiClientAuthError,
    NSWFuelApiClientConnectionError,
    NSWFuelApiClientError,
)
from .dto import (
    GetFuelPricesResponse,
    GetReferenceDataResponse,
    Price,
    Station,
    StationPrice,
)

__all__ = [
    "GetFuelPricesResponse",
    "GetReferenceDataResponse",
    "NSWFuelApiClient",
    "NSWFuelApiClientAuthError",
    "NSWFuelApiClientConnectionError",
    "NSWFuelApiClientError",
    "Price",
    "Station",
    "StationPrice",
]
