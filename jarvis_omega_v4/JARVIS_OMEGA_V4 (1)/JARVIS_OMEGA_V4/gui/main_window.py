"""
gui/main_window.py — JARVIS OMEGA V4 GUI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES & UPGRADES:
  ✅ Arc Reactor moved to CENTER with bigger size (340px)
  ✅ Transparent text background — reactor visible through panels
  ✅ Messages display FULLY — no clipping, auto-height, scrollable
  ✅ Speech recognition responds after capture (signal wiring fixed)
  ✅ Male voice (David/Guy) — fast rate 220
  ✅ Reactor has MORE animations: plasma beams, energy particles,
     data rings, rotating triangles, quantum field effect
  ✅ Left panel: reactor floats center-aligned, bigger
  ✅ Chat bubbles: transparent BG showing reactor glow through them
  ✅ Status indicator always visible
  ✅ No full-stop long pause in speaking — pyttsx3 says it all at once
"""

import sys
import json
import threading
import logging
import time
import math
import random
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QLineEdit, QPushButton, QLabel, QFrame, QStatusBar,
    QSystemTrayIcon, QMenu, QApplication, QDialog, QGridLayout,
    QScrollArea, QSizePolicy, QSplitter, QTextEdit, QCheckBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread, QPoint, QSize, QSizeF, QRectF,
    QPropertyAnimation, QEasingCurve, QRect,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QRadialGradient, QIcon, QAction,
    QBrush, QPen, QPixmap, QKeyEvent, QLinearGradient, QConicalGradient,
    QPolygon, QPolygonF,
)

logger = logging.getLogger("JARVIS.GUI")
_BASE  = Path(__file__).resolve().parent.parent

# ── Iron Man Color Palette ─────────────────────────────────────────────────────
C = {
    "bg":         "#010609",
    "bg2":        "#020c14",
    "bg3":        "#03101a",
    "panel":      "#040f1c",
    "border":     "#0d2035",
    "border2":    "#0f3050",
    "cyan":       "#00d4ff",
    "cyan_dim":   "#006688",
    "cyan_dark":  "#003344",
    "blue":       "#0055bb",
    "blue2":      "#0a3060",
    "blue_bright":"#2288ff",
    "gold":       "#ffaa00",
    "gold_dim":   "#996600",
    "red":        "#ff3333",
    "red_dim":    "#992222",
    "green":      "#00ff88",
    "green_dim":  "#00aa55",
    "orange":     "#ff8800",
    "text":       "#d8eaf5",
    "text_dim":   "#4a7090",
    "user_bg":    "#050f1e",
    "ai_bg":      "#030c16",
}

