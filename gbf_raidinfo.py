from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLabel, QWidget, QPushButton, QProgressBar)
from PySide6.QtCore import Qt

from gbf_party import RaidInfo
import re
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_stylesheet(file_path):
    path = resource_path(file_path)
    with open(path, "r") as f:
        return f.read()

class RaidDetailsDialog(QDialog):
    def __init__(self, boss_name, mechanics_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Mechanics: {boss_name}")
        self.resize(600, 400)
        
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
        attacks = data.get(2, {})  # colspan=2 = attack names + effects
        notes = data.get(3, {})    # colspan=3 = triggers/notes

        # Build rows: each attack key is one row
        attack_items = list(attacks.items())
        self.table.setRowCount(len(attack_items))

        for i, (name, effects) in enumerate(attack_items):
            # --- Left column: attack name (bold) + effects (smaller) ---
            cell_widget = QWidget()
            cell_layout = QVBoxLayout(cell_widget)
            cell_layout.setContentsMargins(6, 6, 6, 6)
            cell_layout.setSpacing(3)

            name_label = QLabel(name)
            name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffcc00;")
            name_label.setWordWrap(True)
            cell_layout.addWidget(name_label)

            for effect in effects:
                effect_label = QLabel(f"• {effect}")
                effect_label.setStyleSheet("font-size: 11px; color: #cccccc;")
                effect_label.setWordWrap(True)
                cell_layout.addWidget(effect_label)

            cell_layout.addStretch()
            self.table.setCellWidget(i, 0, cell_widget)

            # --- Right column: matching note from colspan=3 by index ---
            note_items = list(notes.items())
            if i < len(note_items):
                note_name, note_effects = note_items[i]

                note_widget = QWidget()
                note_layout = QVBoxLayout(note_widget)
                note_layout.setContentsMargins(6, 6, 6, 6)
                note_layout.setSpacing(3)

                note_name_label = QLabel(note_name)
                note_name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #88aaff;")
                note_name_label.setWordWrap(True)
                note_layout.addWidget(note_name_label)

                for note_effect in note_effects:
                    ne_label = QLabel(f"• {note_effect}")
                    ne_label.setStyleSheet("font-size: 11px; color: #cccccc;")
                    ne_label.setWordWrap(True)
                    note_layout.addWidget(ne_label)

                note_layout.addStretch()
                self.table.setCellWidget(i, 1, note_widget)

        self.table.resizeRowsToContents()

class QRaidInfo(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(220) 
        self.raid = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        self.lbl_name = QLabel("Lvl 200 Akasha")
        self.lbl_name.setStyleSheet(load_stylesheet("style.qss"))
        self.lbl_name.setWordWrap(True)

        self.hp_bar = QProgressBar()
        self.hp_bar.setRange(0, 100)
        self.hp_bar.setValue(100)
        self.hp_bar.setTextVisible(False)
        self.hp_bar.setFixedHeight(7)
        self.hp_bar.setStyleSheet(load_stylesheet("style.qss"))

        self.lbl_hp = QLabel("HP: 100,000,000")
        self.lbl_hp.setStyleSheet(load_stylesheet("style.qss"))
        self.lbl_hp.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_dmg_done = QLabel("Hit for: 0%")
        self.lbl_dmg_done.setStyleSheet(load_stylesheet("style.qss"))

        self.btn_action = QPushButton("Raid Details")
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(load_stylesheet("style.qss"))
        self.btn_action.clicked.connect(self.show_raid_details)

        self.log_btn = QPushButton("Combat log")
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.setStyleSheet(load_stylesheet("style.qss"))

        # Add everything to the widget's internal vertical layout
        self.layout.addWidget(self.lbl_name)
        self.layout.addWidget(self.hp_bar)
        self.layout.addWidget(self.lbl_hp)
        self.layout.addWidget(self.lbl_dmg_done)
        self.layout.addWidget(self.btn_action)
        self.layout.addWidget(self.log_btn)
        
        # Add a stretch at the bottom to keep everything at the top
        self.layout.addStretch()

    def show_raid_details(self):
        self.btn_action.setEnabled(False)
        wiki_data = dict()
        try:
            wiki_data = self.raid.get_effect_table()
        except:
            print("No data for this raid")
        if wiki_data:
            details_window = RaidDetailsDialog(self.raid.get_name(), wiki_data, self)
            details_window.exec() # Use exec() to make it a modal "on top"
        self.btn_action.setEnabled(True)

    def update_raid_info(self, raid : RaidInfo, dmg_done: int):
        if self.raid is None:
            self.raid = raid

        max_hp = raid.get_max_hp()
        current_hp = raid.get_hp()
        percent_val = (current_hp / max_hp * 100) if max_hp > 0 else 0
        self.hp_bar.setValue(int(percent_val))

        self.lbl_name.setText(raid.get_name())
        formatted_hp = f"{raid.get_hp():,}"
        honor_val = dmg_done // 100
        formatted_honor = f"{honor_val:,}"
        percent = (current_hp / max_hp) if max_hp > 0 else 0
        

        self.lbl_dmg_done.setText(f"Done: {(dmg_done / max_hp):.2%}")
        self.lbl_hp.setText(
            f"HP: {formatted_hp} ({percent:.0%})\n"
            f"Honour: {formatted_honor}"
        )
