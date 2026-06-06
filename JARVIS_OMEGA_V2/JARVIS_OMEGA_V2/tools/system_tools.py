"""
tools/system_tools.py — System information and hardware control
"""

import logging
import platform
import socket
import datetime

logger = logging.getLogger("JARVIS.SYSTEM")


def get_system_info() -> dict:
    """Gather comprehensive system information."""
    info = {
        "type": "system_info",
        "platform": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "hostname": socket.gethostname(),
        "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        import psutil

        # CPU
        info["cpu_percent"]  = psutil.cpu_percent(interval=1)
        info["cpu_count"]    = psutil.cpu_count()
        info["cpu_freq"]     = round(psutil.cpu_freq().current / 1000, 2) if psutil.cpu_freq() else 0

        # RAM
        mem = psutil.virtual_memory()
        info["ram_total"]   = round(mem.total / 1e9, 2)
        info["ram_used"]    = round(mem.used / 1e9, 2)
        info["ram_percent"] = mem.percent

        # Disk
        disk = psutil.disk_usage("/")
        info["disk_total"]   = round(disk.total / 1e9, 2)
        info["disk_used"]    = round(disk.used / 1e9, 2)
        info["disk_free"]    = round(disk.free / 1e9, 2)
        info["disk_percent"] = disk.percent

        # Battery
        bat = psutil.sensors_battery()
        if bat:
            info["battery"]         = f"{int(bat.percent)}%"
            info["battery_plugged"] = bat.power_plugged
        else:
            info["battery"] = "N/A"

        # Top processes
        procs = []
        for p in sorted(psutil.process_iter(["name", "cpu_percent", "memory_percent"]),
                         key=lambda x: x.info.get("cpu_percent", 0) or 0,
                         reverse=True)[:5]:
            try:
                procs.append({
                    "name": p.info["name"],
                    "cpu":  round(p.info["cpu_percent"] or 0, 1),
                    "mem":  round(p.info["memory_percent"] or 0, 1),
                })
            except Exception:
                pass
        info["top_processes"] = procs

    except ImportError:
        logger.warning("psutil not installed — limited system info")
    except Exception as exc:
        logger.error("System info error: %s", exc)

    # Network
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        info["online"] = True
    except Exception:
        info["online"] = False

    return info


def get_installed_apps() -> list:
    """List installed applications (Windows)."""
    apps = []
    try:
        if platform.system() == "Windows":
            import winreg
            keys = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]
            for key_path in keys:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            sub_key = winreg.OpenKey(key, winreg.EnumKey(key, i))
                            name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                            apps.append(name)
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception as exc:
        logger.warning("App list failed: %s", exc)
    return sorted(set(apps))


def update_digital_twin():
    """Update the digital twin with current system state."""
    import json
    from pathlib import Path
    twin_path = Path(__file__).resolve().parent.parent / "data/digital_twin.json"
    try:
        twin = json.loads(twin_path.read_text(encoding="utf-8")) if twin_path.exists() else {}
        twin["last_updated"] = datetime.datetime.now().isoformat()
        twin["system"] = get_system_info()
        twin["apps"] = get_installed_apps()[:100]
        twin_path.write_text(json.dumps(twin, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Digital twin update failed: %s", exc)
