"""
gui/main_window.py — JARVIS OMEGA V2 GUI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES vs old version:
  ✅ Full text shown — QTextBrowser instead of QLabel (no truncation)
  ✅ Minimal clean interface — no skill panels or clutter
  ✅ Close → hides to system tray (does NOT kill JARVIS)
  ✅ Click floating orb → shows/hides main window
  ✅ Orb is draggable to any screen position
  ✅ VSCode minimize signal when running code
  ✅ Auto-scroll to bottom after each message
  ✅ All settings in right-click menu, not cluttering main UI
"""

import sys
import json
import threading
import logging
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QLineEdit, QPushButton, QLabel, QFrame, QStatusBar,
    QSystemTrayIcon, QMenu, QApplication, QDialog, QGridLayout,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QThread, QPoint, QSize,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QRadialGradient, QIcon, QAction,
    QBrush, QPen, QPixmap, QKeyEvent,
)

logger = logging.getLogger("JARVIS.GUI")
_BASE = Path(__file__).resolve().parent.parent

# ── Color Palette ─────────────────────────────────────────────────────────────
C = {
    "bg":        "#020810",
    "bg2":       "#040d1a",
    "bg3":       "#060f20",
    "panel":     "#07111f",
    "border":    "#0d2540",
    "border2":   "#1a3a5c",
    "cyan":      "#00d4ff",
    "cyan_dim":  "#0088aa",
    "blue":      "#0066cc",
    "blue2":     "#1a4a8a",
    "green":     "#00ff88",
    "green_dim": "#00aa55",
    "orange":    "#ff8c00",
    "red":       "#ff3333",
    "text":      "#e0e8f0",
    "text_dim":  "#6a8aaa",
    "user_bg":   "#0a1e3a",
    "ai_bg":     "#071525",
}

ORB_STATES = {
    "idle":      {"color": QColor(0, 140, 220),  "glow": QColor(0, 80, 180, 60),   "label": "IDLE"},
    "listening": {"color": QColor(0, 220, 255),  "glow": QColor(0, 180, 255, 100), "label": "LISTENING"},
    "thinking":  {"color": QColor(255, 165, 0),  "glow": QColor(255, 120, 0, 80),  "label": "THINKING"},
    "speaking":  {"color": QColor(0, 255, 140),  "glow": QColor(0, 200, 100, 80),  "label": "SPEAKING"},
    "executing": {"color": QColor(100, 50, 255), "glow": QColor(80, 30, 200, 80),  "label": "EXECUTING"},
    "error":     {"color": QColor(255, 50, 50),  "glow": QColor(255, 0, 0, 80),    "label": "ERROR"},
}


# ══════════════════════════════════════════════════════════════════════════════
#  Signal Bridge
# ══════════════════════════════════════════════════════════════════════════════

class Signals(QObject):
    new_message   = pyqtSignal(str, str)   # role, text
    new_web       = pyqtSignal(list)
    new_code      = pyqtSignal(str, str)   # code, output
    status_update = pyqtSignal(str)
    orb_state     = pyqtSignal(str)
    listening_on  = pyqtSignal(bool)
    reminder_fired = pyqtSignal(str)
    minimize_window = pyqtSignal(bool)     # True=minimize, False=restore (NEW)


# ══════════════════════════════════════════════════════════════════════════════
#  Brain Worker Thread
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
#  Neural Orb (animated, draggable)
# ══════════════════════════════════════════════════════════════════════════════

