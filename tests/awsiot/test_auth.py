"""Tests for AWS Cognito credential refresh on expiration."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from whirlpool.awsiot.auth import Auth


@pytest.fixture
def mock_whirlpool_auth() -> MagicMock:
    auth = MagicMock()
    auth.is_access_token_valid.return_value = True
    auth.get_access_token.return_value = "fake-access-token"
    auth.do_auth = AsyncMock(return_value=True)
    return auth


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=["get", "post"])


class TestCredentialExpiration:
    async def test_expired_credentials_are_refreshed(
        self, mock_whirlpool_auth: MagicMock, mock_session: MagicMock
    ) -> None:
        """When cached AWS credentials have expired, get_aws_credentials
        must clear the cache and fetch fresh ones — otherwise SigV4 URLs
        are signed with expired keys and the broker rejects the handshake."""

        auth = Auth(mock_whirlpool_auth, mock_session)

        expired_creds = {
            "AccessKeyId": "OLD_KEY",
            "SecretKey": "OLD_SECRET",
            "SessionToken": "OLD_TOKEN",
            "Expiration": time.time() - 600,
        }
        fresh_creds = {
            "AccessKeyId": "NEW_KEY",
            "SecretKey": "NEW_SECRET",
            "SessionToken": "NEW_TOKEN",
            "Expiration": time.time() + 3600,
        }

        # Pre-populate the cache with expired credentials.
        auth._aws_credentials = expired_creds
        auth._cognito_identity_id = "old-id"
        auth._cognito_token = "old-token"

        # Mock the HTTP calls that happen on re-fetch.
        cognito_response = AsyncMock()
        cognito_response.status = 200
        cognito_response.json = AsyncMock(
            return_value={"identityId": "new-id", "token": "new-token"}
        )
        creds_response = AsyncMock()
        creds_response.status = 200
        creds_response.json = AsyncMock(return_value={"Credentials": fresh_creds})

        get_ctx = AsyncMock()
        get_ctx.__aenter__.return_value = cognito_response
        mock_session.get.return_value = get_ctx

        post_ctx = AsyncMock()
        post_ctx.__aenter__.return_value = creds_response
        mock_session.post.return_value = post_ctx

        result = await auth.get_aws_credentials()

        assert result["AccessKeyId"] == "NEW_KEY"
        assert auth._cognito_identity_id == "new-id"

    async def test_valid_credentials_are_returned_from_cache(
        self, mock_whirlpool_auth: MagicMock, mock_session: MagicMock
    ) -> None:
        """Credentials that haven't expired yet should be returned
        directly from cache without any HTTP calls."""

        auth = Auth(mock_whirlpool_auth, mock_session)

        valid_creds = {
            "AccessKeyId": "CACHED_KEY",
            "SecretKey": "CACHED_SECRET",
            "SessionToken": "CACHED_TOKEN",
            "Expiration": time.time() + 3600,
        }
        auth._aws_credentials = valid_creds

        result = await auth.get_aws_credentials()

        assert result["AccessKeyId"] == "CACHED_KEY"
        mock_session.get.assert_not_called()
        mock_session.post.assert_not_called()
