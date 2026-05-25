"""Mock observability integration for network status monitoring.

This module provides mock implementations of Grafana/Prometheus
observability functions for demonstration purposes.

Production: Replace with real observability API calls.
"""

import time
import random


def get_device_network_status(device_id: str = "default") -> dict:
    """Mock device network status query from observability system.

    Production: Replace with real Grafana/Prometheus API call.

    Args:
        device_id: Optional device identifier to query

    Returns:
        Network status data with latency, throughput, and connection status
    """
    # Simulate API delay
    time.sleep(0.3)
    
    status = {
        "status": "success",
        "device_id": device_id,
        "queried_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "network_status": "Connected",
        "latency_ms": random.randint(10, 150),
        "throughput_mbps": round(random.uniform(100, 1000), 2),
        "packet_loss_percent": round(random.uniform(0, 2), 2),
        "connection_type": "Ethernet",
        "last_sync": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - random.randint(60, 300))),
        "metrics": {
            "cpu_usage": round(random.uniform(20, 80), 2),
            "memory_usage": round(random.uniform(40, 90), 2),
            "disk_io": round(random.uniform(10, 200), 2),
            "network_io": round(random.uniform(50, 500), 2)
        }
    }
    
    return status