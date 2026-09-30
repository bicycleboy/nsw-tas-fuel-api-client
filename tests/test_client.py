"""Unit Test NSW Fuel Check API Client."""

import json
import re
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from nsw_tas_fuel.client import (
    NSWFuelApiClient,
    NSWFuelApiClientAuthError,
    NSWFuelApiClientConnectionError,
    NSWFuelApiClientError,
)
from nsw_tas_fuel.const import (
    AUTH_ENDPOINT,
    NEARBY_ENDPOINT,
    PRICE_ENDPOINT,
    PRICES_ENDPOINT,
    PRICES_NEW_ENDPOINT,
    REFERENCE_ENDPOINT,
)

PRICE_METHODS = [
    pytest.param(
        "get_fuel_prices",
        PRICES_ENDPOINT,
        id="all",
    ),
    pytest.param(
        "get_fuel_prices_new",
        PRICES_NEW_ENDPOINT,
        id="new",
    ),
]

STATION_PRICE_CASES = [
    pytest.param(
        "1000",
        None,
        146.9,
        150.0,
        id="nsw",
    ),
    pytest.param(
        "100",
        "TAS",
        186.9,
        180.0,
        id="tas",
    ),
]


@pytest.fixture
def client(session, aiointercept_mock) -> NSWFuelApiClient:
    """NSWFuelApiClient using default test credentials."""
    return NSWFuelApiClient(
        session=session,
        client_id="key",
        client_secret="secret",
        base_url=aiointercept_mock.server_url,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name, endpoint", PRICE_METHODS)
async def test_get_fuel_prices(
    client,
    mock_token,
    all_prices_data,
    method_name,
    endpoint,
) -> None:
    """
    Test fetching fuel prices from both all and new endpoints.

    When running this case and all others within HA devcontainer run
    with:

    pytest -p no:homeassistant tests/test_client.py

    to avoid homeassistant blocking sockets
    """
    url = f"{mock_token.server_url}{endpoint}"

    mock_token.get(url, payload=all_prices_data)

    method = getattr(client, method_name)
    response = await method()

    assert len(response.stations) == 2
    assert len(response.prices) == 5
    assert response.stations[0].name == "Cool Fuel Brand Hurstville"
    assert response.stations[1].name == "Fake Fuel Brand Kogarah"
    assert response.stations[1].au_state == "NSW"
    assert round(response.stations[1].latitude, 0) == -31
    assert round(response.stations[1].longitude, 0) == 152
    assert response.prices[0].fuel_type == "DL"
    assert response.prices[1].fuel_type == "E10"
    assert response.prices[1].station_code == 1
    assert response.prices[3].fuel_type == "P95"
    assert response.prices[3].station_code == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "station_code, state, expected_e10_price, expected_p95_price",
    STATION_PRICE_CASES,
)
async def test_get_fuel_prices_for_station(
    client,
    mock_token,
    station_code,
    state,
    expected_e10_price,
    expected_p95_price,
) -> None:
    """Test fetching prices for a single station.  Test NSW and TAS."""
    url = f"{mock_token.server_url}{PRICE_ENDPOINT.format(station_code=station_code)}"

    if state is not None:
        url += f"?state={state}"

    mock_token.get(
        url,
        payload={
            "prices": [
                {
                    "fueltype": "E10",
                    "price": expected_e10_price,
                    "lastupdated": "02/06/2018 02:03:04",
                },
                {
                    "fueltype": "P95",
                    "price": expected_p95_price,
                    "lastupdated": "02/06/2018 02:03:04",
                },
            ]
        },
    )

    result = await client.get_fuel_prices_for_station(
        station_code,
        state=state,
    )

    assert len(result) == 2
    assert result[0].fuel_type == "E10"
    assert result[0].price == expected_e10_price
    assert result[0].last_updated == datetime(
        day=2,
        month=6,
        year=2018,
        hour=2,
        minute=3,
        second=4)


