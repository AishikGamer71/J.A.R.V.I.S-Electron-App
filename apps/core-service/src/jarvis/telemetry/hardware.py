import logging
import psutil
from jarvis.domain.entities.models import HardwareTelemetry

logger = logging.getLogger("jarvis.telemetry.hardware")


def get_hardware_telemetry() -> HardwareTelemetry:
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)

    # Memory
    mem = psutil.virtual_memory()
    ram_percent = mem.percent
    ram_used_gb = round(mem.used / (1024 ** 3), 2)
    ram_total_gb = round(mem.total / (1024 ** 3), 2)

    gpu_name = None
    vram_used_mb = None
    vram_total_mb = None

    # Try detecting GPU via torch or WMI on Windows
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_total_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 2), 1)
            vram_used_mb = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 1)
    except Exception:
        pass

    # Tier Calculation
    # Low: < 12GB RAM or low CPU
    # Mid: 16GB-32GB RAM
    # High: >= 32GB RAM or Dedicated GPU >= 8GB VRAM
    system_tier: str = "mid"
    if ram_total_gb < 12:
        system_tier = "low"
    elif ram_total_gb >= 32 or (vram_total_mb and vram_total_mb >= 8000):
        system_tier = "high"
    else:
        system_tier = "mid"

    return HardwareTelemetry(
        cpu_percent=cpu_percent,
        ram_percent=ram_percent,
        ram_used_gb=ram_used_gb,
        ram_total_gb=ram_total_gb,
        gpu_name=gpu_name,
        vram_used_mb=vram_used_mb,
        vram_total_mb=vram_total_mb,
        system_tier=system_tier
    )
