import random
_FAKE_TOOLS = {

    # Query Agent

    "sensor_data": lambda **kwargs: {
        "temperature":24.3,
        "humidity":55,
        "co2":620,
        "occupancy":18
    },

    "weather": lambda **kwargs: {
        "outside_temperature":31,
        "condition":"Sunny"
    },

    "history": lambda **kwargs: {
        "avg_temperature":23.8,
        "trend":"Rising"
    },
        "hvac_status": lambda **kwargs:{

        "supply_temp":14,

        "load_kw":42,

        "fan_speed":65
    },

    "comfort_index": lambda **kwargs:{

        "pmv":0.6,

        "status":"Slightly Warm"
    },
        "lighting_status": lambda **kwargs:{

        "lux":210,

        "target_lux":400
    },
        "access_status": lambda **kwargs:{

        "active_badges":18,

        "unauthorized":0
    },
        "safety_status": lambda **kwargs:{

        "fire":False,

        "smoke":False,

        "gas_ppm":12
    },
        "device_health": lambda **kwargs:{

        "offline_devices":0,

        "faults":[]
    },
        "optimizer": lambda **kwargs:{

        "recommended_temp":25,

        "expected_saving":11.5
    },
        "simulation": lambda **kwargs:{

        "comfort_score":92,

        "predicted_load":37.8
    },
        "bms_execute": lambda **kwargs:{

        "ack":True,

        "latency_ms":random.randint(20,80)
    }

}

def call_tool(name: str, **kwargs):

    if name not in _FAKE_TOOLS:

        return {
            "error":f"Unknown tool '{name}'"
        }

    return _FAKE_TOOLS[name](**kwargs)