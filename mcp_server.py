#!/usr/bin/env python3
"""
FastMCP Server for Whirlpool Sixth Sense Appliances

This server provides tools and resources for interacting with Whirlpool washer/dryer
appliances through the Model Context Protocol (MCP) using FastMCP framework.
"""

import argparse
import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import aiohttp
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector, Brand, Region
from whirlpool.washerdryer import WasherDryer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


@dataclass
class AppContext:
    session: aiohttp.ClientSession
    auth: Auth
    appliance_manager: AppliancesManager
    backend_selector: BackendSelector


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Get configuration from environment variables
    email = os.getenv("WHIRLPOOL_EMAIL")
    password = os.getenv("WHIRLPOOL_PASSWORD")
    brand = os.getenv("WHIRLPOOL_BRAND", "whirlpool")
    region = os.getenv("WHIRLPOOL_REGION", "EU")

    if not email or not password:
        raise ValueError("WHIRLPOOL_EMAIL and WHIRLPOOL_PASSWORD must be set")

    # Initialize on startup
    session = aiohttp.ClientSession()
    appliance_manager = None

    try:
        # Parse brand
        try:
            selected_brand = Brand[brand.title()]
        except KeyError:
            valid_brands = [b.name.lower() for b in Brand]
            raise ValueError(
                f"Invalid brand: {brand}. Valid options: {valid_brands}"
            ) from None

        # Parse region
        try:
            selected_region = Region[region.upper()]
        except KeyError:
            valid_regions = [r.name for r in Region]
            raise ValueError(
                f"Invalid region: {region}. Valid options: {valid_regions}"
            ) from None

        backend_selector = BackendSelector(selected_brand, selected_region)
        auth = Auth(backend_selector, email, password, session)
        await auth.do_auth(store=False)

        appliance_manager = AppliancesManager(backend_selector, auth, session)
        if not await appliance_manager.fetch_appliances():
            raise RuntimeError("Could not fetch appliances")
        await appliance_manager.connect()

        yield AppContext(
            session=session,
            auth=auth,
            appliance_manager=appliance_manager,
            backend_selector=backend_selector,
        )
    finally:
        # Cleanup on shutdown
        if appliance_manager:
            await appliance_manager.disconnect()
        await session.close()


# Create the FastMCP server
mcp = FastMCP("whirlpool-sixth-sense", lifespan=app_lifespan)


def _get_app_context() -> AppContext:
    """Get application context from MCP server"""
    ctx = mcp.get_context()
    return ctx.request_context.lifespan_context  # type: ignore[return-value]


def _find_appliance(app_ctx: AppContext, appliance_id: str) -> WasherDryer | None:
    """Find appliance by SAID"""
    for appliance in app_ctx.appliance_manager.washer_dryers:
        if appliance.said == appliance_id:
            return appliance
    return None


@mcp.tool()
def list_appliances() -> str:
    """List all available washer/dryer appliances"""
    app_ctx = _get_app_context()

    appliances = []
    for appliance in app_ctx.appliance_manager.washer_dryers:
        appliances.append(
            {"said": appliance.said, "name": appliance.name, "type": "washer_dryer"}
        )

    return json.dumps(appliances, indent=2)


@mcp.tool()
def get_status(appliance_id: str) -> str:
    """Get comprehensive status of a specific appliance"""
    app_ctx = _get_app_context()
    appliance = _find_appliance(app_ctx, appliance_id)

    if not appliance:
        return f"Appliance {appliance_id} not found"

    status = {
        "appliance_id": appliance_id,
        "name": appliance.name,
        "online": appliance.get_online(),
        "machine_state": str(appliance.get_machine_state()),
        "cycle_status": {
            "sensing": appliance.get_cycle_status_sensing(),
            "filling": appliance.get_cycle_status_filling(),
            "soaking": appliance.get_cycle_status_soaking(),
            "washing": appliance.get_cycle_status_washing(),
            "rinsing": appliance.get_cycle_status_rinsing(),
            "spinning": appliance.get_cycle_status_spinning(),
        },
        "time_remaining": appliance.get_time_remaining(),
        "door_open": appliance.get_door_open(),
        "dispense_1_level": appliance.get_dispense_1_level(),
    }

    return json.dumps(status, indent=2)


@mcp.tool()
async def refresh_data(appliance_id: str) -> str:
    """Refresh appliance data from Whirlpool servers"""
    app_ctx = _get_app_context()
    appliance = _find_appliance(app_ctx, appliance_id)

    if not appliance:
        return f"Appliance {appliance_id} not found"

    success = await appliance.fetch_data()
    if success:
        return get_status(appliance_id)

    return f"Failed to refresh data for appliance {appliance_id}"


@mcp.tool()
async def send_command(appliance_id: str, attributes: dict[str, Any]) -> str:
    """Send custom command/attributes to appliance"""
    app_ctx = _get_app_context()
    appliance = _find_appliance(app_ctx, appliance_id)

    if not appliance:
        return f"Appliance {appliance_id} not found"

    # Convert all values to strings as expected by the API
    str_attributes = {k: str(v) for k, v in attributes.items()}

    success = await appliance.send_attributes(str_attributes)
    if success:
        return f"Successfully sent command to {appliance_id}: {str_attributes}"

    return f"Failed to send command to {appliance_id}"


@mcp.tool()
def get_machine_state(appliance_id: str) -> str:
    """Get human-readable machine state of appliance"""
    app_ctx = _get_app_context()
    appliance = _find_appliance(app_ctx, appliance_id)

    if not appliance:
        return f"Appliance {appliance_id} not found"

    state = appliance.get_machine_state()
    return str(state) if state else "Unknown state"


@mcp.resource("whirlpool://appliances")
def get_appliances_resource() -> str:
    """List of all connected washer/dryer appliances"""
    return list_appliances()


@mcp.resource("whirlpool://status/{appliance_id}")
def get_status_resource(appliance_id: str) -> str:
    """Current status of specific appliance"""
    return get_status(appliance_id)


@mcp.resource("whirlpool://raw/{appliance_id}")
def get_raw_resource(appliance_id: str) -> str:
    """Raw API data for specific appliance"""
    app_ctx = _get_app_context()
    appliance = _find_appliance(app_ctx, appliance_id)

    if not appliance:
        return f"Appliance {appliance_id} not found"

    return json.dumps(appliance._data_dict, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whirlpool FastMCP Server")
    parser.add_argument(
        "--transport",
        default="sse",
        choices=["sse", "stdio"],
        help="Transport protocol",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")

    args = parser.parse_args()

    # Configure server settings
    mcp.settings.host = args.host
    mcp.settings.port = args.port

    # Run the server
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse")
