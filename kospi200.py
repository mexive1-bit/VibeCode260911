"""네이버 금융에서 코스피200 편입종목 상위 정보를 수집합니다."""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


INDEX_URL = "https://finance.naver.com/sise/sise_index.naver?code=KPI200"
ENTRY_URL = "https://finance.naver.com/sise/entryJongmok.naver"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}


@dataclass
class Constituent:
    rank: int
    name: str
    code: str
    current_price: str
    change: str
    change_rate: str
    volume: str
    trading_value_million: str
    market_cap_million: str


def get_index_code(index_url):
    """지수 URL의 code 파라미터를 가져옵니다."""
    query = parse_qs(urlparse(index_url).query)
    try:
        return query["code"][0]
    except (KeyError, IndexError) as error:
        raise ValueError("URL에 지수 code 파라미터가 없습니다.") from error


def clean_text(element):
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def extract_stock_code(row):
    link = row.select_one('a[href*="item/main.naver"]')
    if link is None:
        return ""
    match = re.search(r"code=(\d+)", link.get("href", ""))
    return match.group(1) if match else ""


def parse_constituents(table, start_rank):
    constituents = []
    for row in table.select("tr"):
        cells = row.select("th, td")
        stock_code = extract_stock_code(row)
        if len(cells) != 7 or not stock_code or cells[0].name != "td":
            continue

        values = [clean_text(cell) for cell in cells]
        constituents.append(
            Constituent(
                rank=start_rank + len(constituents),
                name=values[0],
                code=stock_code,
                current_price=values[1],
                change=values[2],
                change_rate=values[3],
                volume=values[4],
                trading_value_million=values[5],
                market_cap_million=values[6],
            )
        )

    return constituents


def crawl_kospi200(index_url=INDEX_URL, max_stocks=200):
    """코스피200 편입종목 상위 표의 전체 페이지를 반환합니다."""
    index_code = get_index_code(index_url)
    constituents = []
    page = 1

    while len(constituents) < max_stocks:
        response = requests.get(
            ENTRY_URL,
            params={"code": index_code, "page": page},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.select_one("table.type_1")
        if table is None:
            raise RuntimeError(f"{page}페이지의 편입종목 표를 찾지 못했습니다.")

        page_constituents = parse_constituents(table, len(constituents) + 1)
        if not page_constituents:
            break

        constituents.extend(page_constituents)
        page += 1

    return constituents[:max_stocks]


def save_to_excel(stocks, file_path="kospi200.xlsx"):
    """크롤링 결과를 엑셀 파일로 저장합니다."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "코스피200 편입종목"

    headers = [
        "순위",
        "종목명",
        "종목코드",
        "현재가",
        "전일비",
        "등락률",
        "거래량",
        "거래대금(백만)",
        "시가총액(억)",
    ]
    worksheet.append(headers)

    for stock in stocks:
        worksheet.append(
            [
                stock.rank,
                stock.name,
                stock.code,
                stock.current_price,
                stock.change,
                stock.change_rate,
                stock.volume,
                stock.trading_value_million,
                stock.market_cap_million,
            ]
        )

    header_fill = PatternFill("solid", fgColor="1F5F8B")
    for cell in worksheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    column_widths = [8, 20, 12, 14, 14, 12, 16, 18, 18]
    for index, width in enumerate(column_widths, start=1):
        worksheet.column_dimensions[chr(64 + index)].width = width

    output_path = Path(file_path).resolve()
    workbook.save(output_path)
    return output_path


class CrawlWorker(QObject):
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.completed.emit(crawl_kospi200())
        except Exception as error:
            self.failed.emit(str(error))


class Kospi200Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.stocks = []
        self.setup_ui()
        self.start_crawling()

    def setup_ui(self):
        self.setWindowTitle("코스피200 편입종목 상위")
        self.resize(1350, 720)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(10)

        title = QLabel("코스피200 편입종목 상위 200개")
        title.setObjectName("title")
        main_layout.addWidget(title)

        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.start_crawling)
        button_layout.addWidget(self.refresh_button)
        self.excel_button = QPushButton("엑셀 저장")
        self.excel_button.setEnabled(False)
        self.excel_button.clicked.connect(self.save_excel)
        button_layout.addWidget(self.excel_button)
        self.status_label = QLabel("데이터를 불러오는 중입니다...")
        button_layout.addWidget(self.status_label)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.result_table = QTableWidget(0, 9)
        self.result_table.setHorizontalHeaderLabels(
            [
                "순위",
                "종목명",
                "종목코드",
                "현재가",
                "전일비",
                "등락률",
                "거래량",
                "거래대금(백만)",
                "시가총액(억)",
            ]
        )
        self.result_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.result_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.result_table)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #f4f6f8;
                color: #263238;
                font-family: 'Malgun Gothic';
                font-size: 10pt;
            }
            QLabel#title {
                color: #17365d;
                font-size: 19pt;
                font-weight: 700;
            }
            QPushButton {
                background-color: #1f5f8b;
                border: 1px solid #1f5f8b;
                border-radius: 4px;
                color: white;
                font-weight: 700;
                padding: 7px 16px;
            }
            QPushButton:disabled {
                background-color: #9aa7b2;
                border-color: #9aa7b2;
            }
            QTableWidget {
                background-color: white;
                alternate-background-color: #f7f9fb;
                border: 1px solid #d4dce3;
                gridline-color: #e1e7ec;
            }
            QHeaderView::section {
                background-color: #e7edf3;
                color: #34495e;
                font-weight: 700;
                padding: 7px;
                border: 0;
            }
            """
        )

    def start_crawling(self):
        if self.thread is not None:
            return

        self.refresh_button.setEnabled(False)
        self.excel_button.setEnabled(False)
        self.status_label.setText("200개 종목을 수집하는 중입니다...")
        self.result_table.setRowCount(0)

        self.thread = QThread()
        self.worker = CrawlWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.crawling_finished)
        self.thread.start()

    def show_results(self, stocks):
        self.stocks = stocks
        self.result_table.setRowCount(len(stocks))
        for row, stock in enumerate(stocks):
            values = [
                stock.rank,
                stock.name,
                stock.code,
                stock.current_price,
                stock.change,
                stock.change_rate,
                stock.volume,
                stock.trading_value_million,
                stock.market_cap_million,
            ]
            for column, value in enumerate(values):
                self.result_table.setItem(
                    row, column, QTableWidgetItem(str(value))
                )

        self.result_table.resizeColumnsToContents()
        self.excel_button.setEnabled(bool(stocks))
        self.status_label.setText(f"총 {len(stocks):,}개 종목 수집 완료")

    def save_excel(self):
        if not self.stocks:
            return

        try:
            output_path = save_to_excel(self.stocks)
            self.status_label.setText(f"엑셀 저장 완료: {output_path}")
        except Exception as error:
            QMessageBox.critical(self, "엑셀 저장 오류", str(error))

    def show_error(self, message):
        self.status_label.setText("크롤링에 실패했습니다.")
        QMessageBox.critical(self, "크롤링 오류", message)

    def crawling_finished(self):
        self.refresh_button.setEnabled(True)
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.worker = None
        self.thread = None


def main():
    app = QApplication([])
    window = Kospi200Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"프로그램 실행 실패: {error}")