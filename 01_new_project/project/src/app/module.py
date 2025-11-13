import time
import json

def func():
    return {"num": 42, "ts": int(time.time())}

def err():
    raise RuntimeError("Oops!")
