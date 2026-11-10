import os
import logging

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# `or`, not a default: the platform sets this to "" when it has no value.
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "pro-finder-nz"
storage_key = None


def init_storage(force: bool = False):
    global storage_key
    if storage_key and not force:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def _with_retry(fn):
    try:
        return fn(init_storage())
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return fn(init_storage(force=True))
        raise


def put_object(path: str, data: bytes, content_type: str) -> dict:
    def go(key):
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=300)
        resp.raise_for_status()
        return resp.json()
    return _with_retry(go)


def get_object(path: str) -> tuple[bytes, str]:
    def go(key):
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=120)
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
    return _with_retry(go)
