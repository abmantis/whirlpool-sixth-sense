"""
AWS IoT Things API Client

Provides functionality to list and retrieve thing information from AWS IoT.
"""

import logging
import urllib.parse
from typing import Any

import aiohttp
import async_timeout

from .auth import Auth

LOGGER = logging.getLogger(__name__)

# TODO: move to BackendSelector
AWS_REGION = "us-east-2"
AWS_IOT_ENDPOINT = f"iot.{AWS_REGION}.amazonaws.com"


class Things:
    """Client for AWS IoT Things API operations."""

    def __init__(self, auth: Auth, session: aiohttp.ClientSession):
        """Initialize Things client."""
        self._auth = auth
        self._session = session

    async def list_things(self) -> list[dict[str, Any]]:
        """List things in the user's AWS IoT thing group."""
        identity_id = await self._auth.get_cognito_identity_id()
        group_name = identity_id.split(":")[1]

        uri = f"/thing-groups/{urllib.parse.quote(group_name, safe='')}/things"
        headers = await self._auth.create_signed_headers(
            host=AWS_IOT_ENDPOINT, uri=uri, service="iot"
        )
        url = f"https://{AWS_IOT_ENDPOINT}{uri}"

        all_things: list[str] = []
        next_token: str | None = None

        try:
            while True:
                # Add pagination token if present
                if next_token:
                    query_params = {"nextToken": next_token}
                    request_url = f"{url}?nextToken={urllib.parse.quote(next_token)}"
                    headers = await self._auth.create_signed_headers(
                        host=AWS_IOT_ENDPOINT,
                        uri=uri,
                        query_params=query_params,
                        service="iot",
                    )
                else:
                    request_url = url
                async with async_timeout.timeout(30):
                    async with self._session.get(
                        request_url, headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            LOGGER.error(
                                "Failed to list things: %s - %s",
                                response.status,
                                error_text,
                            )
                            break

                        data = await response.json()
                        things = data.get("things", [])
                        all_things.extend(things)
                        LOGGER.debug(
                            "Retrieved %d things from group %s", len(things), group_name
                        )

                        # Check for pagination
                        next_token = data.get("nextToken")
                        if not next_token:
                            break

        except TimeoutError:
            LOGGER.error("Timeout while listing things in group %s", group_name)
        except aiohttp.ClientError as e:
            LOGGER.error("HTTP error while listing things: %s", e)
        except Exception as e:
            LOGGER.error("Error listing things: %s", e)

        # Fetch full data for each thing
        things_with_data: list[dict[str, Any]] = []
        for thing_name in all_things:
            if thing_name:
                thing_data = await self.get_thing(thing_name)
                if thing_data:
                    things_with_data.append(thing_data)

        return things_with_data

    async def get_thing(self, thing_name: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific thing.

        This method uses the AWS IoT DescribeThing API to retrieve
        detailed information about a thing including its attributes.
        """
        uri = f"/things/{urllib.parse.quote(thing_name, safe='')}"
        headers = await self._auth.create_signed_headers(
            host=AWS_IOT_ENDPOINT, uri=uri, service="iot"
        )
        url = f"https://{AWS_IOT_ENDPOINT}{uri}"

        try:
            async with async_timeout.timeout(30):
                async with self._session.get(url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        LOGGER.error(
                            "Failed to get thing %s: %s - %s",
                            thing_name,
                            response.status,
                            error_text,
                        )
                        return None

                    data = await response.json()
                    LOGGER.debug("Retrieved thing data for %s", thing_name)
                    return data

        except TimeoutError:
            LOGGER.error("Timeout while getting thing %s", thing_name)
        except aiohttp.ClientError as e:
            LOGGER.error("HTTP error while getting thing %s: %s", thing_name, e)
        except Exception as e:
            LOGGER.error("Error getting thing %s: %s", thing_name, e)
        return None
