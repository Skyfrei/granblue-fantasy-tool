import sys
import requests
import os
from gbf_asset_requestor import get_wiki_image_by_id as wiki_id
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
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "RANK", "CHARACTER", "AUTO", "OUGI", "SKILL", "TOTAL", "CONTRIB %"
        ])
        
        # Styling
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        
        # Header Behavior
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Rank
        header.setSectionResizeMode(1, QHeaderView.Fixed)            # Character
        self.setColumnWidth(1, 180) 
        self.verticalHeader().setDefaultSectionSize(66)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameStyle(QFrame.NoFrame)
        self.setMinimumHeight(470)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_DARK};
                color: {TEXT_MAIN};
                gridline-color: {BORDER};
                border: 1px solid {BORDER};
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 5px;
                background-color: {BG_ROW_EVEN};
            }}
            QTableWidget::item:alternate {{
                background-color: {BG_ROW_ODD};
            }}
            QHeaderView::section {{
                background-color: {BG_PANEL};
                color: {ACCENT_GOLD};
                font-weight: bold;
                padding: 4px;
                border: 1px solid {BORDER};
            }}
        """)

    def update_table(self, sorted_members, max_dmg):
        self.setRowCount(len(sorted_members))
        
        for i, char in enumerate(sorted_members):
            total = char.get_total_dmg()
            breakdown = char.get_breakdown()
            
            # 0. Rank
            self.setItem(i, 0, QTableWidgetItem(str(i+1)))
            
            # 1. Character (Icon + Name)
            # We reuse your CharacterIcon but smaller
            char_widget = QWidget()
            char_lay = QHBoxLayout(char_widget)
            char_lay.setContentsMargins(2, 2, 2, 2)
            
            mini_icon = CharacterIcon()
            mini_icon.setFixedSize(105,56) 
            mini_icon.load_id(char.get_id())
            
            name_lbl = QLabel(char.get_name())
            name_lbl.setStyleSheet(f"font-weight: bold; color: {ACCENT_GOLD};")
            
            char_lay.addWidget(mini_icon)
            char_lay.addWidget(name_lbl)
            self.setCellWidget(i, 1, char_widget)
            
            # 2-5. Damage Columns
            self.setItem(i, 2, QTableWidgetItem(f"{breakdown['Autos']:,}"))
            self.setItem(i, 3, QTableWidgetItem(f"{breakdown['Ougi']:,}"))
            self.setItem(i, 4, QTableWidgetItem(f"{breakdown['Skills']:,}"))
            self.setItem(i, 5, QTableWidgetItem(f"{total:,}"))
            
            # 6. Contribution Bar
            bar = QProgressBar()
            bar.setFixedSize(100, 20)
            bar.setMaximum(max_dmg)
            bar.setValue(total)
            bar.setTextVisible(True)
            bar.setFormat(f"{(total/max_dmg * 100) if max_dmg > 0 else 0:.1f}%")
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {BORDER};
                    border-radius: 2px;
                    background: {BG_DARK};
                    text-align: center;
                    color: white;
                    height: 10px;
                }}
                QProgressBar::chunk {{
                    background-color: {BAR_FILL};
                }}
            """)
            self.setCellWidget(i, 6, bar)

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

class GBFDpsMeter(QMainWindow):
    def __init__(self, unused_path=None): # unused_path keeps signature for main.py
        super().__init__()
        self.setWindowTitle("Granblue Fantasy tool")
        self.resize(1000, 800)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        central = QWidget()
        self.setCentralWidget(central)
        self.main_lay = QVBoxLayout(central)

        self.header_container = QWidget()
        self.header_lay = QHBoxLayout(self.header_container)
        self.header_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.addWidget(self.header_container)

        self.add_raid_info(self.header_lay)
        self.header_lay.addStretch()
        self.add_dmg_pie(self.header_lay)

        self.middle_container = QWidget()
        self.middle_lay = QHBoxLayout(self.middle_container)
        self.middle_lay.setContentsMargins(0, 0, 0, 0)
        self.main_lay.addWidget(self.middle_container)
        self.add_dps_table(self.middle_lay)


        self.summons_container = QWidget()
        self.summons_lay = QHBoxLayout(self.summons_container)
        self.add_summons(self.summons_lay)
        self.summons_lay.addStretch()
        self.main_lay.addWidget(self.summons_container)
        self.main_lay.addStretch()


    def add_dps_table(self, container):
        self.dps_table = DpsTable()
        container.addWidget(self.dps_table)


    def add_raid_info(self, container):
        self.raid_info = QRaidInfo()
        container.addWidget(self.raid_info)

    def add_dmg_pie(self, container):
        self.damage_pie = DamagePieChart()
        container.addWidget(self.damage_pie)

    def add_summons(self, container):
        self.summons = QSummons()
        container.addWidget(self.summons)

    @Slot(object)
    def update_ui_live(self, quest: Quest):
        try:
            members = quest.get_party().get_members_list()
            if not members: return
            
            summons = quest.get_party().get_summon_list()
            if summons:
                self.summons.update_summons(summons)

            raidinfo = quest.get_raid()
            if raidinfo:
                self.raid_info.update_raid_info(raidinfo)

            sorted_members = sorted(members, key=lambda x: x.get_total_dmg() or 0, reverse=True)
           
            total_raid_dmg = sum(m.total_dmg for m in members)
            self.dps_table.update_table(sorted_members, total_raid_dmg)
            
            if sorted_members:
                self.damage_pie.update_chart(sorted_members[0])
            #pie
            if sorted_members:
                top_char = sorted_members[0]
                self.damage_pie.update_chart(top_char)
                    
        except Exception as e:
            print(f"!!! HIDDEN UI ERROR: {e}")
            import traceback
            traceback.print_exc()