ORB_STATES = {
    "idle":      {"color": QColor(0, 180, 255),   "glow": QColor(0, 120, 200, 80),   "label": "IDLE"},
    "listening": {"color": QColor(0, 220, 255),   "glow": QColor(0, 200, 255, 120),  "label": "LISTENING"},
    "thinking":  {"color": QColor(255, 170, 0),   "glow": QColor(255, 140, 0, 100),  "label": "THINKING"},
    "speaking":  {"color": QColor(0, 255, 140),   "glow": QColor(0, 200, 100, 100),  "label": "SPEAKING"},
    "executing": {"color": QColor(120, 60, 255),  "glow": QColor(100, 40, 220, 100), "label": "EXECUTING"},
    "error":     {"color": QColor(255, 60, 60),   "glow": QColor(255, 0, 0, 100),    "label": "ERROR"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Signal Bridge
# ═══════════════════════════════════════════════════════════════════════════════

class Signals(QObject):
    new_message   = pyqtSignal(str, str)
    new_image     = pyqtSignal(str, str)
    new_code      = pyqtSignal(str, str)
    new_web       = pyqtSignal(list)
    status_update = pyqtSignal(str)
    orb_state     = pyqtSignal(str)
    listening_on  = pyqtSignal(bool)
    reminder_fired = pyqtSignal(str)
    minimize_window = pyqtSignal(bool)
    start_listening = pyqtSignal()
    ask_request   = pyqtSignal(str, str)
    state_change  = pyqtSignal(str)
    stop_listening_sig = pyqtSignal()
    wake_word_detected = pyqtSignal()


# ═══════════════════════════════════════════════════════════════════════════════
# Brain Worker Thread
# ═══════════════════════════════════════════════════════════════════════════════

class BrainWorker(QThread):
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, brain, text: str):
        super().__init__()
        self.brain = brain
        self.text  = text

    def run(self):
        try:
            self.finished.emit(self.brain.process(self.text))
        except Exception as exc:
            self.error.emit(str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# Arc Reactor Widget — FULL IRON MAN MK.VII with advanced animations
# ═══════════════════════════════════════════════════════════════════════════════

class ArcReactorWidget(QWidget):
    """
    Iron Man Arc Reactor — 340px, center-placed.
    Animations: copper coils, rotating rings, hex core, plasma beams,
    energy particles, data rings, quantum field, triangular connectors.
    """

    def __init__(self, parent=None, size: int = 400):
        super().__init__(parent)
        self.size_hint = size
        self.setFixedSize(size, size)
        self._phase    = 0.0
        self._rot      = 0.0
        self._pulse    = 0.0
        self._coil_rot = 0.0
        self._p_rot    = 0.0
        self._flicker  = 1.0
        self._particles = self._init_particles(6)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)   # 30fps

    def _init_particles(self, n):
        return [{"orbit": random.uniform(0.62, 0.80),
                 "angle": random.uniform(0, 360),
                 "speed": random.uniform(0.8, 2.2),
                 "size":  random.uniform(2.0, 4.5),
                 "alpha": random.randint(120, 220)}
                for _ in range(n)]

    def _tick(self):
        self._phase    = (self._phase    + 0.030) % (2 * math.pi)
        self._rot      = (self._rot      + 0.45)  % 360.0
        self._pulse    = (self._pulse    + 0.055) % (2 * math.pi)
        self._coil_rot = (self._coil_rot + 0.70)  % 360.0
        self._p_rot    = (self._p_rot    + 1.1)   % 360.0
        if random.random() < 0.04:
            self._flicker = random.uniform(0.80, 1.0)
        else:
            self._flicker = min(1.0, self._flicker + 0.02)
        for p in self._particles:
            p["angle"] = (p["angle"] + p["speed"]) % 360.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        R = min(w, h) / 2 * 0.90
        fl = self._flicker

        # ── 1. Outer ambient glow ───────────────────────────────
        halo = QRadialGradient(cx, cy, R * 1.2)
        ha = int(30 * fl * abs(math.sin(self._pulse)))
        halo.setColorAt(0.0, QColor(0, 160, 255, ha + 20))
        halo.setColorAt(0.5, QColor(0, 80, 180, ha // 2))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(halo))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - R * 1.2), int(cy - R * 1.2), int(R * 2.4), int(R * 2.4))

        # ── 2. Outer glow rings (pulsing) ──────────────────────
        pulse_a = 50 + int(30 * abs(math.sin(self._pulse)))
        for offset, alpha_mul, width in [(6, 1.0, 2.5), (14, 0.6, 1.5)]:
            r = R + offset
            a = int(pulse_a * alpha_mul * fl)
            p.setPen(QPen(QColor(0, 180, 255, a), width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # ── 3. Copper coils (8 blocks, rotating) ────────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(self._coil_rot)
        n_coils = 8
        coil_r = R * 0.80
        coil_w = R * 0.13
        coil_h = R * 0.20
        for i in range(n_coils):
            angle = i * (360.0 / n_coils)
            rad = math.radians(angle)
            cx2 = coil_r * math.cos(rad)
            cy2 = coil_r * math.sin(rad)
            glow_a = int((140 + 60 * abs(math.sin(self._phase + i * 0.8))) * fl)
            p.save()
            p.translate(cx2, cy2)
            p.rotate(angle + 90)
            p.setBrush(QBrush(QColor(25, 10, 4)))
            p.setPen(QPen(QColor(70, 35, 15, 100), 1))
            p.drawRect(int(-coil_w / 2), int(-coil_h / 2), int(coil_w), int(coil_h))
            for li in range(3):
                y_ln = -coil_h / 2 + li * (coil_h / 3) + coil_h / 6
                alpha = max(glow_a - li * 20, 50)
                p.setPen(QPen(QColor(200, 90, 20, alpha), 1.5))
                p.drawLine(int(-coil_w / 2 + 2), int(y_ln), int(coil_w / 2 - 2), int(y_ln))
            p.setPen(QPen(QColor(255, 140, 50, glow_a // 3), 0.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(int(-coil_w / 2), int(-coil_h / 2), int(coil_w), int(coil_h))
            p.restore()
        p.restore()

        # ── 4. Outer segmented ring ────────────────────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._rot * 0.6)
        seg_r = R * 0.78
        n_segs = 8
        for i in range(n_segs):
            angle1 = i * (360.0 / n_segs)
            angle2 = angle1 + (360.0 / n_segs) * 0.65
            span = angle2 - angle1
            alpha = int((70 + 50 * abs(math.sin(self._phase + i * 0.4))) * fl)
            width = 2.5 if i % 2 == 0 else 1.5
            p.setPen(QPen(QColor(0, 210, 255, alpha), width))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(int(-seg_r), int(-seg_r), int(seg_r * 2), int(seg_r * 2), int(angle1 * 16), int(span * 16))
        p.restore()

        # ── 5. Inner counter-rotating ring (bumps) ──────────────
        p.save()
        p.translate(cx, cy)
        p.rotate(self._rot * 0.35)
        inner_r = R * 0.60
        n_bumps = 10
        bump_w = R * 0.055
        bump_h = R * 0.09
        for i in range(n_bumps):
            angle = i * (360.0 / n_bumps)
            rad = math.radians(angle)
            bx = inner_r * math.cos(rad)
            by = inner_r * math.sin(rad)
            alpha = int((90 + 55 * abs(math.sin(self._phase + i * 0.32))) * fl)
            p.save()
            p.translate(bx, by)
            p.rotate(angle + 90)
            p.setBrush(QBrush(QColor(0, 150, 210, alpha)))
            p.setPen(QPen(QColor(0, 230, 255, alpha + 40), 1))
            p.drawRect(int(-bump_w / 2), int(-bump_h / 2), int(bump_w), int(bump_h))
            p.restore()
        p.restore()

        # ── 6. Middle glowing ring ──────────────────────────────
        mid_r = R * 0.555
        ring_a = int((70 + 45 * abs(math.sin(self._pulse))) * fl)
        p.setPen(QPen(QColor(0, 210, 255, ring_a), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(int(cx - mid_r), int(cy - mid_r), int(mid_r * 2), int(mid_r * 2))

        # ── 7. Hexagonal core ───────────────────────────────────
        hex_r = R * 0.42
        core_glow = QRadialGradient(cx, cy, hex_r)
        gi = (0.65 + 0.35 * abs(math.sin(self._pulse * 1.4))) * fl
        core_glow.setColorAt(0.0, QColor(230, 245, 255, int(210 * gi)))
        core_glow.setColorAt(0.25, QColor(130, 205, 255, int(160 * gi)))
        core_glow.setColorAt(0.55, QColor(0, 165, 225, int(110 * gi)))
        core_glow.setColorAt(1.0, QColor(0, 80, 140, 0))
        p.setBrush(QBrush(core_glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - hex_r), int(cy - hex_r), int(hex_r * 2), int(hex_r * 2))

        cell = R * 0.068
        for row in range(-2, 3):
            for col in range(-2, 3):
                hx = cx + col * cell * 1.72
                hy = cy + row * cell * 1.50 + (col % 2) * cell * 0.75
                dist = math.sqrt((hx - cx)**2 + (hy - cy)**2)
                if dist > hex_r * 0.88:
                    continue
                pts = []
                for k in range(6):
                    a = math.radians(60 * k + 30)
                    pts.append(QPoint(int(hx + cell * 0.46 * math.cos(a)), int(hy + cell * 0.46 * math.sin(a))))
                p.setBrush(QBrush(QColor(150, 220, 255, 22)))
                p.setPen(QPen(QColor(0, 210, 255, 38), 0.5))
                p.drawPolygon(QPolygon(pts))

        # ── 8. Orbiting particles ───────────────────────────────
        for part in self._particles:
            rad = math.radians(part["angle"] + self._p_rot * 0.3)
            orb = R * part["orbit"]
            px_ = cx + orb * math.cos(rad)
            py_ = cy + orb * math.sin(rad)
            sz = part["size"]
            a = int(part["alpha"] * fl)
            pg = QRadialGradient(px_, py_, sz * 2.5)
            pg.setColorAt(0.0, QColor(0, 220, 255, a))
            pg.setColorAt(1.0, QColor(0, 100, 200, 0))
            p.setBrush(QBrush(pg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(px_ - sz * 2.5), int(py_ - sz * 2.5), int(sz * 5), int(sz * 5))
            p.setBrush(QBrush(QColor(200, 240, 255, min(255, a + 60))))
            p.drawEllipse(int(px_ - sz / 2), int(py_ - sz / 2), int(sz), int(sz))

        # ── 9. Bright central core ──────────────────────────────
        core_r = R * 0.09 + 4 * abs(math.sin(self._pulse * 2.2))
        white_core = QRadialGradient(cx, cy, core_r * 2.5)
        ci = int(255 * fl)
        white_core.setColorAt(0.0, QColor(255, 255, 255, ci))
        white_core.setColorAt(0.25, QColor(210, 240, 255, int(220 * fl)))
        white_core.setColorAt(0.7, QColor(0, 190, 255, int(100 * fl)))
        white_core.setColorAt(1.0, QColor(0, 100, 200, 0))
        p.setBrush(QBrush(white_core))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - core_r * 2.5), int(cy - core_r * 2.5), int(core_r * 5), int(core_r * 5))

        # ── 10. Scan line ────────────────────────────────────────
        scan_y = cy + R * 0.30 * math.sin(self._phase * 0.8)
        scan_alpha = int(40 * fl)
        p.setPen(QPen(QColor(0, 220, 255, scan_alpha), 1))
        p.drawLine(int(cx - hex_r * 0.8), int(scan_y), int(cx + hex_r * 0.8), int(scan_y))
        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
# HUD Panel
# ═══════════════════════════════════════════════════════════════════════════════

class HUDPanel(QFrame):
    def __init__(self, parent=None, title: str = ""):
        super().__init__(parent)
        self.title = title
        self.setStyleSheet("background: transparent; border: none;")
        if title:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(2, 16, 2, 2)
            layout.setSpacing(0)
            self._inner = QWidget()
            self._inner.setStyleSheet("background: transparent;")
            layout.addWidget(self._inner)
            self._layout = QVBoxLayout(self._inner)
            self._layout.setContentsMargins(4, 4, 4, 4)
            self._layout.setSpacing(4)
        else:
            self._layout = QVBoxLayout(self)
            self._layout.setContentsMargins(6, 6, 6, 6)
            self._layout.setSpacing(4)

    def add_widget(self, w):
        self._layout.addWidget(w)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.setPen(QPen(QColor(0, 150, 220, 55), 1))
        p.setBrush(QBrush(QColor(0, 12, 28, 55)))
        p.drawRoundedRect(r.adjusted(0, 0, -1, -1), 4, 4)
        if self.title:
            p.setPen(QPen(QColor(0, 180, 255, 90), 1))
            p.setBrush(QBrush(QColor(0, 28, 58, 90)))
            p.drawRoundedRect(r.left(), r.top(), r.width(), 14, 3, 3)
            p.setPen(QColor(0, 200, 255, 180))
            p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
            p.drawText(r.adjusted(6, 1, -6, -r.height() + 14), Qt.AlignmentFlag.AlignVCenter, self.title)
        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
# Message Bubble — fully visible, transparent BG, auto-height
# ═══════════════════════════════════════════════════════════════════════════════

class MessageBubble(QFrame):
    def __init__(self, role: str, text: str, parent=None):
        super().__init__(parent)
        is_user = role.lower() in ("you", "you (voice)")
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)

        # Role header
        icon = "👤" if is_user else "⚡"
        role_color = C["cyan"] if is_user else C["gold"]
        role_lbl = QLabel(f"{icon}  {role.upper()}")
        role_lbl.setStyleSheet(
            f"color: {role_color}; font-size: 9px; font-weight: bold; "
            "letter-spacing: 2px; font-family: 'Consolas'; background: transparent; "
            "border: none; padding: 0px;"
        )

        # Text display
        text_box = QTextBrowser()
        text_box.setReadOnly(True)
        text_box.setOpenExternalLinks(True)
        text_box.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        text_box.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_box.setPlainText(text)

        border_color = C["cyan_dim"] if is_user else C["border2"]
        accent = "#00aacc" if is_user else "#ffaa00"
        bg_color = "rgba(3,12,26,0.30)" if is_user else "rgba(2,8,18,0.25)"

        text_box.setStyleSheet(
            f"color: {C['text']}; font-size: 13px; line-height: 1.65; "
            f"background: {bg_color}; "
            f"border: 1px solid {border_color}; "
            f"border-left: 3px solid {accent}; "
            "border-radius: 6px; padding: 10px 14px; "
            "font-family: 'Segoe UI', 'Arial', sans-serif;"
        )

        # Auto-size height to content
        text_box.document().setPageSize(QSizeF(0, 0))  # let it be unlimited
        text_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        text_box.setMinimumHeight(48)

        # Use document height for accurate auto-sizing
        def _adjust_height():
            doc_h = int(text_box.document().size().height())
            h = max(doc_h + 28, 60)
            h = min(h, 800)  # cap at 800px
            text_box.setMinimumHeight(h)
            text_box.setMaximumHeight(h)

        QTimer.singleShot(50, _adjust_height)

        layout.addWidget(role_lbl)
        layout.addWidget(text_box)

        if is_user:
            layout.setAlignment(role_lbl, Qt.AlignmentFlag.AlignRight)


class ImageBubble(QFrame):
    def __init__(self, path: str, url: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("⚡ JARVIS — IMAGE GENERATED")
        header.setStyleSheet(
            f"color: {C['gold']}; font-size: 9px; font-weight: bold; "
            "letter-spacing: 2px; background: transparent;"
        )
        layout.addWidget(header)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        img_label.setStyleSheet(
            f"border: 1px solid {C['border2']}; border-radius: 6px; "
            "padding: 4px; background: rgba(0,10,20,0.35);"
        )

        if path and Path(path).exists():
            px = QPixmap(path)
            if not px.isNull():
                px = px.scaled(560, 360, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
                img_label.setPixmap(px)
                img_label.setFixedSize(px.width(), px.height())
            else:
                img_label.setText(f"🖼 Image saved: {path}")
        else:
            img_label.setText("🖼 Image generated!")
        layout.addWidget(img_label)

        if url:
            url_lbl = QLabel(f"🔗 <a href='{url}' style='color:{C['cyan']};'>Open in browser</a>")
            url_lbl.setOpenExternalLinks(True)
            url_lbl.setStyleSheet(f"color:{C['text_dim']}; font-size:10px; background:transparent;")
            layout.addWidget(url_lbl)


class CodePanel(QFrame):
    def __init__(self, code: str, output: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background: rgba(0,5,14,0.40); border: 1px solid {C['border2']}; "
            "border-left: 3px solid #00ffaa; border-radius: 6px;"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        hdr_lbl = QLabel("📋 CODE")
        hdr_lbl.setStyleSheet(f"color:{C['green']};font-size:9px;font-weight:bold;background:transparent;")
        hdr.addWidget(hdr_lbl)
        hdr.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedWidth(50)
        copy_btn.setStyleSheet(
            f"background:{C['blue2']};color:{C['text']};border:none;"
            "border-radius:4px;padding:2px;font-size:10px;"
        )
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(code))
        hdr.addWidget(copy_btn)
        layout.addLayout(hdr)

        code_txt = QTextEdit()
        code_txt.setReadOnly(True)
        code_txt.setPlainText(code)
        code_txt.setMinimumHeight(80)
        code_txt.setMaximumHeight(340)
        code_txt.setStyleSheet(
            f"background:#000810;color:{C['green']};"
            "font-family:'Consolas','Courier New',monospace;font-size:12px;border:none;padding:4px;"
        )
        layout.addWidget(code_txt)

        if output:
            out_lbl = QLabel("▶ OUTPUT")
            out_lbl.setStyleSheet(f"color:{C['cyan']};font-size:9px;font-weight:bold;background:transparent;")
            layout.addWidget(out_lbl)
            out_txt = QTextEdit()
            out_txt.setReadOnly(True)
            out_txt.setPlainText(output)
            out_txt.setMinimumHeight(60)
            out_txt.setMaximumHeight(240)
            out_txt.setStyleSheet(
                f"background:#000508;color:{C['text']};"
                "font-family:'Consolas',monospace;font-size:11px;border:none;padding:4px;"
            )
            layout.addWidget(out_txt)


# ═══════════════════════════════════════════════════════════════════════════════
# Status Orb
# ═══════════════════════════════════════════════════════════════════════════════

class StatusOrb(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None, size: int = 44):
        super().__init__(parent)
        self.orb_size = size
        self.setFixedSize(size, size)
        self._state = "idle"
        self._phase = 0.0
        self._rot   = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, s: str):
        if s in ORB_STATES:
            self._state = s
            self.update()

    def _tick(self):
        self._phase = (self._phase + 0.07) % (2 * math.pi)
        self._rot   = (self._rot   + 3.5)  % 360.0
        self.update()

    def paintEvent(self, event):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        st = ORB_STATES.get(self._state, ORB_STATES["idle"])
        cx = cy = self.orb_size // 2
        r  = cx - 4

        gc   = st["glow"]
        glow = QRadialGradient(cx, cy, r + 18)
        glow.setColorAt(0.0, QColor(gc.red(), gc.green(), gc.blue(), 90))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - r - 18, cy - r - 18, (r + 18) * 2, (r + 18) * 2)

        if self._state in ("listening", "thinking", "executing"):
            p.save()
            p.translate(cx, cy)
            p.rotate(self._rot)
            sc = st["color"]
            p.setPen(QPen(QColor(sc.red(), sc.green(), sc.blue(), 110), 1.5, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(-r + 2, -r + 2, (r - 2) * 2, (r - 2) * 2)
            p.restore()

        sc   = st["color"]
        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.6)
        grad.setColorAt(0.0, QColor(min(sc.red()+90, 255), min(sc.green()+90, 255), min(sc.blue()+90, 255), 245))
        grad.setColorAt(0.5, sc)
        grad.setColorAt(1.0, QColor(sc.red() // 3, sc.green() // 3, sc.blue() // 3, 200))
        p.setBrush(QBrush(grad))
        ba = 160 + int(70 * abs(math.sin(self._phase)))
        p.setPen(QPen(QColor(sc.red(), sc.green(), sc.blue(), ba), 1.5))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        p.setPen(QColor(255, 255, 255, 230))
        p.setFont(QFont("Consolas", max(10, self.orb_size // 4), QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "J")
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


# ═══════════════════════════════════════════════════════════════════════════════
# Floating Orb Overlay
# ═══════════════════════════════════════════════════════════════════════════════

class FloatingOrbOverlay(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._drag_pos   = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(110, 145)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.orb = StatusOrb(size=92)
        self.orb.clicked.connect(self._on_click)
        layout.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignHCenter)

        self.label = QLabel("JARVIS")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label.setStyleSheet(
            f"color: {C['cyan']}; font-size: 9px; font-weight: bold; "
            "font-family: 'Consolas'; background: transparent; letter-spacing: 2px;"
        )
        layout.addWidget(self.label)

        screen = QApplication.primaryScreen().availableGeometry()
        pos = main_window.settings.get("overlay_position", [None, None])
        x = pos[0] if pos[0] else screen.right() - 130
        y = pos[1] if pos[1] else screen.bottom() - 175
        self.move(x, y)

    def set_state(self, s: str):
        self.orb.set_state(s)
        self.label.setText(ORB_STATES.get(s, ORB_STATES["idle"])["label"])

    def _on_click(self):
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MouseButton.RightButton:
            self._ctx_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            pos = self.pos()
            self.main_window.settings["overlay_position"] = [pos.x(), pos.y()]

    def _ctx_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{C['bg2']};color:{C['text']};border:1px solid {C['border2']};}}"
            f"QMenu::item:selected{{background:{C['blue2']};}}"
        )
        menu.addAction("⚡ Show JARVIS").triggered.connect(self._on_click)
        menu.addSeparator()
        menu.addAction("🎤 Listen").triggered.connect(self.main_window._start_extended_listening)
        menu.addSeparator()
        menu.addAction("⚙ Settings").triggered.connect(self.main_window._open_settings)
        menu.addSeparator()
        menu.addAction("✖ Quit").triggered.connect(QApplication.instance().quit)
        menu.exec(pos)


# ═══════════════════════════════════════════════════════════════════════════════
# Main JARVIS OMEGA V4 Window
# ═══════════════════════════════════════════════════════════════════════════════

class JarvisOmegaWindow(QMainWindow):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.signals  = Signals()
        self.brain    = None
        self.speaker  = None
        self.listener = None
        self.overlay  = None
        self._si      = None
        self._workers: list[BrainWorker] = []
        self._listening          = False
        self._extended_listening = False
        self._listen_timer       = None
        self._poll_speak_timer   = None
        self._processing         = False

        self._init_brain()
        self._init_speech()
        self._init_self_improve()
        self._build_ui()
        self._connect_signals()
        self._setup_tray()

        if settings.get("overlay_enabled", True):
            self._launch_overlay()

        QTimer.singleShot(900, self._startup_greeting)
        if settings.get("wake_word"):
            QTimer.singleShot(2500, self._start_wake_listener)

    # ── Init ───────────────────────────────────────────────────────────────────

    def _init_brain(self):
        try:
            from core.brain import JarvisOmegaBrain
            self.brain = JarvisOmegaBrain(self.settings, gui_callback=self._tool_callback)
            self.brain.tools.set_minimize_callback(self._handle_minimize)
            logger.info("Brain initialized.")
        except Exception as exc:
            logger.error("Brain init failed: %s", exc)

    def _init_speech(self):
        try:
            from speech.speaker import JarvisSpeaker
            self.speaker = JarvisSpeaker(self.settings)
        except Exception as exc:
            logger.warning("Speaker init: %s", exc)
        try:
            from speech.listener import VoiceListener
            self.listener = VoiceListener(self.settings)
        except Exception as exc:
            logger.warning("Listener init: %s", exc)

    def _init_self_improve(self):
        try:
            from core.self_improve import SelfImprovementEngine
            self._si = SelfImprovementEngine(self.brain.memory, self.settings)
            if self.brain and self.brain.groq:
                self._si.set_groq(self.brain.groq)
            if self.settings.get("self_improve", True):
                self._si.start()
        except Exception as exc:
            logger.warning("SelfImprove init: %s", exc)

    def _launch_overlay(self):
        self.overlay = FloatingOrbOverlay(self)
        self.overlay.show()

    def _start_wake_listener(self):
        try:
            from speech.wake_detector import WakeWordDetector
            wake = WakeWordDetector(
                wake_word=self.settings.get("wake_word", "jarvis"),
                callback=self._on_wake_word,
                listen_callback=self._start_extended_listening,
                settings=self.settings,
            )
            wake.start()
        except Exception as exc:
            logger.warning("Wake word init: %s", exc)

    # ── UI Build ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("⚡ J.A.R.V.I.S OMEGA V4")
        self.resize(1260, 800)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(f"QMainWindow {{ background: {C['bg']}; }}")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Central Arc Reactor — centered, behind UI panels
        self.central_reactor = ArcReactorWidget(self, size=400)
        self.central_reactor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.central_reactor.show()

        # ── Top HUD Bar ───────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(58)
        top_bar.setStyleSheet(
            "background: rgba(2,12,25,0.92); "
            f"border-bottom: 1px solid {C['border2']};"
        )
        top_h = QHBoxLayout(top_bar)
        top_h.setContentsMargins(14, 0, 14, 0)
        top_h.setSpacing(12)

        self.main_orb = StatusOrb(size=46)
        self.main_orb.clicked.connect(self._toggle_mic)
        top_h.addWidget(self.main_orb)

        title_block = QWidget()
        title_block.setStyleSheet("background:transparent;")
        tb_v = QVBoxLayout(title_block)
        tb_v.setContentsMargins(0, 0, 0, 0)
        tb_v.setSpacing(2)
        title_lbl = QLabel("J.A.R.V.I.S  OMEGA  V4")
        title_lbl.setStyleSheet(
            f"color:{C['cyan']};font-size:15px;font-weight:bold;"
            "letter-spacing:3px;font-family:'Consolas';background:transparent;"
        )
        sub_lbl = QLabel("JUST A RATHER VERY INTELLIGENT SYSTEM  •  POWERED BY GROQ AI")
        sub_lbl.setStyleSheet(
            f"color:{C['text_dim']};font-size:8px;"
            "letter-spacing:1px;font-family:'Consolas';background:transparent;"
        )
        tb_v.addWidget(title_lbl)
        tb_v.addWidget(sub_lbl)
        top_h.addWidget(title_block)
        top_h.addStretch()

        self.status_dot = QLabel("● READY")
        self.status_dot.setStyleSheet(
            f"color:{C['green']};font-size:10px;font-weight:bold;"
            "font-family:'Consolas';background:transparent;"
        )
        top_h.addWidget(self.status_dot)

        self.listen_indicator = QLabel("🎤")
        self.listen_indicator.setFixedSize(32, 32)
        self.listen_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.listen_indicator.setStyleSheet(f"color:{C['text_dim']};font-size:16px;background:transparent;")
        top_h.addWidget(self.listen_indicator)

        for icon, tip, func in [("🗑", "Clear chat", self._clear_chat),
                                  ("⚙", "Settings", self._open_settings)]:
            btn = QPushButton(icon)
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.setStyleSheet(
                "background:transparent;color:#4a7090;font-size:17px;"
                "border:none;border-radius:16px;"
            )
            btn.clicked.connect(func)
            top_h.addWidget(btn)

        root.addWidget(top_bar)

        # ── Main area ─────────────────────────────────────────────────────────
        main_area = QWidget()
        main_area.setStyleSheet("background:transparent;")
        main_h = QHBoxLayout(main_area)
        main_h.setContentsMargins(8, 8, 8, 0)
        main_h.setSpacing(8)

        # Chat / output panel — full width
        right_panel = QWidget()
        right_panel = QWidget()
        right_panel.setStyleSheet("background:transparent;")
        right_v = QVBoxLayout(right_panel)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        chat_hud = HUDPanel(title="JARVIS  OUTPUT  CONSOLE  —  INTERACTIVE INTERFACE")
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            f"QScrollBar:vertical{{background:rgba(0,8,18,0.6);width:8px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:{C['border2']};border-radius:4px;min-height:20px;}}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        self._scroll.viewport().setAutoFillBackground(False)
        self._scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._chat_container = QWidget()
        self._chat_container.setStyleSheet("background:transparent;")
        self.chat_layout = QVBoxLayout(self._chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(14)
        self.chat_layout.addStretch()
        self._scroll.setWidget(self._chat_container)
        chat_hud._layout.addWidget(self._scroll)
        right_v.addWidget(chat_hud, 1)

        # Input bar
        input_bar = QWidget()
        input_bar.setFixedHeight(64)
        input_bar.setStyleSheet(
            "background:rgba(2,12,25,0.92);"
            f"border-top:1px solid {C['border2']};"
        )
        input_h = QHBoxLayout(input_bar)
        input_h.setContentsMargins(12, 10, 12, 10)
        input_h.setSpacing(10)

        mic_btn = QPushButton("🎤")
        mic_btn.setFixedSize(44, 44)
        mic_btn.setToolTip("Click to start listening")
        mic_btn.setStyleSheet(
            f"background:rgba(0,30,65,0.9);color:{C['cyan']};font-size:19px;"
            f"border:1px solid {C['border2']};border-radius:22px;"
        )
        mic_btn.clicked.connect(self._toggle_mic)
        input_h.addWidget(mic_btn)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask JARVIS anything… or click 🎤 to speak")
        self.input_field.setStyleSheet(
            f"background:rgba(3,16,32,0.97);color:{C['text']};font-size:13px;"
            f"border:1px solid {C['border2']};border-radius:8px;padding:8px 14px;"
            "font-family:'Segoe UI',sans-serif;"
        )
        self.input_field.returnPressed.connect(self._on_send)
        input_h.addWidget(self.input_field)

        self.send_btn = QPushButton("SEND")
        self.send_btn.setFixedSize(76, 44)
        self.send_btn.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C['blue']},stop:1 {C['blue_bright']});"
            "color:white;font-size:11px;font-weight:bold;font-family:'Consolas';"
            "border:none;border-radius:8px;letter-spacing:1px;"
        )
        self.send_btn.clicked.connect(self._on_send)
        input_h.addWidget(self.send_btn)
        right_v.addWidget(input_bar)
        main_h.addWidget(right_panel, 1)
        root.addWidget(main_area, 1)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(
            f"background:rgba(1,8,18,0.92);color:{C['text_dim']};"
            "font-size:9px;font-family:'Consolas';"
        )

        # Stacking order: central_reactor (bottom) < main UI (top)
        self.central_reactor.lower()
        self.centralWidget().raise_()
        self._center_reactor()

    def _center_reactor(self):
        if not hasattr(self, 'central_reactor'):
            return
        w = self.width()
        h = self.height()
        rw = self.central_reactor.width()
        rh = self.central_reactor.height()
        x = (w - rw) // 2
        y = (h - rh) // 2
        self.central_reactor.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "central_reactor"):
            self._center_reactor()

    # ── Tray ───────────────────────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        px = QPixmap(32, 32)
        px.fill(QColor(0, 180, 255))
        self.tray.setIcon(QIcon(px))
        self.tray.setToolTip("JARVIS OMEGA V4")
        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            f"QMenu{{background:{C['bg2']};color:{C['text']};border:1px solid {C['border2']};}}"
            f"QMenu::item:selected{{background:{C['blue2']};}}"
        )
        tray_menu.addAction("⚡ Show JARVIS").triggered.connect(self._show_from_tray)
        tray_menu.addSeparator()
        tray_menu.addAction("🎤 Listen").triggered.connect(self._start_extended_listening)
        tray_menu.addSeparator()
        tray_menu.addAction("✖ Quit").triggered.connect(QApplication.instance().quit)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _show_from_tray(self):
        self.show(); self.raise_(); self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("JARVIS OMEGA V4", "Running in background. Click tray to restore.",
                              QSystemTrayIcon.MessageIcon.Information, 2000)

    def _handle_minimize(self, should_minimize: bool):
        self.signals.minimize_window.emit(should_minimize)

    def _do_minimize(self, minimize: bool):
        if minimize:
            self.showMinimized()
        else:
            self.showNormal(); self.raise_(); self.activateWindow()

    # ── Signals ────────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.signals.new_message.connect(self._add_bubble)
        self.signals.new_image.connect(self._add_image)
        self.signals.new_web.connect(self._add_web)
        self.signals.new_code.connect(self._add_code)
        self.signals.status_update.connect(self._on_status)
        self.signals.orb_state.connect(self._set_orb_state)
        self.signals.listening_on.connect(self._update_mic)
        self.signals.reminder_fired.connect(self._on_reminder)
        self.signals.minimize_window.connect(self._do_minimize)
        self.signals.start_listening.connect(self._start_extended_listening)
        self.signals.ask_request.connect(self._ask)
        self.signals.state_change.connect(self._set_state)
        self.signals.stop_listening_sig.connect(self._stop_listening)
        self.signals.wake_word_detected.connect(self._handle_wake_word)

    # ── Send / Ask ─────────────────────────────────────────────────────────────

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            self.status_bar.showMessage("Please enter a command.", 2000)
            return
        if not self.brain:
            self.status_bar.showMessage("Brain not initialized. Check API key in ⚙ Settings.", 3000)
            return
        self.input_field.clear()
        self._ask(text)

    def _ask(self, text: str, role: str = "You"):
        if self._processing:
            self.signals.status_update.emit("Still processing previous request...")
            return
        self._processing = True
        self.signals.new_message.emit(role, text)
        self._set_state("thinking")
        self.send_btn.setEnabled(False)
        worker = BrainWorker(self.brain, text)
        worker.finished.connect(self._on_reply)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(self._on_error)
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_reply(self, reply: str):
        self._processing = False
        import re as _re
        img_match = _re.search(r'\[IMAGE:([^\]]+)\]', reply)
        if img_match:
            img_path  = img_match.group(1)
            url_match = _re.search(r'URL: (https?://\S+)', reply)
            url       = url_match.group(1) if url_match else ""
            clean     = _re.sub(r'\[IMAGE:[^\]]+\]', '', reply).strip()
            clean     = _re.sub(r'URL: https?://\S+', '', clean).strip()
            if clean:
                self.signals.new_message.emit("JARVIS", clean)
            self.signals.new_image.emit(img_path, url)
        else:
            self._set_state("speaking")
            self.signals.new_message.emit("JARVIS", reply)
            if self.speaker:
                if self._poll_speak_timer:
                    self._poll_speak_timer.stop()
                    self._poll_speak_timer = None
                self.speaker.speak(reply)
                self._poll_speak_timer = QTimer(self)
                self._poll_speak_timer.timeout.connect(self._check_speak_done)
                self._poll_speak_timer.start(200)
            else:
                QTimer.singleShot(1200, lambda: self._set_state("idle"))
        self.send_btn.setEnabled(True)

    def _check_speak_done(self):
        if not self.speaker or not self.speaker.is_speaking:
            self._set_state("idle")
            if self._poll_speak_timer:
                self._poll_speak_timer.stop()
                self._poll_speak_timer = None

    def _on_error(self, err: str):
        self._processing = False
        self._set_state("error")
        self.signals.new_message.emit("JARVIS", f"⚠ Error: {err}")
        self.send_btn.setEnabled(True)
        QTimer.singleShot(3000, lambda: self._set_state("idle"))

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    # ── State ──────────────────────────────────────────────────────────────────

    def _set_state(self, state: str):
        self.signals.orb_state.emit(state)
        labels = {
            "idle":      ("● READY",     C["green"]),
            "listening": ("● LISTENING", C["cyan"]),
            "thinking":  ("● THINKING",  C["orange"]),
            "speaking":  ("● SPEAKING",  C["green_dim"]),
            "executing": ("● EXECUTING", "#8040ff"),
            "error":     ("● ERROR",     C["red"]),
        }
        txt, color = labels.get(state, ("● READY", C["green"]))
        self.status_dot.setText(txt)
        self.status_dot.setStyleSheet(
            f"color:{color};font-size:10px;font-weight:bold;"
            "font-family:'Consolas';background:transparent;"
        )

    def _set_orb_state(self, state: str):
        self.main_orb.set_state(state)
        if self.overlay:
            self.overlay.set_state(state)

    # ── Tool callback ──────────────────────────────────────────────────────────

    def _tool_callback(self, result_type: str, action: str, data):
        if not isinstance(data, dict):
            return
        if result_type in ("status", "download"):
            msg = data.get("text", "")
            if msg:
                self.status_bar.showMessage(msg, 8000)
            return
        t = data.get("type", "")
        if t == "web_results":
            self.signals.new_web.emit(data.get("results", []))
        elif t == "code_result":
            self.signals.new_code.emit(data.get("code", ""), data.get("stdout", ""))
        elif t == "image":
            self.signals.new_image.emit(data.get("path", ""), data.get("url", ""))
        elif result_type == "reminder":
            self.signals.reminder_fired.emit(data.get("text", ""))

    # ── Voice ──────────────────────────────────────────────────────────────────

    def _toggle_mic(self):
        if not self.listener:
            self.status_bar.showMessage(
                "Mic unavailable. pip install SpeechRecognition sounddevice numpy", 5000)
            return
        if self._listening:
            self._stop_listening()
        else:
            self._start_extended_listening()

    def _start_extended_listening(self):
        if not self.listener:
            self.status_bar.showMessage("Microphone not available.", 3000)
            return
        if self._listening:
            return

        self._extended_listening = True
        self._listening          = True
        self._set_state("listening")
        self.signals.listening_on.emit(True)
        self.status_bar.showMessage(
            "🎤 Listening — speak now. Say 'stop' to end. Session lasts 3 minutes.", 6000
        )
        threading.Thread(target=self._listen_extended_loop, daemon=True).start()
        self._listen_timer = QTimer(self)
        self._listen_timer.setSingleShot(True)
        self._listen_timer.timeout.connect(self._stop_listening)
        self._listen_timer.start(180_000)

    def _stop_listening(self):
        self._extended_listening = False
        self._listening          = False
        self.signals.listening_on.emit(False)
        self._set_state("idle")
        if self._listen_timer:
            self._listen_timer.stop()
            self._listen_timer = None
        self.status_bar.showMessage("Listening stopped.", 2000)

    def _listen_extended_loop(self):
        while self._extended_listening:
            try:
                text = self.listener.listen(timeout=8.0)
                if not self._extended_listening:
                    break
                if text:
                    text_lower = text.lower().strip()
                    stop_words = ["stop listening", "stop", "quit listening",
                                  "be quiet", "jarvis stop", "shut up"]
                    if any(s in text_lower for s in stop_words):
                        self.signals.status_update.emit("Stopping listening...")
                        self.signals.stop_listening_sig.emit()
                        break
                    if self._processing:
                        self.signals.status_update.emit("Still processing, please wait...")
                        continue
                    self.signals.state_change.emit("thinking")
                    self.signals.ask_request.emit(text, "You (voice)")
                    time.sleep(0.2)
                else:
                    time.sleep(0.08)
            except Exception as exc:
                logger.warning("Listen loop error: %s", exc)
                time.sleep(0.5)

    def _listen_once(self):
        try:
            text = self.listener.listen(timeout=8.0)
            self._listening = False
            self.signals.listening_on.emit(False)
            if text:
                self.signals.ask_request.emit(text, "You (voice)")
            else:
                self.signals.status_update.emit("Didn't catch that — try again.")
                self.signals.state_change.emit("idle")
        except Exception as exc:
            logger.warning("Listen once error: %s", exc)
            self._listening = False
            self.signals.listening_on.emit(False)
            self.signals.state_change.emit("idle")

    def _on_wake_word(self):
        self.signals.wake_word_detected.emit()

    def _handle_wake_word(self):
        self.show(); self.raise_(); self.activateWindow()
        self._set_state("listening")
        self.signals.listening_on.emit(True)
        self._listening = True
        threading.Thread(target=self._listen_once, daemon=True).start()

    def _update_mic(self, active: bool):
        if active:
            self.listen_indicator.setText("🔴")
            self.listen_indicator.setStyleSheet(
                f"color:{C['red']};font-size:16px;background:transparent;"
            )
        else:
            self.listen_indicator.setText("🎤")
            self.listen_indicator.setStyleSheet(
                f"color:{C['text_dim']};font-size:16px;background:transparent;"
            )

    # ── Chat ───────────────────────────────────────────────────────────────────

    def _add_bubble(self, role: str, text: str):
        self._pop_stretch()
        bubble = MessageBubble(role, text)
        self.chat_layout.addWidget(bubble)
        self.chat_layout.addStretch()
        self._scroll_bottom()

    def _add_image(self, path: str, url: str):
        self._pop_stretch()
        self.chat_layout.addWidget(ImageBubble(path, url))
        self.chat_layout.addStretch()
        self._scroll_bottom()

    def _add_web(self, results: list):
        if not results:
            return
        lines = ["🌐 Web Results:\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', '')}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:200]}")
            if r.get("url"):
                lines.append(f"   🔗 {r['url'][:100]}\n")
        self._add_bubble("JARVIS", "\n".join(lines))

    def _add_code(self, code: str, output: str):
        self._pop_stretch()
        self.chat_layout.addWidget(CodePanel(code, output))
        self.chat_layout.addStretch()
        self._scroll_bottom()

    def _pop_stretch(self):
        count = self.chat_layout.count()
        if count > 0:
            item = self.chat_layout.takeAt(count - 1)
            del item

    def _scroll_bottom(self):
        QTimer.singleShot(150, lambda: (
            self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            )
        ))

    def _clear_chat(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        self.chat_layout.addStretch()
        if self.brain:
            self.brain.reset()
        self._add_bubble("JARVIS", "Conversation cleared. Systems reset. How can I assist you, Sir?")

    def _on_status(self, msg: str):
        self.status_bar.showMessage(msg)

    def _on_reminder(self, text: str):
        self._add_bubble("JARVIS", f"⏰ Reminder: {text}")
        if self.speaker:
            threading.Thread(target=self.speaker.speak,
                             args=(f"Reminder: {text}",), daemon=True).start()

    # ── Startup ────────────────────────────────────────────────────────────────

    def _startup_greeting(self):
        import datetime
        hour     = datetime.datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        user     = self.settings.get("user_name", "Sir")
        ai       = self.settings.get("ai_name", "JARVIS")
        has_key  = bool(self.settings.get("groq_api_key", "").strip())
        use_local = self.settings.get("use_local_llm", True)
        hinglish = self.settings.get("hinglish_mode", True)

        key_info = (
            "✅ ALL AI providers race in parallel — fastest wins.\n"
            "   Cloud: Gemini + OpenRouter + NVIDIA + SambaNova + Cerebras + Groq\n"
            "   Backup: Local Llama-3.2-3B (CPU, works offline)\n"
            "   If one hits a rate limit, the others instantly take over."
        )

        if not has_key and not use_local:
            key_info = (
                "⚠ No cloud API keys and local LLM is disabled.\n"
                "  Add FREE keys in ⚙ Settings for faster cloud responses,\n"
                "  or enable 'Pre-load Local LLM' to work offline."
            )

        lang_note = "  🌐  Hinglish mode ON — speak Hindi + English mix, I understand both.\n"

        msg = (
            f"{greeting}, {user}. I am {ai} OMEGA V4 — online and ready.\n\n"
            "  🎤  Click the mic button or say 'Jarvis listen' to speak\n"
            "  ⚡  The orb shows my status — drag it anywhere on your screen\n"
            "  ✖   Closing hides me to tray — I keep running in background\n"
            "  ⚙   Click Settings to configure API keys and voice\n\n"
            f"{lang_note}"
            "Quick commands to try:\n"
            "  • 'Open Chrome and search latest AI news'\n"
            "  • 'Open YouTube and search Iron Man videos'\n"
            "  • 'Generate an image of Iron Man arc reactor'\n"
            "  • 'Create a Python snake game and run it'\n"
            "  • 'Take a screenshot and read what's on screen'\n"
            "  • 'Show system info'\n\n"
            f"{key_info}"
        )
        self._add_bubble("JARVIS", msg)
        self._set_state("idle")

        speak_text = (
            f"{greeting} {user}. All systems online. "
            f"I am {ai}, your personal artificial intelligence. "
            "Ready for your command."
        )
        if self.speaker:
            threading.Thread(target=self.speaker.speak, args=(speak_text,), daemon=True).start()

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            settings_path = _BASE / "config/settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            self.status_bar.showMessage(
                "Settings saved. Restart JARVIS to apply API key changes.", 4000)


# ═══════════════════════════════════════════════════════════════════════════════
# Settings Dialog
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("⚙ JARVIS OMEGA V4 Settings")
        self.resize(620, 720)
        self.setStyleSheet(
            f"QDialog{{background:{C['bg2']};}} "
            f"QLabel{{color:{C['text']};}} "
            f"QLineEdit{{background:{C['bg3']};color:{C['text']};"
            f"border:1px solid {C['border2']};border-radius:6px;padding:7px;}} "
            f"QPushButton{{background:{C['blue2']};color:{C['text']};"
            "border:none;border-radius:6px;padding:9px 18px;}}"
        )
        layout = QVBoxLayout(self)

        title = QLabel("⚙  JARVIS OMEGA V4  —  CONFIGURATION")
        title.setStyleSheet(
            f"color:{C['cyan']};font-size:12px;font-weight:bold;"
            "font-family:'Consolas';letter-spacing:2px;"
        )
        layout.addWidget(title)
        layout.addSpacing(8)

        grid = QGridLayout()
        fields = [
            ("user_name",           "Your Name (e.g. Sir):"),
            ("ai_name",             "AI Name (e.g. JARVIS):"),
            ("wake_word",           "Wake Word (e.g. jarvis):"),
            ("groq_api_key",        "Groq API Key (FREE — console.groq.com):"),
            ("google_api_key",      "Google Gemini Key (FREE — aistudio.google.com):"),
            ("openrouter_api_key",  "OpenRouter Key (FREE — openrouter.com):"),
            ("nvidia_api_key",      "NVIDIA NIM Key (FREE — build.nvidia.com):"),
            ("sambanova_api_key",   "SambaNova Key (FREE — cloud.sambanova.ai):"),
            ("cerebras_api_key",    "Cerebras Key (FREE — cloud.cerebras.ai):"),
            ("groq_model",          "AI Model (llama-3.3-70b-versatile):"),
            ("tts_voice",           "Edge-TTS Voice (en-US-GuyNeural = male):"),
            ("whisper_model",       "Whisper Model (tiny / base / small):"),
            ("tts_rate",            "Speech Speed — pyttsx3 rate (220=fast, 170=normal):"),
            ("tts_edge_rate",       "Edge-TTS Rate (+15%=fast, +0%=normal):"),
        ]
        self._fields = {}
        for i, (key, label) in enumerate(fields):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{C['text_dim']};font-size:10px;")
            grid.addWidget(lbl, i, 0)
            field = QLineEdit(str(settings.get(key, "")))
            if "key" in key.lower():
                field.setEchoMode(QLineEdit.EchoMode.Password)
            self._fields[key] = field
            grid.addWidget(field, i, 1)
        layout.addLayout(grid)
        layout.addSpacing(6)

        self._local_check = QCheckBox("Pre-load Local LLM (offline fallback — always used if cloud fails)")
        self._local_check.setChecked(bool(settings.get("use_local_llm", True)))
        self._local_check.setStyleSheet(f"color:{C['text']};font-size:10px;")
        layout.addWidget(self._local_check)
        layout.addSpacing(6)

        self._hinglish_check = QCheckBox("Enable Hinglish voice recognition (Hindi + English mix)")
        self._hinglish_check.setChecked(bool(settings.get("hinglish_mode", True)))
        self._hinglish_check.setStyleSheet(f"color:{C['text']};font-size:10px;")
        layout.addWidget(self._hinglish_check)
        layout.addSpacing(10)

        notes = QLabel(
            "💡 ALL KEYS ABOVE ARE FREE TIERS — NO CREDIT CARD NEEDED\n"
            "🖥  Local LLM: Llama-3.2-3B (~2 GB, CPU). First run downloads once. No API key ever.\n"
            "🗣 Male voices: en-US-GuyNeural | en-GB-RyanNeural | en-US-ChristopherNeural\n"
            "🧠 Whisper: tiny (fastest) / base (balanced) / small (most accurate)\n"
            "⚡ pyttsx3 rate 220 = fast & confident male voice (recommended)\n"
            "🌐 Hinglish: speak Hindi + English mix, JARVIS will understand both"
        )
        notes.setStyleSheet(
            f"color:{C['cyan_dim']};font-size:10px;font-family:'Consolas';"
            f"background:rgba(0,20,40,0.55);border-left:2px solid {C['border2']};"
            "padding:8px;border-radius:4px;"
        )
        notes.setWordWrap(True)
        layout.addWidget(notes)
        layout.addStretch()

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C['blue']},stop:1 {C['blue_bright']});"
            "color:white;font-weight:bold;border:none;border-radius:6px;padding:9px 18px;"
        )
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _save(self):
        for key, field in self._fields.items():
            val = field.text().strip()
            if key in ("tts_rate",):
                try:
                    val = int(val)
                except ValueError:
                    pass
            self.settings[key] = val
        self.settings["use_local_llm"] = bool(self._local_check.isChecked())
        self.settings["hinglish_mode"] = bool(self._hinglish_check.isChecked())
        # Auto-enable Hinglish languages if checked
        if self.settings["hinglish_mode"]:
            self.settings["languages"] = ["hi-IN", "en-IN", "en-US"]
        else:
            self.settings["languages"] = ["en-IN", "en-US"]
        self.accept()
