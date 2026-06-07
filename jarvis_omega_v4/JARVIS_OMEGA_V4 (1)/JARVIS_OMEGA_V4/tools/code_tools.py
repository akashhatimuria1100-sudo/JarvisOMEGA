"""
tools/code_tools.py — Autonomous Project Creation
JARVIS creates complete projects: Python apps, web apps, Arduino, etc.
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger("JARVIS.CODE")

_BASE = Path(__file__).resolve().parent.parent
PROJECTS_DIR = _BASE / "data/projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def create_project_scaffold(name: str, proj_type: str, description: str) -> dict:
    """Create a complete project with proper file structure."""
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name.lower())
    proj_dir = PROJECTS_DIR / safe_name
    proj_dir.mkdir(parents=True, exist_ok=True)

    proj_type = proj_type.lower()
    files_created = []

    try:
        if proj_type == "python":
            files_created = _create_python_project(proj_dir, safe_name, description)
        elif proj_type in ("web", "website", "html"):
            files_created = _create_web_project(proj_dir, safe_name, description)
        elif proj_type == "arduino":
            files_created = _create_arduino_project(proj_dir, safe_name, description)
        elif proj_type in ("game", "pygame"):
            files_created = _create_game_project(proj_dir, safe_name, description)
        elif proj_type in ("mobile", "android"):
            files_created = _create_mobile_project(proj_dir, safe_name, description)
        else:
            files_created = _create_python_project(proj_dir, safe_name, description)

        # Always create README
        readme = proj_dir / "README.md"
        readme.write_text(
            f"# {name}\n\n{description}\n\n"
            f"Created by JARVIS OMEGA — {time.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"## Files\n" + "\n".join(f"- `{f}`" for f in files_created),
            encoding="utf-8"
        )
        files_created.append("README.md")

        logger.info("Project created: %s (%d files)", proj_dir, len(files_created))
        return {
            "type": "project_created",
            "name": name,
            "path": str(proj_dir),
            "files": files_created,
            "summary": f"Project '{name}' created at {proj_dir} with {len(files_created)} files.",
        }

    except Exception as exc:
        logger.error("Project creation failed: %s", exc, exc_info=True)
        return {"type": "error", "error": str(exc)}


def _create_python_project(proj_dir: Path, name: str, desc: str) -> list:
    files = []

    # main.py
    (proj_dir / "main.py").write_text(
        f'"""\n{desc}\nCreated by JARVIS OMEGA\n"""\n\n'
        f'def main():\n    print("Hello from {name}!")\n    # TODO: Implement {desc}\n\n'
        f'if __name__ == "__main__":\n    main()\n',
        encoding="utf-8"
    )
    files.append("main.py")

    # requirements.txt
    (proj_dir / "requirements.txt").write_text("# Add dependencies here\n", encoding="utf-8")
    files.append("requirements.txt")

    # config.py
    (proj_dir / "config.py").write_text(
        f'# Configuration for {name}\n\nAPP_NAME = "{name}"\nVERSION = "1.0.0"\nDEBUG = True\n',
        encoding="utf-8"
    )
    files.append("config.py")

    # utils.py
    (proj_dir / "utils.py").write_text(
        f'"""Utility functions for {name}."""\n\nimport logging\nlogger = logging.getLogger(__name__)\n\n'
        f'def setup_logging():\n    logging.basicConfig(level=logging.INFO)\n',
        encoding="utf-8"
    )
    files.append("utils.py")

    return files


def _create_web_project(proj_dir: Path, name: str, desc: str) -> list:
    files = []

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>{name}</h1>
        <p>{desc}</p>
    </header>
    <main id="app">
        <!-- Content goes here -->
    </main>
    <script src="app.js"></script>
</body>
</html>"""
    (proj_dir / "index.html").write_text(html, encoding="utf-8")
    files.append("index.html")

    css = f"""/* {name} Styles */
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: 'Segoe UI', sans-serif;
    background: #0a0a0a;
    color: #e0e0e0;
    min-height: 100vh;
}}
header {{
    background: linear-gradient(135deg, #0d1a2e, #1a3a5c);
    padding: 2rem;
    text-align: center;
    border-bottom: 2px solid #00d4ff;
}}
h1 {{ color: #00d4ff; font-size: 2rem; }}
main {{ max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
"""
    (proj_dir / "style.css").write_text(css, encoding="utf-8")
    files.append("style.css")

    js = f"""// {name} — JavaScript
'use strict';

document.addEventListener('DOMContentLoaded', () => {{
    console.log('{name} loaded');
    // TODO: Implement {desc}
}});
"""
    (proj_dir / "app.js").write_text(js, encoding="utf-8")
    files.append("app.js")

    return files


