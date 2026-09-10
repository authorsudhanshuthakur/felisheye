import os
import json
import base64
import hashlib
import numpy as np
from cryptography.fernet import Fernet
from typing import Union, List
from app.core.config import KEY_PATH, settings

def _get_or_create_key() -> bytes:
    if KEY_PATH.exists():
        try:
            with open(KEY_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) == 44:  # Valid base64 Fernet key length
                    return key
        except Exception:
            pass
    # Generate a new Fernet key
    new_key = Fernet.generate_key()
    try:
        with open(KEY_PATH, "wb") as f:
            f.write(new_key)
    except Exception as e:
        print(f"[Security Warning] Could not write key file: {e}")
    return new_key

_FERNET_KEY = _get_or_create_key()
_cipher = Fernet(_FERNET_KEY)

def encrypt_vector(vector: Union[np.ndarray, List[float]]) -> str:
    """
    Encrypts a 128D numpy embedding vector into a secure encrypted base64 string.
    """
    if isinstance(vector, np.ndarray):
        arr = vector.astype(np.float32).tolist()
    else:
        arr = list(vector)
    
    raw_json = json.dumps(arr).encode('utf-8')
    if settings.ENCRYPT_EMBEDDINGS:
        encrypted_bytes = _cipher.encrypt(raw_json)
        return encrypted_bytes.decode('utf-8')
    else:
        return base64.b64encode(raw_json).decode('utf-8')

def decrypt_vector(token: str) -> np.ndarray:
    """
    Decrypts an encrypted base64 string back into a 128D numpy array.
    """
    try:
        raw_bytes = token.encode('utf-8')
        try:
            decrypted = _cipher.decrypt(raw_bytes)
        except Exception:
            # Fallback if unencrypted base64
            decrypted = base64.b64decode(raw_bytes)
        
        arr = json.loads(decrypted.decode('utf-8'))
        return np.array(arr, dtype=np.float32)
    except Exception as e:
        raise ValueError(f"Failed to decrypt biometric vector: {e}")

def compute_image_hash(image_bytes: bytes) -> str:
    """Computes SHA-256 hash of image data."""
    return hashlib.sha256(image_bytes).hexdigest()
