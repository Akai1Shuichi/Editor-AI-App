from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QCheckBox


class ToggleSwitch(QCheckBox):
    """Công tắc gạt hiện đại (Toggle Switch) kế thừa QCheckBox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        checked = self.isChecked()
        track_color = QColor("#2563eb" if checked else "#374151")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(1, 2, 36, 18), 9, 9)

        knob_x = 28 if checked else 10
        painter.setBrush(QColor("#ffffff" if checked else "#f1f5f9"))
        painter.drawEllipse(QPointF(knob_x, 11), 7, 7)
