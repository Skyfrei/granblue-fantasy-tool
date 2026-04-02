from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QStyledItemDelegate, QSizePolicy
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFont
import time
from gbf_party import Quest

def load_stylesheet(file_path):
    with open(file_path, "r") as f:
        return f.read()
 
class BarDelegate(QStyledItemDelegate):
    def paint(self, painter, opt, idx):
        try:
            ratio = float(idx.data(Qt.DisplayRole) or 0)
        except:
            ratio = 0.0
 
        name = str(idx.data(Qt.UserRole) or "")
 
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
 
        r = opt.rect.adjusted(10, 6, -10, -6)
 
        NAME_W = 80
        PCT_W  = 38
        GAP    = 8
        bar_w  = max(0, r.width() - NAME_W - PCT_W - GAP * 2)
 
        name_r = QRect(r.left(), r.top(), NAME_W, r.height())
        bar_r  = QRect(r.left() + NAME_W + GAP, r.top() + r.height() // 2 - 3, bar_w, 6)
        pct_r  = QRect(r.right() - PCT_W, r.top(), PCT_W, r.height())
 
        # Name
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(name_r, Qt.AlignLeft | Qt.AlignVCenter, name)
 
        # Bar track
        painter.fillRect(bar_r, QColor(42, 42, 61))
 
        # Bar fill
        if bar_w > 0:
            fill_r = QRect(bar_r.left(), bar_r.top(), int(bar_w * min(ratio, 1.0)), bar_r.height())
            painter.fillRect(fill_r, QColor("#378ADD"))
 
        # Percentage
        painter.setPen(QColor("#8888aa"))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(pct_r, Qt.AlignRight | Qt.AlignVCenter, f"{ratio * 100:.1f}%")
 
        painter.restore()

class MetricCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet(load_stylesheet("style.qss"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet(load_stylesheet("style.qss"))
        
        self.val_lbl = QLabel("0")
        self.val_lbl.setStyleSheet(load_stylesheet("style.qss"))
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)

    def set_value(self, text):
        self.val_lbl.setText(text)

class QDmgPerTurn(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(450)
        self.setMaximumWidth(650)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(15)

        # 1. Metric Cards Row
        self.build_metric_cards()       

        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setObjectName("dividerLine")
        self.line.setStyleSheet(load_stylesheet("style.qss"))
        self.main_layout.addWidget(self.line)

        # 3. The Original Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Damage share", "Current turn", "Previous turn"])
        self.table.setStyleSheet(load_stylesheet("style.qss"))
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        
        self.bar = BarDelegate()
        self.table.setItemDelegateForColumn(0, self.bar)
        self.main_layout.addWidget(self.table)

    def build_metric_cards(self):
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)
        self.card_time = MetricCard("Time")
        self.card_dpm  = MetricCard("DPM")
        self.card_dpt  = MetricCard("DPT")
        self.card_tpm  = MetricCard("TPM")
        self.cards_layout.addWidget(self.card_time)
        self.cards_layout.addWidget(self.card_dpm)
        self.cards_layout.addWidget(self.card_dpt)
        self.cards_layout.addWidget(self.card_tpm)
        self.main_layout.addLayout(self.cards_layout)
 
    
    def update_card(self, card: MetricCard, value: int):
        card.set_value(value)

    def update_turn_table(self, quest: Quest):
        members = quest.get_party().get_members_list()
        self.table.setRowCount(len(members))
        turn = quest.get_turn()
        max_dmg = 1
        member_stats = []
        total_turn_dmg = 1
        all_total_dmg = 0

        for member in members:
            dmg_list = member.get_dmg_list(turn)
            curr_dmg = sum(member.get_dmg_list(turn))
            prev_dmg = sum(member.get_dmg_list(turn - 1))
            total_turn_dmg += curr_dmg
            all_total_dmg += member.get_total_dmg()

            if curr_dmg > max_dmg:
                max_dmg = curr_dmg

            member_stats.append({
                'name': member.get_name(),
                'curr': curr_dmg,
                'prev': prev_dmg
            })

        self.bar.max_val = max_dmg
        self.update_card(self.card_dpt, f"{all_total_dmg / turn:,.0f}")
        self.update_card(self.card_tpm, f"{turn / quest.get_minutes_passed():,.2f}")
        self.update_card(self.card_dpm, f"{all_total_dmg / quest.get_minutes_passed():,.2f}")
        mins, secs = divmod(int(quest.get_elapsed_time()), 60)
        self.update_card(self.card_time, f"{mins:02d}:{secs:02d}")


        for i, stats in enumerate(member_stats):
            curr_dmg = stats['curr']
            prev_dmg = stats['prev']
            ratio_this_turn = curr_dmg / total_turn_dmg
            item_main = QTableWidgetItem(str(ratio_this_turn))
            item_main.setData(Qt.UserRole, stats['name'])
            self.table.setItem(i, 0, item_main)
            self.table.setItem(i, 1, QTableWidgetItem(f"{curr_dmg:,}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{prev_dmg:,}"))

        self.table.viewport().update()

