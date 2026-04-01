import sys
import requests
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QSizePolicy, QGridLayout, QPushButton,
    QTableWidget, QHeaderView, QProgressBar, QTableWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QBrush, QPixmap, QImage
)
from PySide6.QtCharts import QChart, QChartView, QPieSeries

# Import your classes
from gbf_party import Party, Character, Quest, RaidInfo

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
            f"./db/{self.char_id}.png",
            f"./db/char_{self.char_id}.png",
            f"./db/summon_{self.char_id}.png",
            f"./db/raid_{self.char_id}.jpg",
            self.char_id 
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
        self.setFixedSize(100, 100) 
        self.setStyleSheet(f"background: {BG_DARK}; border: 1px solid {BORDER};")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_id = None
        self.original_image = None
        self.downloader = None
        
        # CRITICAL FIX: Initialize this so resizeEvent doesn't crash
        self.original_pixmap = None

    def _on_ready(self, image, char_id):
        self.original_image = image
        self.update_scaled_pixmap()

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
        if not char_id or char_id == self.current_id:
            return
        if self.downloader and self.downloader.isRunning():
            return 

        self.current_id = char_id
        self.downloader = ImageAssigner(char_id)
        self.downloader.finished.connect(self._on_ready)
        self.downloader.start()

    def set_initial_pixmap(self, pixmap, char_id):
        self.original_pixmap = pixmap
        self.update_scaled_pixmap()

    def resizeEvent(self, event):
        # Triggered whenever the window/row is resized
        super().resizeEvent(event)
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if self.original_image and not self.original_image.isNull():
            scaled = self.original_image.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, # Better for portraits
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(QPixmap.fromImage(scaled))

class DpsTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "RANK", "NAME", "AUTO", "OUGI", "SKILL", "TOTAL"
        ])
        
        # Set a tighter row height since there are no icons
        self.verticalHeader().setDefaultSectionSize(35) 
        self.verticalHeader().setVisible(False)
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Rank
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Name
        
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_DARK};
                alternate-background-color: {BG_ROW_ODD}; /* Fixes the white rows */
                color: {TEXT_MAIN};
                gridline-color: {BORDER};
                border: 1px solid {BORDER};
                selection-background-color: {ACCENT_GOLD};
            }}
            QTableWidget::item {{
                background-color: {BG_ROW_EVEN};
                color: {TEXT_MAIN};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {BG_PANEL};
                color: {ACCENT_GOLD};
                font-weight: bold;
                border: 1px solid {BORDER};
            }}
        """)

    def update_table(self, sorted_members, total_raid_dmg):
        self.setRowCount(len(sorted_members))
        for i, char in enumerate(sorted_members):
            total = char.get_total_dmg()
            breakdown = char.get_breakdown()
            
            # Rank & Name (Text only)
            self.setItem(i, 0, QTableWidgetItem(str(i+1)))
            name_item = QTableWidgetItem(char.get_name())
            name_item.setForeground(QBrush(QColor(ACCENT_GOLD)))
            self.setItem(i, 1, name_item)
            
            # Damage columns
            self.setItem(i, 2, QTableWidgetItem(f"{breakdown.get('Autos', 0):,}"))
            self.setItem(i, 3, QTableWidgetItem(f"{breakdown.get('Ougi', 0):,}"))
            self.setItem(i, 4, QTableWidgetItem(f"{breakdown.get('Skills', 0):,}"))
            self.setItem(i, 5, QTableWidgetItem(f"{total:,}"))
            
class QPartyIcons(QWidget):
    def __init__(self):
        super().__init__()
        # Width: (60px * 3) + 20px for padding/spacing
        self.setFixedWidth(300) 
        self.setFixedHeight(200) 
        
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(5, 5, 5, 5)
        self.grid.setSpacing(5)
        
        self.slots = [CharacterIcon() for _ in range(6)]
        for i, slot in enumerate(self.slots):
            slot.setFixedSize(100, 100) # Ensure icons stay square
            self.grid.addWidget(slot, i // 3, i % 3)

    def update_party_icons(self, members):
        for i, char in enumerate(members):
            if i < len(self.slots):
                # Using img_id as confirmed by your previous logs
                self.slots[i].load_id(char.img_id)

class QSummons(QWidget):
    def __init__(self):
        super().__init__()
        # 180px height works well for two rows of icons
        self.setFixedHeight(180) 
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(5, 5, 5, 5)
        self.grid.setSpacing(5)
        self.setFixedHeight(260) 
        self.setFixedWidth(600)

        # Create 6 slots
        self.slots = [CharacterIcon() for _ in range(6)]
        for slot in self.slots:
            slot.setFixedSize(220, 120)

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
            
        for summon in summons_list:
            if 0 <= summon.get_pos() < len(self.slots):
                self.slots[summon.get_pos()].load_id(summon.img)

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

    def update_raid_info(self, raid : RaidInfo):
        self.lbl_name.setText(raid.get_name())
        formatted_hp = f"{raid.get_hp():,}".replace(",", ".")
        self.lbl_hp.setText(f"HP: {formatted_hp} ({raid.get_hp() / raid.get_max_hp():.0%})")

class DamagePieChart(QChartView):
    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.Antialiasing)
        self.chart = QChart()
        self.chart.setBackgroundVisible(False) # Keep it clean for Dark Mode
        self.chart.setTitleBrush(Qt.white)
        self.setChart(self.chart)
        self.series = QPieSeries()
        self.setFixedSize(450, 350)
        
    def update_chart(self, character):
        self.chart.removeAllSeries()
        self.series = QPieSeries()
        
        data = character.get_breakdown()
        
        # Don't show chart if no damage dealt yet
        if character.total_dmg == 0:
            self.chart.setTitle(f"No Data for {character.name}")
            return

        self.chart.setTitle(f"{character.name}'s Damage Breakdown")
        
        # Add slices
        for label, val in data.items():
            if val > 0:
                self.series.append(label, val)
        
        # Style the labels
        for slice in self.series.slices():
            percentage = 100 * slice.percentage()
            slice.setLabel(f"{slice.label()}: {percentage:.0f}%")
            slice.setLabelVisible(True)
            slice.setLabelColor(Qt.white)

        self.chart.addSeries(self.series)

class QRaidMembers(QWidget):
    def __init__(self):
        super().__init__()

    def update_summons(self):
        pass

class GBFDpsMeter(QMainWindow):
    def __init__(self, unused_path=None): # unused_path keeps signature for main.py
        super().__init__()
        self.setWindowTitle("Granblue Fantasy tool")
        self.resize(1000, 800)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        central = QWidget()
        self.setCentralWidget(central)
        self.main_lay = QVBoxLayout(central)

        header = self.build_header()

        self.add_raid(header)
        header.addStretch()
        self.add_dmg_pie(header)


        middle = self.build_middle()
        self.add_dps_table(middle)

        bottom = self.build_bottom()
        
        self.add_summons(bottom)
        bottom.addStretch()
        self.party_portraits = QPartyIcons()
        bottom.addWidget(self.party_portraits)
        
        self.add_raid_members(self.main_lay)

        self.main_lay.addStretch()


    # methods
    def build_header(self):
        header_container = QWidget()
        header_lay = QHBoxLayout(header_container)
        header_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.addWidget(header_container)
        return header_lay

    def build_middle(self):
        middle_container = QWidget()
        middle_lay = QHBoxLayout(middle_container)
        middle_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.addWidget(middle_container)
        return middle_lay

    def build_bottom(self):
        footer_widget = QWidget()
        footer_lay = QHBoxLayout(footer_widget)
        self.main_lay.addWidget(footer_widget)
        return footer_lay

    def add_dps_table(self, container):
        self.dps_table = DpsTable()
        container.addWidget(self.dps_table)

    def add_raid(self, container):
        self.raid_info = QRaidInfo()
        container.addWidget(self.raid_info)

    def add_dmg_pie(self, container):
        self.damage_pie = DamagePieChart()
        container.addWidget(self.damage_pie)

    def add_summons(self, container):
        self.summons = QSummons()
        container.addWidget(self.summons)

    def add_raid_members(self, container):
        self.raid_members = QRaidMembers()
        container.addWidget(self.raid_members)


    @Slot(object)
    def update_ui_live(self, quest: Quest):
        try:
            members = quest.get_party().get_members_list()
            if not members: return
            
            # Update the new portrait grid
            self.party_portraits.update_party_icons(members)
            
            # Update the table (now text-only)
            total_raid_dmg = sum(m.get_total_dmg() for m in members)
            sorted_members = sorted(members, key=lambda x: x.get_total_dmg() or 0, reverse=True)
            self.dps_table.update_table(sorted_members, total_raid_dmg)
            
            # Standard updates
            self.raid_info.update_raid_info(quest.get_raid())

            self.summons.update_summons(quest.get_party().get_summon_list())
            if sorted_members:
                self.damage_pie.update_chart(sorted_members[0])
                
        except Exception as e:
            print(f"UI Update Error: {e}")