@pytest.mark.asyncio
async def test_get_fuel_prices_within_radius(client, mock_token) -> None:
    """Test fetching prices within radius."""
    url = f"{mock_token.server_url}{NEARBY_ENDPOINT}"

    mock_token.post(
        url,
        payload={
            "stations": [
                {
                    "stationid": "SAAAAAA",
                    "brandid": "BAAAAAA",
                    "brand": "Cool Fuel Brand",
                    "code": 678,
                    "name": "Cool Fuel Brand Luxembourg",
                    "address": "123 Fake Street",
                    "location": {"latitude": -33.987, "longitude": 151.334},
                },
                {
                    "stationid": "SAAAAAB",
                    "brandid": "BAAAAAB",
                    "brand": "Fake Fuel Brand",
                    "code": 679,
                    "name": "Fake Fuel Brand Luxembourg",
                    "address": "123 Fake Street",
                    "location": {"latitude": -33.587, "longitude": 151.434},
                },
                {
                    "stationid": "SAAAAAB",
                    "brandid": "BAAAAAB",
                    "brand": "Fake Fuel Brand2",
                    "code": 880,
                    "name": "Fake Fuel Brand2 Luxembourg",
                    "address": "123 Fake Street",
                    "location": {"latitude": -33.687, "longitude": 151.234},
                },
            ],
            "prices": [
                {
                    "stationcode": 678,
                    "fueltype": "P95",
                    "price": 150.9,
                    "priceunit": "litre",
                    "description": None,
                    "lastupdated": "2018-06-02 00:46:31",
                },
                {
                    "stationcode": 678,
                    "fueltype": "P95",
                    "price": 130.9,
                    "priceunit": "litre",
                    "description": None,
                    "lastupdated": "2018-06-02 00:46:31",
                },
                {
                    "stationcode": 880,
                    "fueltype": "P95",
                    "price": 155.9,
                    "priceunit": "litre",
                    "description": None,
                    "lastupdated": "2018-06-02 00:46:31",
                },
            ],
        },
    )

    result = await client.get_fuel_prices_within_radius(
        latitude=-33.0, longitude=151.0, radius=10, fuel_type="E10"
    )

    assert len(result) == 3
    assert result[0].station.code == 678
    assert round(result[0].station.latitude, 3) == -33.987
    assert round(result[0].station.longitude, 3) == 151.334
    assert result[0].price.price == 150.9


@pytest.mark.asyncio
async def test_get_reference_data(client, mock_token, lovs_data) -> None:
    """Test fetching reference data."""
    url = f"{mock_token.server_url}{REFERENCE_ENDPOINT}"

    mock_token.get(url, payload=lovs_data)

    response = await client.get_reference_data()

    assert len(response.brands) == 2
    assert len(response.fuel_types) == 2
    assert len(response.stations) == 2
    assert len(response.trend_periods) == 2
    assert len(response.sort_fields) == 2
    assert response.brands[0] == "Cool Fuel Brand"
    assert response.fuel_types[0].code == "E10"
    assert response.fuel_types[0].name == "Ethanol 94"
    assert response.stations[0].name == "Cool Fuel Brand Hurstville"
    assert response.trend_periods[0].period == "Day"
    assert response.trend_periods[0].description == "Description for day"
    assert response.sort_fields[0].code == "Sort 1"
    assert response.sort_fields[0].name == "Sort field 1"


@pytest.mark.asyncio
async def test_get_fuel_prices_server_error(client, mock_token) -> None:
    """Test 500 server error for all fuel prices."""
    url = f"{mock_token.server_url}{PRICES_ENDPOINT}"
    mock_token.get(url, status=500, body="Internal Server Error")

    with pytest.raises(NSWFuelApiClientConnectionError) as exc:
        await client.get_fuel_prices()

    assert "Server error 500: Internal Server Error" in str(exc.value)


@pytest.mark.asyncio
async def test_get_fuel_prices_for_station_client_error(client, mock_token) -> None:
    """Test 400 client error for a single station."""
    station_code = "21199"
    url = f"{mock_token.server_url}{PRICE_ENDPOINT.format(station_code=station_code)}"
    mock_token.get(
        url,
        status=400,
        payload={
            "errorDetails": [
                {
                    "code": "E0014",
                    "description": f'Invalid service station code "{station_code}"',
                }
            ]
        },
    )

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_fuel_prices_for_station(station_code)

    assert f'Invalid service station code "{station_code}"' in str(exc.value)


@pytest.mark.asyncio
async def test_get_fuel_prices_within_radius_server_error(client, mock_token) -> None:
    """Test 500 server error for nearby fuel prices."""
    url = f"{mock_token.server_url}{NEARBY_ENDPOINT}"
    mock_token.post(url, status=500, body="Internal Server Error")

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_fuel_prices_within_radius(
            latitude=-33.0, longitude=151.0, radius=10, fuel_type="E10"
        )

    assert "Server error 500: Internal Server Error" in str(exc.value)


