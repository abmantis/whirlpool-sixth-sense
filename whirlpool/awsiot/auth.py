"""AWS Cognito authentication for Whirlpool appliances."""

import logging
import time
from typing import Any

import aiohttp
import async_timeout

from ..auth import Auth as WhirlpoolAuth
from .signing import create_signed_headers, create_signed_url

LOGGER = logging.getLogger(__name__)

# TODO: What about EMEA?
AWS_REGION = "us-east-2"
COGNITO_URL = f"https://cognito-identity.{AWS_REGION}.amazonaws.com/"
WHIRLPOOL_COGNITO_URL = "https://api.whrcloud.com/api/v1/cognito/identityid"


class AuthException(Exception):
    """Custom exception for authentication errors."""


class Auth:
    """Handles AWS Cognito authentication for IoT access."""

    def __init__(self, whirlpool_auth: WhirlpoolAuth, session: aiohttp.ClientSession):
        """Initialize AWS authentication."""
        self._whirlpool_auth = whirlpool_auth
        self._session = session
        self._cognito_identity_id: str | None = None
        self._cognito_token: str | None = None
        self._aws_credentials: dict[str, Any] | None = None

    async def get_cognito_identity_id(self) -> str:
        """
        Get a Cognito identity ID and token from Whirlpool's API.

        This calls Whirlpool's API which returns both the identity ID and a
        Cognito token that can be used to get AWS credentials.

        The result is cached.

        Returns:
            Cognito identity ID or None if failed
        """
        if self._cognito_identity_id:
            return self._cognito_identity_id

        if not self._whirlpool_auth.is_access_token_valid():
            LOGGER.info("Access token expired. Renewing.")
            if not await self._whirlpool_auth.do_auth():
                raise AuthException("Failed to renew access token")

        access_token = self._whirlpool_auth.get_access_token()
        if not access_token:
            raise AuthException("No access token available")

        headers = {
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {access_token}",
        }

        async with async_timeout.timeout(30):
            async with self._session.get(WHIRLPOOL_COGNITO_URL, headers=headers) as r:
                if r.status != 200:
                    LOGGER.error("Failed to get Cognito identity ID: %s", r.status)
                    raise AuthException(
                        f"Failed to get Cognito identity ID: {r.status}"
                    )

                data = await r.json()
                self._cognito_identity_id = data.get("identityId")
                self._cognito_token = data.get("token")
                LOGGER.debug("Cognito identity ID: %s", self._cognito_identity_id)
                if not self._cognito_identity_id:
                    raise AuthException("No identity ID in response")
                return self._cognito_identity_id

    async def get_aws_credentials(self) -> dict[str, Any]:
        """
        Get temporary AWS credentials for IoT access.

        The result is cached until expiration.
        """
        if self._aws_credentials:
            expiration = self._aws_credentials.get("Expiration", 0)
            if time.time() < expiration - 60:
                return self._aws_credentials
            LOGGER.info("AWS credentials expired, refreshing")
            self._aws_credentials = None
            self._cognito_identity_id = None
            self._cognito_token = None

        identity_id = await self.get_cognito_identity_id()
        if not identity_id or not self._cognito_token:
            raise AuthException("Cognito identity ID or token not available")

        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityService.GetCredentialsForIdentity",
            "User-Agent": "okhttp/3.12.0",
        }

        body = {
            "IdentityId": identity_id,
            "Logins": {
                "cognito-identity.amazonaws.com": self._cognito_token,
            },
        }

        async with async_timeout.timeout(30):
            async with self._session.post(COGNITO_URL, headers=headers, json=body) as r:
                if r.status != 200:
                    raise AuthException(f"Failed to get AWS credentials: {r.status}")

                # Use content_type=None to accept application/x-amz-json-1.1
                data = await r.json(content_type=None)
                self._aws_credentials = data.get("Credentials")
                if not self._aws_credentials:
                    raise AuthException("No credentials in response")

                LOGGER.debug(
                    "AWS credentials obtained, expires: %s",
                    self._aws_credentials.get("Expiration"),
                )
                return self._aws_credentials

    async def create_signed_url(self, endpoint: str) -> str:
        """Create a SigV4-signed URL for AWS IoT MQTT connection."""
        credentials = await self.get_aws_credentials()

        return create_signed_url(
            access_key=credentials["AccessKeyId"],
            secret_key=credentials["SecretKey"],
            session_token=credentials["SessionToken"],
            host=endpoint,
            region=AWS_REGION,
        )

    async def create_signed_headers(
        self,
        host: str,
        uri: str,
        service: str,
        query_params: dict[str, str] | None = None,
    ) -> dict[str, str]:
        credentials = await self.get_aws_credentials()

        return create_signed_headers(
            access_key=credentials["AccessKeyId"],
            secret_key=credentials["SecretKey"],
            session_token=credentials["SessionToken"],
            method="GET",
            host=host,
            uri=uri,
            region=AWS_REGION,
            query_params=query_params,
            service=service,
        )
