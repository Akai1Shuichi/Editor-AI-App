from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class PricingTab(QWidget):
    """Trang giá mua Voice API qua Telegram bot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pricing_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        self.lbl_pricing_title = QLabel("Bảng giá")
        self.lbl_pricing_title.setObjectName("page_heading")
        layout.addWidget(self.lbl_pricing_title)

        offer_panel = QFrame()
        offer_panel.setObjectName("bot_offer")
        offer_layout = QHBoxLayout(offer_panel)
        offer_layout.setContentsMargins(16, 14, 16, 14)
        offer_layout.setSpacing(12)

        self.lbl_bot_offer_name = QLabel("ElevenLabs Redeem 131K Credit · Sale 30%")
        self.lbl_bot_offer_name.setObjectName("bot_offer_name")

        self.lbl_bot_offer_original_price = QLabel("92.000đ")
        self.lbl_bot_offer_original_price.setObjectName("bot_offer_original_price")
        self.lbl_bot_offer_sale_price = QLabel("65.000đ")
        self.lbl_bot_offer_sale_price.setObjectName("bot_offer_sale_price")

        offer_layout.addWidget(self.lbl_bot_offer_name)
        offer_layout.addStretch()
        offer_layout.addWidget(self.lbl_bot_offer_original_price)
        offer_layout.addWidget(self.lbl_bot_offer_sale_price)
        layout.addWidget(offer_panel)

        purchase_row = QHBoxLayout()
        purchase_row.setContentsMargins(2, 0, 0, 0)
        purchase_row.setSpacing(7)
        self.lbl_bot_purchase_prefix = QLabel("Mua tại")
        purchase_row.addWidget(self.lbl_bot_purchase_prefix)
        self.lbl_bot_purchase_telegram_icon = QLabel()
        self.lbl_bot_purchase_telegram_icon.setPixmap(
            QPixmap(str(ICONS_DIR / "telegram.svg")).scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.lbl_bot_purchase_link = QLabel(
            '<a href="https://t.me/DichVuIT_bot">@DichVuIT_bot</a>'
        )
        self.lbl_bot_purchase_link.setOpenExternalLinks(True)
        self.lbl_bot_purchase_link.setObjectName("bot_purchase_link")
        purchase_row.addWidget(self.lbl_bot_purchase_telegram_icon)
        purchase_row.addWidget(self.lbl_bot_purchase_link)
        purchase_row.addStretch()
        layout.addLayout(purchase_row)
        layout.addStretch()
