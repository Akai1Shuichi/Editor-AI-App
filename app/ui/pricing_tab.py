from pathlib import Path
from typing import Any, Optional

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
PRODUCTS_URL = "https://api.botocit.com/api/v2/telegram-buyer/products"


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
    result_ready = pyqtSignal(bool, object, str)

    def __init__(self, url: Optional[str] = None):
        super().__init__()
        self.url = url or PRODUCTS_URL

    def run(self):
        try:
            res = requests.get(
                self.url, headers={"Accept": "application/json"}, timeout=10
            )
            res.raise_for_status()
            data = res.json()
            self.result_ready.emit(True, data, "")
        except Exception as e:
            self.result_ready.emit(False, {}, str(e))


class PricingTab(QWidget):
    """Trang giá mua Voice API qua Telegram bot."""

    def __init__(self, parent=None, api_url: Optional[str] = None):
        super().__init__(parent)
        self.setObjectName("pricing_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.pricing_url = api_url or PRODUCTS_URL
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

        self.offers_container = QWidget()
        self.offers_layout = QVBoxLayout(self.offers_container)
        self.offers_layout.setContentsMargins(0, 0, 0, 0)
        self.offers_layout.setSpacing(8)
        layout.addWidget(self.offers_container)

        self.lbl_status = QLabel("Đang tải bảng giá...")
        self.lbl_status.setObjectName("page_subtitle")
        layout.addWidget(self.lbl_status)

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
        if not self.offers_layout.count():
            self.lbl_status.setText("Đang tải bảng giá...")
            self.lbl_status.show()
        self.worker = PricingFetchThread(self.pricing_url)
        self.worker.result_ready.connect(self._on_pricing_loaded)
        self.worker.start()

    def _on_pricing_loaded(self, success: bool, data: Any, error_msg: str):
        if success:
            self.update_pricing_data(data)
        else:
            self.lbl_status.setText("Không tải được bảng giá. Vui lòng thử lại sau.")
            self.lbl_status.show()

    def update_pricing_data(self, data: Any):
        """Render từng gói giá từ mảng API, đồng thời hỗ trợ payload JSON cũ."""
        offers = self._extract_offers(data)
        self._clear_offers()

        for offer in offers:
            self.offers_layout.addWidget(self._create_offer_widget(offer))
        self.lbl_status.setText("" if offers else "Chưa có sản phẩm trong bảng giá.")
        self.lbl_status.setVisible(not offers)

    @staticmethod
    def _extract_offers(data: Any) -> list[dict]:
        if isinstance(data, list):
            return [offer for offer in data if isinstance(offer, dict)]
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return [offer for offer in items if isinstance(offer, dict)]
            return [data]
        return []

    def _clear_offers(self):
        while self.offers_layout.count():
            item = self.offers_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_offer_widget(self, offer: dict) -> QFrame:
        panel = QFrame()
        panel.setObjectName("pricing_offer")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        label = QLabel(str(offer.get("label", "")).strip())
        label.setObjectName("offer_label")
        layout.addWidget(label)

        sale = self._sale_percent(offer.get("sale", 0))
        if sale > 0:
            sale_label = QLabel(f"Sale {sale:g}%")
            sale_label.setObjectName("offer_sale")
            layout.addWidget(sale_label)

        layout.addStretch()

        if sale > 0 and offer.get("old_price") is not None:
            old_price = QLabel(format_vnd_price(offer["old_price"]))
            old_price.setObjectName("offer_old_price")
            layout.addWidget(old_price)

        if offer.get("price") is not None:
            price = QLabel(format_vnd_price(offer["price"]))
            price.setObjectName("offer_price")
            layout.addWidget(price)

        return panel

    @staticmethod
    def _sale_percent(value: Any) -> float:
        try:
            return max(0, float(str(value).replace("%", "").strip()))
        except (TypeError, ValueError):
            return 0
