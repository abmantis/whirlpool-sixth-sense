"""
AWS SigV4 Signing Utilities

Provides functions for signing AWS API requests using Signature Version 4.
"""

import datetime
import hashlib
import hmac
import urllib.parse


def _sign(key: bytes, msg: str) -> bytes:
    """HMAC-SHA256 sign a message."""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(
    secret_key: str, date_stamp: str, region: str, service: str
) -> bytes:
    """Generate AWS SigV4 signing key."""
    k_date = _sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, service)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


def create_signed_url(
    access_key: str,
    secret_key: str,
    session_token: str,
    host: str,
    region: str,
    service: str = "iotdata",
) -> str:
    """
    Create a SigV4-signed WebSocket URL for AWS IoT.

    Args:
        access_key: AWS access key ID
        secret_key: AWS secret access key
        session_token: AWS session token
        host: MQTT endpoint hostname
        region: AWS region
        service: AWS service name (iotdata for IoT)

    Returns:
        Signed WebSocket URL (wss://...)
    """
    now = datetime.datetime.now(datetime.UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"

    algorithm = "AWS4-HMAC-SHA256"
    credential = f"{access_key}/{credential_scope}"

    # Build canonical query string (WITHOUT security token - it's added after signing)
    signed_headers = "host"
    query_params = {
        "X-Amz-Algorithm": algorithm,
        "X-Amz-Credential": credential,
        "X-Amz-Date": amz_date,
        "X-Amz-SignedHeaders": signed_headers,
    }

    canonical_querystring = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(query_params.items())
    )

    canonical_uri = "/mqtt"
    canonical_headers = f"host:{host}\n"
    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_request = "\n".join(
        [
            "GET",
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    string_to_sign = "\n".join(
        [
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    # Calculate signature
    signing_key = _get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Build final URL - add signature first, then security token (order matters!)
    signed_url = (
        f"wss://{host}{canonical_uri}?{canonical_querystring}"
        f"&X-Amz-Signature={signature}"
    )

    # Add security token AFTER the signature (not part of the signed content)
    if session_token:
        signed_url += (
            f"&X-Amz-Security-Token={urllib.parse.quote(session_token, safe='')}"
        )

    return signed_url


def create_signed_headers(
    access_key: str,
    secret_key: str,
    session_token: str,
    method: str,
    host: str,
    uri: str,
    region: str,
    query_params: dict[str, str] | None = None,
    service: str = "iot",
    payload: bytes = b"",
) -> dict[str, str]:
    """
    Create SigV4-signed headers for AWS API requests.

    Args:
        access_key: AWS access key ID
        secret_key: AWS secret access key
        session_token: AWS session token
        method: HTTP method (GET, POST, etc.)
        host: API endpoint hostname
        uri: Request URI path
        region: AWS region
        query_params: Optional query parameters
        payload: Request body
        service: AWS service name

    Returns:
        Dictionary of headers including Authorization
    """
    now = datetime.datetime.now(datetime.UTC)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    if query_params:
        canonical_querystring = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted(query_params.items())
        )
    else:
        canonical_querystring = ""

    canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(payload).hexdigest()

    canonical_request = "\n".join(
        [
            method,
            uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    algorithm = "AWS4-HMAC-SHA256"

    string_to_sign = "\n".join(
        [
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )

    # Calculate signature
    signing_key = _get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "Host": host,
        "X-Amz-Date": amz_date,
        "Authorization": authorization,
        "X-Amz-Security-Token": session_token,
    }

    return headers
