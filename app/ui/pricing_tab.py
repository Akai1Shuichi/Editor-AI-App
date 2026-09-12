import time
from pathlib import Path
from typing import Any, Optional

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
ELEVENLABS_PRICING_API_URL = "https://gist.github.com/Akai1Shuichi/9cae5e226f6e3a624e24fa3fb207321e/raw/price.json"


def format_vnd_price(value: Any) -> str:
    """Định dạng số tiền sang chuẩn hiển thị VNĐ (ví dụ 65000 -> 65.000đ)."""
    if value is None:
        return ""
    try:
        val_int = int(value)
        return f"{val_int:,}đ".replace(",", ".")
    except (ValueError, TypeError):
        s = str(value).strip()
        if not s:
            return ""
        return s if s.endswith("đ") else f"{s}đ"


class PricingFetchThread(QThread):
    """Thread tải bảng giá động từ API."""
    result_ready = pyqtSignal(bool, dict, str)

    def __init__(self, url: str = ELEVENLABS_PRICING_API_URL):
        super().__init__()
        self.url = url

    def run(self):
        try:
            params = {"t": int(time.time())}
            res = requests.get(self.url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            self.result_ready.emit(True, data, "")
        except Exception as e:
            self.result_ready.emit(False, {}, str(e))


class PricingTab(QWidget):
    """Trang giá mua Voice API qua Telegram bot."""

    def __init__(self, parent=None, api_url: str = ELEVENLABS_PRICING_API_URL):
        super().__init__(parent)
        self.setObjectName("pricing_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.pricing_url = api_url
        self.worker: Optional[PricingFetchThread] = None
        self.init_ui()
        self.refresh_pricing()

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

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_pricing()

    def refresh_pricing(self):
        if self.worker and self.worker.isRunning():
            return
        self.worker = PricingFetchThread(self.pricing_url)
        self.worker.result_ready.connect(self._on_pricing_loaded)
        self.worker.start()

    def _on_pricing_loaded(self, success: bool, data: dict, error_msg: str):
        if success and data:
            self.update_pricing_data(data)

    def update_pricing_data(self, data: dict):
        """Cập nhật giao diện khi có dữ liệu giá từ API."""
        sale = str(data.get("sale", "")).strip()
        price = data.get("price")
        old_price = data.get("old_price")

        if sale:
            self.lbl_bot_offer_name.setText(f"ElevenLabs Redeem 131K Credit · Sale {sale}")
        else:
            self.lbl_bot_offer_name.setText("ElevenLabs Redeem 131K Credit")

        if old_price is not None:
            self.lbl_bot_offer_original_price.setText(format_vnd_price(old_price))
            self.lbl_bot_offer_original_price.setVisible(True)
        else:
            self.lbl_bot_offer_original_price.setVisible(False)

        if price is not None:
            self.lbl_bot_offer_sale_price.setText(format_vnd_price(price))
            self.lbl_bot_offer_sale_price.setVisible(True)
        else:
            self.lbl_bot_offer_sale_price.setVisible(False)
