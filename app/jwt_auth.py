import time
import base64
import logging
from typing import Dict, Any, Optional
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ============================================================
# Key Generation on Startup (Ephemeral)
# ============================================================

logger.info("Generating ephemeral RSA-2048 key pair for Sarathi JWTs...")
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

KEY_ID = "sarathi-key-001"
ALGORITHM = "RS256"

# ============================================================
# JWKS Construction
# ============================================================

def int_to_base64url(i: int) -> str:
    """Convert an integer to a Base64URL-encoded string."""
    b = i.to_bytes((i.bit_length() + 7) // 8, byteorder='big')
    return base64.urlsafe_b64encode(b).decode('utf-8').rstrip('=')

def get_jwks() -> Dict[str, Any]:
    """Returns the JSON Web Key Set (JWKS) containing the public key."""
    pn = public_key.public_numbers()
    
    n = int_to_base64url(pn.n)
    e = int_to_base64url(pn.e)
    
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": KEY_ID,
                "use": "sig",
                "alg": ALGORITHM,
                "n": n,
                "e": e
            }
        ]
    }

# ============================================================
# JWT Minting
# ============================================================

def mint_bridge_jwt(
    execution_id: str,
    trace_id: Optional[str] = None,
    cet_hash: Optional[str] = None
) -> str:
    """
    Mints an RS256 signed JWT for Ranjit's Bridge containing Sarathi enforcement claims.
    """
    now = int(time.time())
    expires_in_seconds = 300  # 5 minutes
    
    payload = {
        "iss": "tantra-sarathi",
        "aud": "tantra-bridge",
        "exp": now + expires_in_seconds,
        "iat": now,
        "execution_id": execution_id,
        "trace_id": trace_id if trace_id else "unknown",
        "cet_hash": cet_hash if cet_hash else "unknown",
        "rajya_verdict": "EXECUTION_APPROVED"
    }
    
    headers = {
        "kid": KEY_ID,
        "typ": "JWT"
    }
    
    token = jwt.encode(
        payload,
        private_key,
        algorithm=ALGORITHM,
        headers=headers
    )
    
    logger.info(
        f"MINTED SARATHI JWT | execution_id={execution_id} | kid={KEY_ID}",
        extra={"event_type": "sarathi_jwt_minted", "execution_id": execution_id}
    )
    
    return token
