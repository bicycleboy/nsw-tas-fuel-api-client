"""Fixtures for NSW Fuel Check API Client tests."""

import json
import os
import re

import aiohttp
import pytest

from nsw_tas_fuel.const import AUTH_ENDPOINT

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
ALL_PRICES_FILE = os.path.join(FIXTURES_DIR, "all_prices.json")
LOVS_FILE = os.path.join(FIXTURES_DIR, "lovs.json")


@pytest.fixture
async def session():
    """Function-scoped aiohttp session for each test."""
    async with aiohttp.ClientSession() as sess:
        yield sess


@pytest.fixture
def mock_token(aiointercept_mock):
    """Mock the FuelCheck API token endpoint and hand back the mock for further registrations."""
    token_resp = {"access_token": "testtoken", "expires_in": 3600}

    # No trailing $ anchor: the real request appends ?grant_type=client_credentials
    auth_url = f"^{re.escape(aiointercept_mock.server_url)}{re.escape(AUTH_ENDPOINT)}"
    aiointercept_mock.get(re.compile(auth_url), payload=token_resp)

    return aiointercept_mock


@pytest.fixture
def all_prices_data() -> dict:
    """Load the all_prices.json fixture file as parsed JSON."""
    with open(ALL_PRICES_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def lovs_data() -> dict:
    """Load the lovs.json fixture file as parsed JSON."""
    with open(LOVS_FILE, encoding="utf-8") as f:
        return json.load(f)