@pytest.mark.asyncio
async def test_get_reference_data_client_error(client, mock_token) -> None:
    """Test 400 client error for reference data."""
    url = f"{mock_token.server_url}{REFERENCE_ENDPOINT}"
    mock_token.get(
        url,
        status=400,
        payload={
            "errorDetails": {
                "code": "-2146233033",
                "message": "String was not recognized as a valid DateTime.",
            }
        },
    )

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_reference_data()

    assert "String was not recognized as a valid DateTime" in str(exc.value)


@pytest.mark.asyncio
async def test_get_reference_data_server_error(client, mock_token) -> None:
    """Test 500 server error for reference data."""
    url = f"{mock_token.server_url}{REFERENCE_ENDPOINT}"
    mock_token.get(url, status=500, body="Internal Server Error.")

    with pytest.raises(NSWFuelApiClientConnectionError) as exc:
        await client.get_reference_data()

    assert "Server error 500: Internal Server Error" in str(exc.value)


@pytest.mark.asyncio
async def test_get_fuel_price_timeout(client, mock_token) -> None:
    """Test timeout error for fetching fuel prices for a single station."""

    station_code = "21199"
    url = f"{mock_token.server_url}{PRICE_ENDPOINT.format(station_code=station_code)}"
    # client.py retries on 408, so the mock needs to retry
    mock_token.get(url, status=408, body="API timeout.", repeat=2)

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_fuel_prices_for_station(station_code)

    assert "Request timed out after retry" in str(exc.value)


@pytest.mark.asyncio
async def test_server_error_raises_connection_error(client, mock_token) -> None:
    """Test that a 500 server error raises NSWFuelApiClientConnectionError."""

    url = f"{mock_token.server_url}{PRICES_ENDPOINT}"
    mock_token.get(
        url,
        status=500,
        payload={"message": "Server error 500: Internal Server Error"},
    )

    with pytest.raises(NSWFuelApiClientConnectionError):
        await client.get_fuel_prices()


@pytest.mark.asyncio
async def test_invalid_client_credentials_token_fetch(
    session, aiointercept_mock
) -> None:
    """
    Test that invalid client_id/client_secret causes NSWFuelApiClientAuthError
    raised during token fetch (HTTP 401 from token endpoint).
    """
    auth_url = f"^{re.escape(aiointercept_mock.server_url)}{re.escape(AUTH_ENDPOINT)}"

    # Mock token URL to return 401 Unauthorized with JSON error message
    aiointercept_mock.get(
        re.compile(auth_url),
        status=401,
        body=json.dumps(
            {
                "error": "invalid_client",
                "error_description": "Invalid client credentials",
            }
        ),
        content_type="application/json",
    )

    # No need to mock fuel price URL since token fetch fails

    client = NSWFuelApiClient(
        session=session,
        client_id="bad_client_id",
        client_secret="bad_client_secret",
        base_url=aiointercept_mock.server_url,
    )

    with pytest.raises(NSWFuelApiClientAuthError) as exc:
        await client.get_fuel_prices()

    assert "Invalid NSW Fuel Check API credentials" in str(exc.value)


@pytest.mark.asyncio
async def test_async_get_token_invalid_json(client, aiointercept_mock) -> None:
    """Test handling of invalid JSON response during token fetch."""

    client._token = None  # force token refresh
    auth_url = rf"^{re.escape(aiointercept_mock.server_url)}{re.escape(AUTH_ENDPOINT)}"

    aiointercept_mock.get(
        re.compile(auth_url),
        status=200,
        content_type="application/json",
        body="not valid json!!!",
    )

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client._async_get_token()

    assert "Failed to parse token response JSON" in str(exc.value)


@pytest.mark.asyncio
async def test_get_fuel_prices_for_station_empty_response(client, monkeypatch) -> None:
    """Test handling of empty or malformed response for single station prices."""

    # Patch _async_request to return empty dict (missing "prices" key)
    monkeypatch.setattr(client, "_async_request", AsyncMock(return_value={}))

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_fuel_prices_for_station("12345")

    assert "malformed or empty" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_get_fuel_prices_within_radius_missing_keys(client, monkeypatch) -> None:
    """Test handling of missing keys in response for fuel prices within radius."""

    # Make _async_request return "{}" so both keys "stations" and "prices" are missing
    monkeypatch.setattr(client, "_async_request", AsyncMock(return_value={}))

    with pytest.raises(NSWFuelApiClientError) as exc:
        await client.get_fuel_prices_within_radius(
            latitude=-33.0, longitude=151.0, radius=10, fuel_type="E10"
        )

    # Ensure the error mentions missing keys
    assert (
        "station" in str(exc.value).lower()
        or "price" in str(exc.value).lower()
        or "location" in str(exc.value).lower()
    )