class NeuralOrb(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None, size: int = 120):
        super().__init__(parent)
        self.orb_size  = size
        self.setFixedSize(size, size)
        self._state    = "idle"
        self._phase    = 0.0
        self._ring_rot = 0.0
        self._wave     = [0.0] * 32
        self._drag_pos = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, state: str):
        if state in ORB_STATES:
            self._state = state
            self.update()

    def _tick(self):
        import math
        self._phase    = (self._phase + 0.05) % (2 * 3.14159)
        self._ring_rot = (self._ring_rot + 2.0) % 360.0
        for i in range(len(self._wave)):
            self._wave[i] = (self._wave[i] * 0.85 +
                             0.15 * abs(0.5 * (1 + math.sin(self._phase + i * 0.4))))
        self.update()

    def paintEvent(self, event):
        import math
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        state = ORB_STATES.get(self._state, ORB_STATES["idle"])
        cx = cy = self.orb_size // 2
        r  = cx - 8

        # Glow
        glow_r = r + 16 + int(8 * abs(math.sin(self._phase)))
        glow = QRadialGradient(cx, cy, glow_r)
        gc = state["glow"]
        glow.setColorAt(0.0, QColor(gc.red(), gc.green(), gc.blue(), 80))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2)

        # Rotating rings (thinking/executing)
        if self._state in ("thinking", "executing"):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._ring_rot)
            rc = state["color"]
            for rr, alpha in [(r - 4, 100), (r - 14, 60)]:
                painter.setPen(QPen(QColor(rc.red(), rc.green(), rc.blue(), alpha),
                                    2, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(-rr, -rr, rr * 2, rr * 2)
            painter.restore()

        # Main sphere
        grad = QRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 1.8)
        sc = state["color"]
        grad.setColorAt(0.0, QColor(min(sc.red() + 60, 255), min(sc.green() + 60, 255),
                                    min(sc.blue() + 60, 255), 220))
        grad.setColorAt(0.4, QColor(sc.red() // 3, sc.green() // 3, sc.blue() // 3, 200))
        grad.setColorAt(1.0, QColor(2, 8, 20, 230))
        painter.setBrush(QBrush(grad))
        border_alpha = 160 + int(60 * abs(math.sin(self._phase)))
        painter.setPen(QPen(QColor(sc.red(), sc.green(), sc.blue(), border_alpha), 2))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # State label
        if self.orb_size >= 90:
            font = QFont("Segoe UI", max(14, self.orb_size // 7), QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor(sc.red(), sc.green(), sc.blue(), 230)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "J")

        # Status dot
        dot_c = sc
        painter.setBrush(QBrush(dot_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx + int(r * 0.65) - 5, cy + int(r * 0.65) - 5, 10, 10)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.clicked.emit()


# ══════════════════════════════════════════════════════════════════════════════
#  Floating Orb Overlay (always-on-top, draggable)
# ══════════════════════════════════════════════════════════════════════════════

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
        self.setFixedSize(100, 130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.orb = NeuralOrb(size=90)
        self.orb.clicked.connect(self._on_click)
        layout.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignHCenter)

        self.label = QLabel("JARVIS")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label.setStyleSheet(
            "color: #00d4ff; font-size: 9px; font-weight: bold; "
            "font-family: 'Segoe UI'; background: transparent;"
        )
        layout.addWidget(self.label)

        # Position bottom-right by default
        screen = QApplication.primaryScreen().availableGeometry()
        pos = main_window.settings.get("overlay_position", [None, None])
        x = pos[0] if pos[0] else screen.right() - 120
        y = pos[1] if pos[1] else screen.bottom() - 160
        self.move(x, y)

    def set_state(self, state: str):
        self.orb.set_state(state)

    def _on_click(self):
        """Toggle main window visibility."""
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self._context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            pos = self.pos()
            self.main_window.settings["overlay_position"] = [pos.x(), pos.y()]

    def _context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background:{C['bg2']}; color:{C['text']}; border:1px solid {C['border2']}; }}"
            f"QMenu::item:selected {{ background:{C['blue2']}; }}"
        )
        open_act  = menu.addAction("⚡ Show JARVIS")
        menu.addSeparator()
        mic_act   = menu.addAction("🎤 Listen")
        menu.addSeparator()
        set_act   = menu.addAction("⚙ Settings")
        menu.addSeparator()
        quit_act  = menu.addAction("✖ Quit")

        action = menu.exec(pos)
        if action == open_act:
            self._on_click()
        elif action == mic_act:
            self.main_window._toggle_mic()
        elif action == set_act:
            self.main_window._open_settings()
        elif action == quit_act:
            QApplication.instance().quit()


# ══════════════════════════════════════════════════════════════════════════════
#  Message Bubble — FIXED: uses QTextBrowser for full text display
# ══════════════════════════════════════════════════════════════════════════════

class MessageBubble(QFrame):
    """
    FIX: replaced QLabel with QTextBrowser so all text — no matter how long —
    is fully displayed with scrolling, word-wrap, and selectable text.
    """
    def __init__(self, role: str, text: str, parent=None):
        super().__init__(parent)
        is_user = role.lower() in ("you", "you (voice)")
        self.setContentsMargins(4, 2, 4, 2)

        layout = QVBoxLayout(self)
        layout.setSpacing(3)

        # Role label
        icon = "👤" if is_user else "⚡"
        role_color = C["cyan"] if is_user else C["green"]
        role_lbl = QLabel(f"{icon} {role.upper()}")
        role_lbl.setStyleSheet(
            f"color: {role_color}; font-size: 9px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent;"
        )

        # ── Text display: QTextBrowser (FIXED) ────────────────────────────
        text_box = QTextBrowser()
        text_box.setReadOnly(True)
        text_box.setOpenExternalLinks(True)
        text_box.setPlainText(text)          # plain text — no truncation ever
        # Word wrap — compatible with all PyQt6 versions
        try:
            from PyQt6.QtGui import QTextOption
            text_box.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        except Exception:
            pass  # Default wrapping is fine

        bg     = C["user_bg"] if is_user else C["ai_bg"]
        border = C["cyan_dim"] if is_user else C["border"]
        text_box.setStyleSheet(
            f"color: {C['text']}; font-size: 13px; line-height: 1.5; "
            f"background: {bg}; border: 1px solid {border}; "
            "border-radius: 10px; padding: 10px 14px;"
        )

        # Auto-size height to content — expand as needed, scroll if huge
        text_box.setMinimumHeight(40)
        text_box.setMaximumHeight(600)       # cap at 600px; scrolls inside if longer
        text_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout.addWidget(role_lbl)
        layout.addWidget(text_box)

        align = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
        layout.setAlignment(role_lbl, align)
        layout.setAlignment(text_box, align)


# ══════════════════════════════════════════════════════════════════════════════
#  Code Panel
# ══════════════════════════════════════════════════════════════════════════════

class CodePanel(QFrame):
    def __init__(self, code: str, output: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background: {C['bg2']}; border: 1px solid {C['border2']}; border-radius: 8px;"
        )
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("📋 Code"))
        header.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedWidth(50)
        copy_btn.setStyleSheet(
            f"background:{C['blue2']}; color:{C['text']}; border:none; border-radius:4px; padding:2px;"
        )
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(code))
        header.addWidget(copy_btn)
        layout.addLayout(header)

        from PyQt6.QtWidgets import QTextEdit
        code_txt = QTextEdit()
        code_txt.setReadOnly(True)
        code_txt.setPlainText(code)
        code_txt.setMaximumHeight(200)
        code_txt.setStyleSheet(
            f"background:#000810; color:{C['green']}; "
            "font-family:'Consolas','Courier New',monospace; font-size:12px; border:none;"
        )
        layout.addWidget(code_txt)

        if output:
            from PyQt6.QtWidgets import QTextEdit as QTE2
            out_lbl = QLabel("▶ Output")
            out_lbl.setStyleSheet(f"color:{C['cyan']}; font-size:10px; font-weight:bold;")
            layout.addWidget(out_lbl)
            out_txt = QTE2()
            out_txt.setReadOnly(True)
            out_txt.setPlainText(output)
            out_txt.setMaximumHeight(120)
            out_txt.setStyleSheet(
                f"background:#000508; color:{C['text_dim']}; "
                "font-family:'Consolas',monospace; font-size:11px; border:none;"
            )
            layout.addWidget(out_txt)


# ══════════════════════════════════════════════════════════════════════════════
#  Main JARVIS OMEGA Window (redesigned)
# ══════════════════════════════════════════════════════════════════════════════

class JarvisOmegaWindow(QMainWindow):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings   = settings
        self.signals    = Signals()
        self.brain      = None
        self.speaker    = None
        self.listener   = None
        self.overlay    = None
        self._si        = None
        self._workers: list[BrainWorker] = []
        self._listening = False

        self._init_brain()
        self._init_speech()
        self._init_self_improve()
        self._build_ui()
        self._connect_signals()
        self._setup_tray()

        if settings.get("overlay_enabled", True):
            self._launch_overlay()

        QTimer.singleShot(800, self._startup_greeting)
        if settings.get("wake_word"):
            QTimer.singleShot(2000, self._start_wake_listener)

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_brain(self):
        try:
            from core.brain import JarvisOmegaBrain
            self.brain = JarvisOmegaBrain(self.settings, gui_callback=self._tool_callback)
            # Register minimize callback with tool_manager
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
            self._si = None

    def _launch_overlay(self):
        self.overlay = FloatingOrbOverlay(self)
        self.overlay.show()

    def _start_wake_listener(self):
        try:
            from speech.wake_detector import WakeWordDetector
            wake = WakeWordDetector(
                wake_word=self.settings.get("wake_word", "jarvis"),
                callback=self._on_wake_word,
                settings=self.settings,
            )
            wake.start()
        except Exception as exc:
            logger.warning("Wake word init: %s", exc)

    # ── GUI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("⚡ JARVIS OMEGA")
        self.resize(860, 680)
        self.setMinimumSize(600, 480)
        self.setStyleSheet(f"QMainWindow {{ background: {C['bg']}; }}")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setFixedHeight(52)
        top_bar.setStyleSheet(
            f"background: {C['bg2']}; border-bottom: 1px solid {C['border']};"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 0, 14, 0)
        top_layout.setSpacing(10)

        # Orb (small, clickable = toggle mic)
        self.main_orb = NeuralOrb(size=40)
        self.main_orb.clicked.connect(self._toggle_mic)
        top_layout.addWidget(self.main_orb)

        # Title
        title = QLabel("J.A.R.V.I.S  OMEGA")
        title.setStyleSheet(
            f"color: {C['cyan']}; font-size: 14px; font-weight: bold; "
            "letter-spacing: 2px; font-family: 'Segoe UI';"
        )
        top_layout.addWidget(title)
        top_layout.addStretch()

        # Status dot
        self.status_dot = QLabel("● READY")
        self.status_dot.setStyleSheet(f"color:{C['green']}; font-size:11px; font-weight:bold;")
        top_layout.addWidget(self.status_dot)

        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setStyleSheet(
            f"background: transparent; color: {C['text_dim']}; font-size: 16px; border: none;"
            f"border-radius: 16px;"
        )
        settings_btn.clicked.connect(self._open_settings)
        top_layout.addWidget(settings_btn)

        main_layout.addWidget(top_bar)

        # ── Chat area (scrollable, FIXED) ─────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {C['bg']}; border: none; }}"
            f"QScrollBar:vertical {{ background: {C['bg2']}; width: 6px; }}"
            f"QScrollBar::handle:vertical {{ background: {C['border2']}; border-radius: 3px; }}"
        )

        chat_container = QWidget()
        chat_container.setStyleSheet(f"background: {C['bg']};")
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.setContentsMargins(14, 14, 14, 14)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()

        self._scroll.setWidget(chat_container)
        main_layout.addWidget(self._scroll, 1)

        # ── Input area ────────────────────────────────────────────────────
        input_bar = QWidget()
        input_bar.setFixedHeight(58)
        input_bar.setStyleSheet(
            f"background: {C['bg2']}; border-top: 1px solid {C['border']};"
        )
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(38, 38)
        self.mic_btn.setCheckable(True)
        self.mic_btn.setStyleSheet(
            f"QPushButton {{ background: {C['bg3']}; color: {C['text']}; font-size: 16px; "
            f"border: 1px solid {C['border2']}; border-radius: 19px; }}"
            f"QPushButton:checked {{ background: {C['blue2']}; border-color: {C['cyan']}; }}"
        )
        self.mic_btn.clicked.connect(self._toggle_mic)
        input_layout.addWidget(self.mic_btn)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask JARVIS anything…")
        self.input_field.setStyleSheet(
            f"background: {C['bg3']}; color: {C['text']}; font-size: 13px; "
            f"border: 1px solid {C['border2']}; border-radius: 8px; padding: 8px 12px;"
        )
        self.input_field.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedSize(64, 38)
        self.send_btn.setStyleSheet(
            f"background: {C['blue2']}; color: {C['text']}; font-size: 13px; font-weight: bold; "
            f"border: none; border-radius: 8px;"
        )
        self.send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_bar)

        # ── Status bar ────────────────────────────────────────────────────
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(
            f"background: {C['bg3']}; color: {C['text_dim']}; font-size: 10px;"
        )

    # ── System tray (FIXED: close hides to tray) ──────────────────────────────

    def _setup_tray(self):
        """Set up system tray icon so closing hides the window instead of quitting."""
        self.tray = QSystemTrayIcon(self)

        # Use a colored pixmap as icon
        px = QPixmap(32, 32)
        px.fill(QColor(0, 212, 255))
        self.tray.setIcon(QIcon(px))
        self.tray.setToolTip("JARVIS OMEGA")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            f"QMenu {{ background:{C['bg2']}; color:{C['text']}; border:1px solid {C['border2']}; }}"
            f"QMenu::item:selected {{ background:{C['blue2']}; }}"
        )
        show_act  = tray_menu.addAction("⚡ Show JARVIS")
        tray_menu.addSeparator()
        mic_act   = tray_menu.addAction("🎤 Listen")
        tray_menu.addSeparator()
        quit_act  = tray_menu.addAction("✖ Quit JARVIS")

        show_act.triggered.connect(self._show_from_tray)
        mic_act.triggered.connect(self._toggle_mic)
        quit_act.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def closeEvent(self, event):
        """FIXED: Hide to tray instead of quitting."""
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "JARVIS OMEGA",
            "Running in background. Click the tray icon to restore.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    # ── Minimize/restore for code execution (NEW) ─────────────────────────────

    def _handle_minimize(self, should_minimize: bool):
        """Called by ToolManager when running code — minimize then restore."""
        if should_minimize:
            self.signals.minimize_window.emit(True)
        else:
            QTimer.singleShot(500, lambda: self.signals.minimize_window.emit(False))

    def _do_minimize(self, minimize: bool):
        if minimize:
            self.showMinimized()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    # ── Signal connections ────────────────────────────────────────────────────

    def _connect_signals(self):
        self.signals.new_message.connect(self._add_bubble)
        self.signals.new_web.connect(self._add_web)
        self.signals.new_code.connect(self._add_code)
        self.signals.status_update.connect(self._on_status)
        self.signals.orb_state.connect(self._set_orb_state)
        self.signals.listening_on.connect(self._update_mic)
        self.signals.reminder_fired.connect(self._on_reminder)
        self.signals.minimize_window.connect(self._do_minimize)  # NEW

    # ── Send / process ────────────────────────────────────────────────────────

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text or not self.brain:
            return
        self.input_field.clear()
        self._ask(text)

    def _ask(self, text: str):
        self.signals.new_message.emit("You", text)
        self._set_state("thinking")
        worker = BrainWorker(self.brain, text)
        worker.finished.connect(self._on_reply)
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(self._on_error)
        worker.error.connect(lambda: self._cleanup_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _on_reply(self, reply: str):
        self._set_state("speaking")
        self.signals.new_message.emit("JARVIS", reply)
        if self.speaker:
            threading.Thread(
                target=self._speak_and_idle, args=(reply,), daemon=True
            ).start()
        else:
            QTimer.singleShot(1500, lambda: self._set_state("idle"))

    def _speak_and_idle(self, text: str):
        try:
            self.speaker.speak(text, blocking=True)
        except Exception:
            pass
        self.signals.orb_state.emit("idle")

    def _on_error(self, err: str):
        self._set_state("error")
        self.signals.new_message.emit("JARVIS", f"⚠️ Error: {err}")
        QTimer.singleShot(3000, lambda: self._set_state("idle"))

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    # ── State management ──────────────────────────────────────────────────────

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
        self.status_dot.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")
        self.send_btn.setEnabled(state in ("idle", "error"))

    def _set_orb_state(self, state: str):
        self.main_orb.set_state(state)
        if self.overlay:
            self.overlay.set_state(state)

    # ── Tool callback ─────────────────────────────────────────────────────────

    def _tool_callback(self, result_type: str, action: str, data):
        if not isinstance(data, dict):
            return
        t = data.get("type", "")
        if t == "web_results":
            self.signals.new_web.emit(data.get("results", []))
        elif t == "code_result":
            self.signals.new_code.emit(data.get("code", ""), data.get("stdout", ""))
        elif result_type == "reminder":
            self.signals.reminder_fired.emit(data.get("text", ""))

    # ── Voice ─────────────────────────────────────────────────────────────────

    def _toggle_mic(self):
        if not self.listener:
            self.status_bar.showMessage("Microphone not available.")
            return
        if self._listening:
            self._listening = False
            self.signals.listening_on.emit(False)
        else:
            self._listening = True
            self._set_state("listening")
            self.signals.listening_on.emit(True)
            threading.Thread(target=self._listen_once, daemon=True).start()

    def _listen_once(self):
        try:
            text = self.listener.listen(timeout=10.0)
            self._listening = False
            self.signals.listening_on.emit(False)
            if text:
                self.signals.new_message.emit("You (voice)", text)
                self._ask(text)
            else:
                self.signals.status_update.emit("Didn't catch that — try again.")
                self._set_state("idle")
        except Exception as exc:
            logger.warning("Listen error: %s", exc)
            self._listening = False
            self.signals.listening_on.emit(False)
            self._set_state("idle")

    def _on_wake_word(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._set_state("listening")
        self.signals.listening_on.emit(True)
        self._listening = True
        threading.Thread(target=self._listen_once, daemon=True).start()

    def _update_mic(self, active: bool):
        self.mic_btn.setText("🔴" if active else "🎤")
        self.mic_btn.setChecked(active)

    # ── Chat helpers ──────────────────────────────────────────────────────────

    def _add_bubble(self, role: str, text: str):
        # Remove the stretch, add bubble, add stretch back
        count = self.chat_layout.count()
        if count > 0:
            stretch = self.chat_layout.takeAt(count - 1)
            del stretch

        bubble = MessageBubble(role, text)
        self.chat_layout.addWidget(bubble)
        self.chat_layout.addStretch()
        self._scroll_bottom()

    def _add_web(self, results: list):
        if not results:
            return
        # Show top 3 web results as a simple bubble
        lines = ["🌐 Web Results:"]
        for i, r in enumerate(results[:3], 1):
            lines.append(f"\n{i}. {r.get('title', '')}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:120]}")
            if r.get("url"):
                lines.append(f"   {r['url'][:80]}")
        self._add_bubble("JARVIS", "\n".join(lines))

    def _add_code(self, code: str, output: str):
        count = self.chat_layout.count()
        if count > 0:
            stretch = self.chat_layout.takeAt(count - 1)
            del stretch
        panel = CodePanel(code, output)
        self.chat_layout.addWidget(panel)
        self.chat_layout.addStretch()
        self._scroll_bottom()

    def _scroll_bottom(self):
        QTimer.singleShot(100, lambda: (
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
        self._add_bubble("JARVIS", "Conversation cleared. How can I assist you?")

    def _on_status(self, msg: str):
        self.status_bar.showMessage(msg)

    def _on_reminder(self, text: str):
        self._add_bubble("JARVIS", f"⏰ Reminder: {text}")
        if self.speaker:
            threading.Thread(
                target=self.speaker.speak, args=(f"Reminder: {text}",), daemon=True
            ).start()

    # ── Startup greeting ──────────────────────────────────────────────────────

    def _startup_greeting(self):
        import datetime
        hour    = datetime.datetime.now().hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        user    = self.settings.get("user_name", "Sir")
        ai      = self.settings.get("ai_name", "JARVIS")
        has_key = bool(self.settings.get("groq_api_key", "").strip())
        key_info = "✅ Groq AI connected." if has_key else (
            "⚠️ No API key — get a FREE one at console.groq.com and add to config/settings.json"
        )

        msg = (
            f"{greeting}, {user}. I am {ai} OMEGA V2.\n\n"
            f"  • 🎤 Click the mic or say '{self.settings.get('wake_word', 'jarvis')}' to speak\n"
            f"  • 🔮 The orb shows my state and floats on your desktop\n"
            f"  • ✖ Closing this window keeps me running in the tray\n"
            f"  • ⚙ Right-click the orb for settings\n\n"
            f"Try: 'Open Notepad and write hello world'\n"
            f"Try: 'Create a snake game in Python'\n"
            f"Try: 'Search latest AI news'\n\n"
            f"{key_info}"
        )
        self._add_bubble("JARVIS", msg)
        self._set_state("idle")

        if self.speaker and has_key:
            threading.Thread(
                target=self.speaker.speak,
                args=(f"{greeting}, {user}. All systems are online. How can I help?",),
                daemon=True,
            ).start()

    # ── Settings dialog ───────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            settings_path = _BASE / "config/settings.json"
            settings_path.write_text(
                json.dumps(self.settings, indent=2), encoding="utf-8"
            )
            self.status_bar.showMessage("Settings saved.")


# ══════════════════════════════════════════════════════════════════════════════
#  Settings Dialog (unchanged from v1, kept clean)
# ══════════════════════════════════════════════════════════════════════════════

class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("⚙ JARVIS OMEGA Settings")
        self.resize(480, 440)
        self.setStyleSheet(
            f"QDialog {{ background:{C['bg2']}; }} "
            f"QLabel {{ color:{C['text']}; }} "
            f"QLineEdit {{ background:{C['bg3']}; color:{C['text']}; "
            f"border:1px solid {C['border2']}; border-radius:6px; padding:6px; }} "
            f"QPushButton {{ background:{C['blue2']}; color:{C['text']}; "
            "border:none; border-radius:6px; padding:8px 16px; }"
        )
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        fields = [
            ("groq_api_key",   "Groq API Key (FREE at console.groq.com):"),
            ("user_name",      "Your Name:"),
            ("ai_name",        "AI Name:"),
            ("wake_word",      "Wake Word:"),
            ("groq_model",     "AI Model:"),
            ("tts_voice",      "TTS Voice (edge-tts):"),
            ("whisper_model",  "Whisper Model (tiny/base/small):"),
        ]
        self._fields = {}
        for i, (key, label) in enumerate(fields):
            grid.addWidget(QLabel(label), i, 0)
            field = QLineEdit(str(settings.get(key, "")))
            if "key" in key.lower():
                field.setEchoMode(QLineEdit.EchoMode.Password)
            self._fields[key] = field
            grid.addWidget(field, i, 1)

        layout.addLayout(grid)
        layout.addSpacing(8)

        notes = [
            "💡 Groq key: console.groq.com (free, no credit card)",
            "🎙 TTS Voice examples: en-US-GuyNeural, en-IN-NeerjaNeural",
            "🧠 Whisper: tiny (fast) / base (balanced) / small (accurate)",
        ]
        for note in notes:
            lbl = QLabel(note)
            lbl.setStyleSheet(f"color:{C['cyan_dim']}; font-size:10px;")
            layout.addWidget(lbl)

        layout.addStretch()
        btn_layout = QHBoxLayout()
        save_btn   = QPushButton("💾 Save")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        for key, field in self._fields.items():
            self.settings[key] = field.text().strip()
        self.accept()
