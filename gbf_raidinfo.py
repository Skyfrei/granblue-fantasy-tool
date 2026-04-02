from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLabel, QWidget, QPushButton)
from PySide6.QtCore import Qt

from gbf_party import RaidInfo
import re

def load_stylesheet(file_path):
    with open(file_path, "r") as f:
        return f.read()

class RaidDetailsDialog(QDialog):
    def __init__(self, boss_name, mechanics_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mechanics: {boss_name}")
        self.resize(600, 400)
        
        # Make it stay on top and look like a clean window
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        # Title Label
        title = QLabel(f"Special Attacks & Triggers for {boss_name}")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(title)

        # Setup Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Trigger / Name", "Effect / Description"])
        
        # Style the table to look like a Wiki
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("alternate-background-color: #2a2a2a; background-color: #1e1e1e; color: white;")
        
        self.populate_table(mechanics_list)
        layout.addWidget(self.table)

    def populate_table(self, data):
        rows = []
        
        for block in data:
            # 1. CRITICAL CLEANUP: Replace non-breaking spaces with normal spaces
            # This makes the regex actually find the start of lines.
            block = block.replace('\xa0', ' ')
            
            # 2. Extract Attack Definitions (The "Dictionary")
            # We look for: Name + Space + (N, OD, or TR) + Description
            attack_definitions = {}
            
            # This regex is now more flexible with spacing and weird characters
            defs = re.findall(r'^([A-Z][\w\s\-\']+)\s+(?:N|OD|TR|Marked).*?\n\s*(.*?)(?=\n|[A-Z][a-z]|\Z)', block, re.MULTILINE)
            
            for name, effect in defs:
                clean_name = name.strip()
                # Remove the wiki tooltip junk (anything after the first ". |")
                clean_effect = effect.split(". |")[0].split(".  ")[0].strip()
                attack_definitions[clean_name] = clean_effect

            # 3. Find HP Triggers
            # The wiki often puts the trigger % on one line and the action on the next
            found_triggers = re.findall(r'(\d+%\s+Trigger)\s*\n\s*(.*?)(?=\n|$)', block)
            
            if found_triggers:
                for trig, action in found_triggers:
                    display_effect = action.strip()
                    
                    # 4. LINKING: Match the action (e.g. "Casts Taurus Blight") to our Dictionary
                    for atk_name, atk_effect in attack_definitions.items():
                        if atk_name.lower() in action.lower():
                            display_effect = f"<b>{action}</b><br>↳ {atk_effect}"
                            break
                    
                    rows.append((trig, display_effect))
            
            # 5. Fallback: If no HP triggers found, show the general attacks found in the block
            elif attack_definitions:
                for name, effect in attack_definitions.items():
                    rows.append((name, effect))

        # --- UI UPDATE ---
        self.table.setRowCount(len(rows))
        for i, (name, desc) in enumerate(rows):
            # We use a QLabel for the description to support the <b> and <br> tags
            name_label = QLabel(name)
            name_label.setStyleSheet("padding: 5px; color: #ffcc00; font-weight: bold;")
            
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("padding: 5px; color: white;")
            
            self.table.setCellWidget(i, 0, name_label)
            self.table.setCellWidget(i, 1, desc_label)
            
        self.table.resizeRowsToContents()

class QRaidInfo(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(220) 
        self.raid = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        # 1. Raid Banner Image
        self.lbl_image = QLabel()
        self.lbl_image.setFixedSize(200, 70)
        self.lbl_image.setStyleSheet(load_stylesheet("style.qss"))
        self.lbl_image.setScaledContents(True)
        # Placeholder text if no image is loaded
        self.lbl_image.setText("RAID BANNER")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 2. Level and Name
        self.lbl_name = QLabel("Lvl 200 Akasha")
        self.lbl_name.setStyleSheet(load_stylesheet("style.qss"))
        self.lbl_name.setWordWrap(True)

        # 3. HP Display
        self.lbl_hp = QLabel("HP: 100.0%")
        self.lbl_hp.setStyleSheet(load_stylesheet("style.qss"))

        # 4. Action Button
        self.btn_action = QPushButton("Raid Details")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(load_stylesheet("style.qss"))
        self.btn_action.clicked.connect(self.show_raid_details)

        self.log_btn = QPushButton("Combat log")
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.setStyleSheet(load_stylesheet("style.qss"))

        # Add everything to the widget's internal vertical layout
        self.layout.addWidget(self.lbl_image)
        self.layout.addWidget(self.lbl_name)
        self.layout.addWidget(self.lbl_hp)
        self.layout.addWidget(self.btn_action)
        self.layout.addWidget(self.log_btn)

        
        # Add a stretch at the bottom to keep everything at the top
        self.layout.addStretch()

    def show_raid_details(self):
        self.btn_action.setEnabled(False)
        wiki_data = self.raid.get_effect_table()
        if wiki_data:
            details_window = RaidDetailsDialog(self.raid.get_name(), wiki_data, self)
            details_window.exec() # Use exec() to make it a modal "on top"
        else:
            print("No data found.")

    def update_raid_info(self, raid : RaidInfo, dmg_done: int):
        if self.raid is None:
            self.raid = raid
        self.lbl_name.setText(raid.get_name())
        formatted_hp = f"{raid.get_hp():,}".replace(",", ".")
        honor_val = dmg_done // 100
        formatted_honor = f"{honor_val:,}".replace(",", ".")
        max_hp = raid.get_max_hp()
        percent = (raid.get_hp() / max_hp) if max_hp > 0 else 0

        self.lbl_hp.setText(
            f"HP: {formatted_hp} ({percent:.0%})\n"
            f"Honour: {formatted_honor}"
        )


