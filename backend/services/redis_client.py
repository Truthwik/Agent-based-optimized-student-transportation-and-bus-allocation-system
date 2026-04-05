"""
Redis client with in-memory fallback.
If Redis is not running, the system falls back to a Python dict — tracking
still works but won't broadcast to WebSocket clients (real-time map won't update).
Install Redis (Memurai for Windows) for full functionality.
"""
import json
from ..config import REDIS_URL

redis_client = None
_in_memory_store: dict = {}  # Fallback when Redis is unavailable

# Try connecting to Redis
try:
    import redis as _redis
    _client = _redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _client.ping()  # Test connection
    redis_client = _client
    print("[GPS] ✅ Redis connected successfully.")
except Exception as e:
    print(f"[GPS] ⚠️  Redis unavailable ({e}). Using in-memory fallback — WebSocket live map disabled.")


def _mem_get(key):
    return _in_memory_store.get(key)

def _mem_set(key, val):
    _in_memory_store[key] = val

def _mem_del(key):
    _in_memory_store.pop(key, None)


def set_bus_state(bus_id, is_active: bool):
    key = f"bus:{bus_id}:active"
    val = "true" if is_active else "false"
    if redis_client:
        redis_client.set(key, val)
    else:
        _mem_set(key, val)

def is_bus_active(bus_id) -> bool:
    key = f"bus:{bus_id}:active"
    val = redis_client.get(key) if redis_client else _mem_get(key)
    return val == "true"

def update_bus_location(bus_id, data: dict):
    key = f"bus:{bus_id}:location"
    serialized = json.dumps(data)
    if redis_client:
        redis_client.set(key, serialized)
        redis_client.publish(f"bus:{bus_id}:updates", serialized)
    else:
        _mem_set(key, serialized)

def get_bus_location(bus_id):
    key = f"bus:{bus_id}:location"
    raw = redis_client.get(key) if redis_client else _mem_get(key)
    return json.loads(raw) if raw else None

def get_active_buses():
    results = []
    if redis_client:
        keys = redis_client.keys("bus:*:active")
        for key in keys:
            if redis_client.get(key) == "true":
                bus_id = key.split(":")[1]
                loc = get_bus_location(bus_id)
                if loc:
                    results.append(loc)
    else:
        for key, val in list(_in_memory_store.items()):
            if key.endswith(":active") and val == "true":
                bus_id = key.split(":")[1]
                loc = get_bus_location(bus_id)
                if loc:
                    results.append(loc)
    return results
