from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor

from gbf_party import Party, Character, Quest, RaidInfo

class QDmgGraph(QChartView):
    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.Antialiasing)
        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.setTitle("Comparison: Total Damage (Millions)")
        self.chart.setTitleBrush(QColor("#c9a84c"))
        self.setChart(self.chart)

        # Setup Axes
        self.axis_x = QValueAxis()
        self.axis_x.setLabelsColor(Qt.white)
        self.axis_x.setTitleText("Turn")
        self.axis_y = QValueAxis()
        self.axis_y.setLabelsColor(Qt.white)
        self.axis_y.setTitleText("Total Dmg (M)")

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)

    def update_data(self, matching_quests: dict):
        self.chart.removeAllSeries()
        if not matching_quests:
            return

        max_dmg_m = 0
        max_turn = 0
        colors = ["#c9a84c", "#4db6ac", "#9575cd", "#e57373", "#64b5f6"]

        for i, (q_id, quest) in enumerate(matching_quests.items()):
            series = QLineSeries()
            party_names = ", ".join(c.get_name() for c in quest.get_party().get_members_list())
            series.setName(f"{party_names}")
            
            pen = QPen(QColor(colors[i % len(colors)]))
            pen.setWidth(2)
            series.setPen(pen)

            cumulative_dmg = 0
            # Calculate cumulative damage turn-by-turn using character dicts
            for t in range(1, quest.get_turn() + 1):
                turn_total = 0
                for char in quest.get_party().get_members_list():
                    # sum() the list of damage hits stored for this turn
                    turn_total += sum(char.get_dmg_list(t))
                
                cumulative_dmg += turn_total
                dmg_m = cumulative_dmg / 1_000_000
                series.append(t, dmg_m)

                if dmg_m > max_dmg_m: max_dmg_m = dmg_m
                if t > max_turn: max_turn = t

            self.chart.addSeries(series)
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)

        # Update viewport
        self.axis_x.setRange(1, max_turn + 1)
        self.axis_y.setRange(0, max_dmg_m * 1.1)
