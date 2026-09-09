"""Authenticate exact report bytes with the public key in the pinned checkout."""

import base64
import os
from pathlib import Path
import subprocess
import tempfile

from telemetry.public_fields import exact_keys, object_value

PUBLIC_KEY = Path(__file__).resolve().with_name("report-public-key.pem")
RSA_SIGNATURE_BYTES = 256


def _signature_bytes(value):
    if not isinstance(value, str) or len(value) > 512:
        raise ValueError("invalid report signature encoding")
    try:
        signature = base64.b64decode(value, validate=True)
    except ValueError:
        raise ValueError("invalid report signature encoding") from None
    if len(signature) != RSA_SIGNATURE_BYTES:
        raise ValueError("invalid RSA report signature size")
    return signature


def _verify(payload, signature):
    if not isinstance(payload, str):
        raise ValueError("signed report must be an exact UTF-8 string")
    if not PUBLIC_KEY.is_file() or PUBLIC_KEY.is_symlink():
        raise ValueError("pinned report public key unavailable")
    try:
        with tempfile.NamedTemporaryFile(dir=os.environ.get("RUNNER_TEMP")) as proof:
            proof.write(signature)
            proof.flush()
            result = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(PUBLIC_KEY),
                                     "-signature", proof.name], input=payload.encode("utf-8"),
                                    capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("report signature verification unavailable") from None
    if result.returncode != 0:
        raise ValueError("report signature verification failed")


def verified_dispatch(event):
    """Return authenticated serialized JSON; parsing and sanitization follow this."""
    inputs = object_value(object_value(event).get("inputs"))
    exact_keys(inputs, ("sanitized_json", "signature"))
    payload = inputs["sanitized_json"]
    _verify(payload, _signature_bytes(inputs["signature"]))
    return payload
