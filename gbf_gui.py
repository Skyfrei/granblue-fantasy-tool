import sys
import requests
import os
from gbf_asset_requestor import get_wiki_image_by_id as wiki_id
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy, QGridLayout, QPushButton
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
class ImageAssigner(QThread):
    finished = Signal(QImage, str)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    def run(self):
        paths_to_check = [
            f"./db/{self.char_id}.jpg",
            f"./db/{self.char_id}.png",
        ]
        
        image = QImage()
        for path in paths_to_check:
            if os.path.exists(path):
                image.load(path)
                break
        if not image.isNull():
            self.finished.emit(image, self.char_id)
        else:
            print(f"DEBUG: Asset {self.char_id} not found in ./db/")

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
        self.downloader = ImageAssigner(char_id)
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
            # 1. Scale the QImage (still a QImage here)
            scaled_img = self.original_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # 2. CONVERT to QPixmap specifically for the QLabel 
            final_pixmap = QPixmap.fromImage(scaled_img)
            
            # 3. Set it (this won't crash now)
            self.setPixmap(final_pixmap)
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

class QSummons(QWidget):
    def __init__(self):
        super().__init__()
        # 180px height works well for two rows of icons
        self.setFixedHeight(180) 
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(5, 5, 5, 5)
        self.grid.setSpacing(5)

        # Create 6 slots
        self.slots = [CharacterIcon() for _ in range(6)]

        # Row 0
        self.grid.addWidget(self.slots[0], 0, 0) # Main
        self.grid.addWidget(self.slots[1], 0, 1) # Sub 1
        self.grid.addWidget(self.slots[2], 0, 2) # Sub 2

        # Row 1
        self.grid.addWidget(self.slots[3], 1, 0) # Sub 3
        self.grid.addWidget(self.slots[4], 1, 1) # Sub 4
        self.grid.addWidget(self.slots[5], 1, 2) # Support/Friend

    def update_summons(self, summons_list):
        """ Pushes summon IDs into the slots from the parser """
        if not summons_list:
            return
            
        for i, summon in enumerate(summons_list):
            if i < len(self.slots):
                # Use the img_id from your Summon objects
                self.slots[i].load_id(summon.img_id)

class QRaidInfo(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(220) 
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        # 1. Raid Banner Image
        self.lbl_image = QLabel()
        self.lbl_image.setFixedSize(200, 70)
        self.lbl_image.setStyleSheet(f"background: #1a1d26; border: 1px solid {BORDER};")
        self.lbl_image.setScaledContents(True)
        # Placeholder text if no image is loaded
        self.lbl_image.setText("RAID BANNER")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Level and Name
        self.lbl_name = QLabel("Lvl 200 Akasha")
        self.lbl_name.setStyleSheet(f"color: {TEXT_MAIN}; font-weight: bold; font-size: 14px;")
        self.lbl_name.setWordWrap(True)

        # 3. HP Display
        self.lbl_hp = QLabel("HP: 100.0%")
        self.lbl_hp.setStyleSheet(f"color: {ACCENT_GOLD}; font-family: monospace; font-size: 13px;")

        # 4. Action Button
        self.btn_action = QPushButton("RAID DETAILS")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT_GOLD};
                color: #0d0f14;
                border: none;
                font-weight: bold;
                padding: 8px;
                border-radius: 2px;
            }}
            QPushButton:hover {{ background-color: #ffffff; }}
        """)

        # Add everything to the widget's internal vertical layout
        self.layout.addWidget(self.lbl_image)
        self.layout.addWidget(self.lbl_name)
        self.layout.addWidget(self.lbl_hp)
        self.layout.addWidget(self.btn_action)
        
        # Add a stretch at the bottom to keep everything at the top
        self.layout.addStretch()

class GBFDpsMeter(QMainWindow):
    def __init__(self, unused_path=None): # unused_path keeps signature for main.py
        super().__init__()
        self.setWindowTitle("Granblue Fantasy tool")
        self.resize(500, 700)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        central = QWidget()
        self.setCentralWidget(central)
        self.main_lay = QVBoxLayout(central)
        self.raid_info = QRaidInfo()
        self.main_lay.addWidget(self.raid_info)

        self.party_row_lay = QHBoxLayout()

        
        self.portrait_slots = [CharacterIcon() for _ in range(4)]
        for p in self.portrait_slots:
            p.setFixedSize(120, 180) # Adjust to your preference
            self.party_row_lay.addWidget(p)

        self.summons = QSummons()
        self.party_row_lay.addWidget(self.summons)

        self.main_lay.addLayout(self.party_row_lay)

        # ROW 3: Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.table_lay = QVBoxLayout(self.scroll_content)
        
        self.rows = [DpsRow(i+1) for i in range(6)]
        for r in self.rows:
            self.table_lay.addWidget(r)
        
        self.table_lay.addStretch()
        self.scroll.setWidget(self.scroll_content)
        
        # Stretch=1 makes the scroll area expand to fill the bottom
        self.main_lay.addWidget(self.scroll, 1)
        

    

    @Slot(object)
    def update_ui_live(self, party: Party):
        try:
            members = party.get_members_list()
            if not members: return
            
            summons = party.get_summon_list()
            if summons:
                self.summons.update_summons(summons)

            sorted_members = sorted(members, key=lambda x: x.get_total_dmg() or 0, reverse=True)
            
            max_val = max(m.get_total_dmg() for m in members)
            max_dmg = max_val if max_val > 0 else 1
            
            for i, member in enumerate(sorted_members):
                if i < len(self.rows):
                    self.rows[i].update_from_char(member, max_dmg, i+1)
                    
        except Exception as e:
            print(f"!!! HIDDEN UI ERROR: {e}")
            import traceback
            traceback.print_exc()
