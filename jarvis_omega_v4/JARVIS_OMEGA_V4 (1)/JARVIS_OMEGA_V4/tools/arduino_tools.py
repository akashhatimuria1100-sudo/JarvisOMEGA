"""
tools/arduino_tools.py — Arduino & Hardware Control
Detects Arduino/ESP32/ESP8266, uploads firmware, reads serial data.
"""

import logging
import time
import threading
from pathlib import Path

logger = logging.getLogger("JARVIS.ARDUINO")
_BASE = Path(__file__).resolve().parent.parent


def detect_boards() -> list:
    """Detect connected Arduino/ESP boards."""
    boards = []
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            board_info = {
                "port": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "type": _identify_board(port.description, port.hwid),
            }
            boards.append(board_info)
    except ImportError:
        logger.warning("pyserial not installed. Install: pip install pyserial")
    except Exception as exc:
        logger.error("Board detection failed: %s", exc)
    return boards


def _identify_board(description: str, hwid: str) -> str:
    """Identify board type from USB description."""
    desc_lower = (description + hwid).lower()
    if "arduino" in desc_lower:
        if "uno" in desc_lower:
            return "Arduino Uno"
        elif "nano" in desc_lower:
            return "Arduino Nano"
        elif "mega" in desc_lower:
            return "Arduino Mega"
        return "Arduino (unknown)"
    elif "esp32" in desc_lower or "cp210" in desc_lower:
        return "ESP32"
    elif "esp8266" in desc_lower or "ch340" in desc_lower:
        return "ESP8266"
    elif "raspberry" in desc_lower:
        return "Raspberry Pi"
    return "Unknown Device"


def _auto_detect_port() -> str:
    """Auto-detect the first available Arduino port."""
    boards = detect_boards()
    if boards:
        return boards[0]["port"]
    return ""


def upload_sketch(code: str, port: str = "auto", board: str = "arduino:avr:uno") -> dict:
    """Save Arduino sketch and attempt upload via arduino-cli."""
    if not code.strip():
        return {"type": "error", "error": "No Arduino code provided"}

    if port == "auto":
        port = _auto_detect_port()
        if not port:
            boards = detect_boards()
            if boards:
                port = boards[0]["port"]

    # Save sketch
    sketch_dir = _BASE / "data/arduino_sketch"
    sketch_dir.mkdir(parents=True, exist_ok=True)
    sketch_name = sketch_dir.name
    ino_file = sketch_dir / f"{sketch_name}.ino"
    ino_file.write_text(code, encoding="utf-8")

    if not port:
        return {
            "type": "arduino_sketch_saved",
            "path": str(ino_file),
            "message": "Sketch saved. No Arduino detected. Connect board and upload manually.",
        }

    # Try arduino-cli upload
    try:
        import subprocess
        result = subprocess.run(
            ["arduino-cli", "compile", "--upload", "-p", port, "-b", board, str(sketch_dir)],
            capture_output=True, text=True, timeout=60
        )
        success = result.returncode == 0
        return {
            "type": "arduino_uploaded" if success else "arduino_error",
            "port": port,
            "output": (result.stdout + result.stderr)[:1000],
            "success": success,
        }
    except FileNotFoundError:
        return {
            "type": "arduino_sketch_saved",
            "path": str(ino_file),
            "message": (
                f"Sketch saved to {ino_file}. "
                "arduino-cli not found. Install from arduino.cc/pro/cli or "
                "open Arduino IDE and upload manually."
            ),
        }
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def read_serial(port: str = "auto", baud: int = 9600, duration: float = 5.0) -> dict:
    """Read serial data from Arduino for a given duration."""
    if port == "auto":
        port = _auto_detect_port()
        if not port:
            return {"type": "error", "error": "No Arduino/serial device detected"}

    lines = []
    try:
        import serial
        ser = serial.Serial(port, baud, timeout=1)
        end_time = time.time() + duration
        while time.time() < end_time:
            if ser.in_waiting:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    lines.append(line)
                    logger.info("Serial [%s]: %s", port, line)
        ser.close()
        return {
            "type": "serial_data",
            "port": port,
            "baud": baud,
            "lines": lines,
            "text": "\n".join(lines),
        }
    except ImportError:
        return {"type": "error", "error": "pyserial not installed. Run: pip install pyserial"}
    except Exception as exc:
        return {"type": "error", "error": f"Serial error: {exc}"}


def generate_circuit_diagram_text(description: str) -> str:
    """Generate ASCII circuit diagram for simple circuits."""
    return f"""
╔══════════════════════════════════════════════════╗
║          Circuit Diagram: {description[:30]:<30}  ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║   [Arduino Uno / ESP32]                          ║
║      │                                           ║
║      ├─── 5V ─────────────────┐                  ║
║      │                        │                  ║
║      ├─── GND ─────────────┐  │                  ║
║      │                     │  │                  ║
║      ├─── Pin 13 ──[220Ω]──┤  │                  ║
║      │                     │  │                  ║
║      │              LED(+)─┘  │                  ║
║      │              LED(-)────┘                  ║
║                                                  ║
║   NOTE: Always use appropriate resistors!        ║
╚══════════════════════════════════════════════════╝
"""


def generate_3d_printable_stl_description(component: str) -> dict:
    """Generate a description for 3D printable parts (placeholder for actual slicer integration)."""
    return {
        "type": "3d_print_info",
        "component": component,
        "message": (
            f"3D print design for: {component}\n"
            "To generate actual STL files:\n"
            "1. Install FreeCAD or OpenSCAD\n"
            "2. Use JARVIS Blender Skill for 3D modeling\n"
            "3. Export as STL for slicing with Cura/PrusaSlicer"
        ),
        "scad_template": f"""
// OpenSCAD template for {component}
// Generated by JARVIS OMEGA
// Customize dimensions as needed

module {component.replace(' ', '_').lower()}() {{
    // Basic shape — modify as needed
    difference() {{
        cube([50, 30, 20]);           // Outer shell
        translate([2, 2, 2])
            cube([46, 26, 20]);       // Inner cavity
    }}
}}

{component.replace(' ', '_').lower()}();
""",
    }