def _create_arduino_project(proj_dir: Path, name: str, desc: str) -> list:
    files = []
    ino = f"""/*
 * {name}
 * {desc}
 * Created by JARVIS OMEGA
 */

// Pin definitions
const int LED_PIN = 13;

void setup() {{
    Serial.begin(9600);
    pinMode(LED_PIN, OUTPUT);
    Serial.println("{name} started!");
}}

void loop() {{
    // TODO: Implement {desc}
    digitalWrite(LED_PIN, HIGH);
    delay(1000);
    digitalWrite(LED_PIN, LOW);
    delay(1000);
}}
"""
    (proj_dir / f"{name}.ino").write_text(ino, encoding="utf-8")
    files.append(f"{name}.ino")

    # Wiring diagram (text)
    wiring = f"""# {name} — Wiring Diagram
# Created by JARVIS OMEGA

## Components
- Arduino Uno / ESP32
- LED (connected to pin 13)
- 220Ω resistor

## Connections
- LED (+) → Pin 13 → 220Ω → GND

## Serial Monitor
- Baud rate: 9600
"""
    (proj_dir / "wiring.md").write_text(wiring, encoding="utf-8")
    files.append("wiring.md")

    return files


def _create_game_project(proj_dir: Path, name: str, desc: str) -> list:
    files = []
    main_py = f""""""
    main_py = f'''"""
{name} — {desc}
Created by JARVIS OMEGA using Pygame
Run: pip install pygame && python main.py
"""

import pygame
import sys
import random

# Initialize
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("{name}")
clock = pygame.time.Clock()

# Colors
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
CYAN   = (0, 212, 255)
GREEN  = (0, 255, 100)
RED    = (255, 50, 50)

font_large = pygame.font.Font(None, 72)
font_med   = pygame.font.Font(None, 36)
font_small = pygame.font.Font(None, 24)

def draw_text(text, font, color, x, y, center=False):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(surf, rect)


def main():
    running = True
    score = 0

    while running:
        screen.fill(BLACK)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # Game logic here
        draw_text("{name}", font_large, CYAN, WIDTH // 2, HEIGHT // 2 - 50, center=True)
        draw_text("Score: " + str(score), font_med, WHITE, 20, 20)
        draw_text("Press ESC to quit", font_small, WHITE, 20, HEIGHT - 30)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
'''
    (proj_dir / "main.py").write_text(main_py, encoding="utf-8")
    files.append("main.py")

    reqs = "pygame>=2.5.0\n"
    (proj_dir / "requirements.txt").write_text(reqs, encoding="utf-8")
    files.append("requirements.txt")

    return files


def _create_mobile_project(proj_dir: Path, name: str, desc: str) -> list:
    """Kivy-based mobile app scaffold."""
    files = []
    main_py = f'''"""
{name} — Mobile App
{desc}
Created by JARVIS OMEGA using Kivy
Run: pip install kivy && python main.py
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.add_widget(Label(text="{name}", font_size=32, color=(0, 0.8, 1, 1)))
        self.add_widget(Label(text="{desc}", font_size=16))
        btn = Button(text="Start", size_hint=(None, None), size=(200, 60))
        btn.bind(on_press=self.on_start)
        self.add_widget(btn)

    def on_start(self, instance):
        print("Button pressed!")


class {name.replace(" ", "").replace("-", "")}App(App):
    def build(self):
        return MainScreen()

if __name__ == "__main__":
    {name.replace(" ", "").replace("-", "")}App().run()
'''
    (proj_dir / "main.py").write_text(main_py, encoding="utf-8")
    files.append("main.py")
    (proj_dir / "requirements.txt").write_text("kivy>=2.3.0\n", encoding="utf-8")
    files.append("requirements.txt")
    return files
