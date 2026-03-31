import sys
import requests
from gbf_asset_requestor import get_wiki_image_by_id as wiki_id
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QBrush, QPixmap, QImage
)

# Import your classes
from gbf_party import Party, Character

# ── Color Palette ──────────────────────────────────────────────────────────
BG_DARK      = "#0d0f14"
BG_PANEL     = "#13161f"
BG_ROW_ODD   = "#191c28"
BG_ROW_EVEN  = "#141720"
ACCENT_GOLD  = "#c9a84c"
TEXT_MAIN    = "#e8ecf4"
BORDER       = "#252a38"
BAR_FILL     = "#4a90d9"

# ── Image Threading (Improved Quality) ─────────────────────────────────────
class ImageDownloader(QThread):
    finished = Signal(QPixmap, str)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    def run(self):
        wiki_url = wiki_id(self.char_id)
        if not wiki_url: return
        try:
            r = requests.get(wiki_url, headers={'User-Agent': 'GBF_Meter/1.0'}, timeout=5)
            if r.status_code == 200:
                img = QImage()
                img.loadFromData(r.content)
                self.finished.emit(QPixmap.fromImage(img), self.char_id)
        except: pass

class CharacterIcon(QLabel):
    def __init__(self):
        super().__init__()
        # 1. Set a wide box to match your 280x158 images
        self.setFixedSize(120, 68) 
        self.setStyleSheet(f"background: {BG_DARK}; border: 1px solid {BORDER};")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # CRITICAL FIX: Initialize this so resizeEvent doesn't crash
        self.original_pixmap = None

    def set_pixmap(self, pixmap):
        # 2. SIMPLE LOGIC: Resize to fit the box, but DO NOT stretch
        scaled = pixmap.scaled(
            self.width(), 
            self.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)

    def load_id(self, char_id):
        self.downloader = ImageDownloader(char_id)
        # Ensure we use the two-argument signature from your Signal
        self.downloader.finished.connect(self.set_initial_pixmap)
        self.downloader.start()

    def set_initial_pixmap(self, pixmap, char_id):
        self.original_pixmap = pixmap
        self.update_scaled_pixmap()

    def resizeEvent(self, event):
        # Triggered whenever the window/row is resized
        super().resizeEvent(event)
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if self.original_pixmap and not self.original_pixmap.isNull():
            # Use SmoothTransformation to maintain resolution
            scaled = self.original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)

class DamageBar(QWidget):
    def __init__(self, fraction=0.0):
        super().__init__()
        self.fraction = fraction
        self.setFixedHeight(12)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor("#1a1d26")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        
        fw = int(self.width() * self.fraction)
        if fw > 5:
            grad = QLinearGradient(0, 0, fw, 0)
            grad.setColorAt(0, QColor(BAR_FILL).darker(110))
            grad.setColorAt(1, QColor(BAR_FILL).lighter(120))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, fw, self.height(), 4, 4)

class DpsRow(QWidget):
    def __init__(self, rank):
        super().__init__()
        self.rank = rank
        # Increased row height to accommodate wider vertical strips
        self.setFixedHeight(160) 
        self.char_id = None
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 20, 10) # More breathing room
        
        self.icon = CharacterIcon()
        
        v_info = QVBoxLayout()
        v_info.setSpacing(5)
        
        self.lbl_name = QLabel("—")
        self.lbl_name.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: bold; font-size: 18px; letter-spacing: 1px;")
        
        self.bar = DamageBar(0.0)
        self.lbl_total = QLabel("0 TOTAL")
        self.lbl_total.setStyleSheet(f"color: {ACCENT_GOLD}; font-weight: bold; font-size: 14px;")
        
        v_info.addWidget(self.lbl_name)
        v_info.addWidget(self.bar)
        v_info.addWidget(self.lbl_total)
        
        # Add the wider icon
        lay.addWidget(self.icon)
        lay.addLayout(v_info, 1)

    def update_from_char(self, char: Character, max_dmg, rank):
        self.lbl_name.setText(char.get_name().upper())
        total = char.get_total_dmg()
        self.lbl_total.setText(f"{total:,} DMG")
        self.bar.fraction = total / max_dmg if max_dmg > 0 else 0
        self.bar.update()
        
        if char.img_id != self.char_id:
            self.char_id = char.img_id
            self.icon.load_id(char.img_id)
            
        bg = BG_ROW_ODD if rank % 2 else BG_ROW_EVEN
        self.setStyleSheet(f"background: {bg}; border-radius: 4px; margin: 2px;")

class GBFDpsMeter(QMainWindow):
    def __init__(self, unused_path=None): # unused_path keeps signature for main.py
        super().__init__()
        self.setWindowTitle("CYPHER // LIVE MONITOR")
        self.resize(500, 700)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        central = QWidget()
        self.setCentralWidget(central)
        self.main_lay = QVBoxLayout(central)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.table_lay = QVBoxLayout(self.scroll_content)
        
        # Start with 6 empty rows for a full party
        self.rows = [DpsRow(i+1) for i in range(6)]
        for r in self.rows:
            self.table_lay.addWidget(r)
        self.table_lay.addStretch()
        self.scroll.setWidget(self.scroll_content)
        self.main_lay.addWidget(self.scroll)

    @Slot(object)
    def update_ui_live(self, party: Party):
        """ Receives the Party object directly from the thread """
        members = party.get_members_list()
        if not members: return

        # Sorting logic stays in UI to keep display ranked by DMG
        sorted_members = sorted(members, key=lambda x: x.get_total_dmg(), reverse=True)
        max_dmg = max(m.get_total_dmg() for m in members) if members else 1
        
        for i, member in enumerate(sorted_members):
            if i < len(self.rows):
                self.rows[i].update_from_char(member, max_dmg, i+1)
