import hashlib
import json

def hash_event(prev_hash: str, payload: dict) -> str:
    """
    Cryptographically hashes a dictionary payload combined with the previous hash
    to form a continuous immutable chain.
    """
    # Deterministic JSON representation (sort_keys=True ensures consistent ordering)
    data_str = json.dumps(payload, sort_keys=True)
    combined = f"{prev_hash}{data_str}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()
