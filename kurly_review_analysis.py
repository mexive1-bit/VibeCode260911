"""컬리 상품 리뷰 10건 수집, 감성 분석 및 시각화."""

from __future__ import annotations

import re
import time
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PRODUCT_URL = "https://www.kurly.com/goods/1002063927?collectionCode=26chu-269010"
TARGET_REVIEWS = 10
MAX_CLICK_ATTEMPTS = 80
OUTPUT_DIR = Path(__file__).with_name("kurly_review_analysis_output")

AD_PATTERNS = (
    r"광고|협찬|체험단|제공받|원고료|구매대행|공동구매|서포터즈|앰배서더|홍보",
    r"할인코드|쿠폰코드|추천인|오픈채팅|카카오톡|인스타그램|instagram|youtube",
    r"링크를? 통해|프로모션|sponsored|affiliate|gifted",
)
POSITIVE_WORDS = (
    "좋아요", "좋다", "만족", "추천", "재구매", "효과", "편해", "편리", "맛있",
    "건강", "상쾌", "든든", "빠르", "깔끔", "저렴", "감사", "잘 먹", "기대",
    "최고", "굿", "만족스럽", "도움",
)
NEGATIVE_WORDS = (
    "별로", "아쉽", "실망", "불만", "비싸", "비쌈", "맛없", "쓰다", "시다",
    "역하", "불편", "느리", "늦", "파손", "누락", "상했", "효과 없", "모르겠",
    "부작용", "구려", "싫",
)
DATE_PATTERN = re.compile(r"20\d{2}[./-]\s?\d{1,2}[./-]\s?\d{1,2}")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def make_driver() -> webdriver.Chrome:
    options = Options()
    options.page_load_strategy = "none"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,3000")
    options.add_argument("--lang=ko-KR")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)


def clean_text(value: str) -> str:
    return " ".join(value.split())


def load_reviews() -> list[dict[str, str]]:
    try:
        response = requests.get(
            PRODUCT_URL,
            headers=HEADERS,
            timeout=(10, 20),
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        direct_reviews = extract_reviews(response.text)
        if len(direct_reviews) >= TARGET_REVIEWS:
            return direct_reviews
        print(f"HTTP 방식으로 {len(direct_reviews)}건을 확인했습니다. 브라우저 수집을 시작합니다...")
    except requests.RequestException as error:
        print(f"HTTP 수집을 건너뜁니다: {error}")

    print("Chrome 브라우저를 시작하는 중입니다...")
    driver = make_driver()
    collected: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        driver.set_page_load_timeout(10)
        try:
            print("상품 페이지를 불러오는 중입니다...")
            driver.get(PRODUCT_URL)
        except WebDriverException as error:
            raise RuntimeError("컬리 페이지 로딩 시간이 초과되었습니다.") from error
        load_started = time.monotonic()
        while time.monotonic() - load_started < 12:
            try:
                page_state = driver.execute_script("return document.readyState;")
                body_length = driver.execute_script(
                    "return document.body ? document.body.innerText.length : 0;"
                )
                if page_state in {"interactive", "complete"} and body_length > 500:
                    break
            except WebDriverException:
                break
            time.sleep(0.5)
        driver.execute_script("window.stop();")
        time.sleep(2)
        started_at = time.monotonic()

        for _ in range(MAX_CLICK_ATTEMPTS):
            for review in extract_reviews(driver.page_source):
                if review["리뷰"] not in seen:
                    seen.add(review["리뷰"])
                    collected.append(review)
            if len(collected) >= TARGET_REVIEWS:
                return collected

            buttons = driver.find_elements(By.XPATH, "//button | //a")
            next_buttons = [
                button
                for button in buttons
                if clean_text(button.text) == "다음"
                and button.is_displayed()
                and button.is_enabled()
            ]
            if next_buttons:
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        next_buttons[-1],
                    )
                    driver.execute_script(
                        "arguments[0].click();", next_buttons[-1]
                    )
                    time.sleep(0.9)
                except WebDriverException:
                    break
            else:
                more_buttons = [
                    button
                    for button in buttons
                    if clean_text(button.text) in {"더보기", "+더보기"}
                    and button.is_displayed()
                    and button.is_enabled()
                ]
                if more_buttons:
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            more_buttons[-1],
                        )
                        driver.execute_script(
                            "arguments[0].click();", more_buttons[-1]
                        )
                        time.sleep(0.7)
                    except WebDriverException:
                        pass
                else:
                    driver.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    time.sleep(0.7)

            if time.monotonic() - started_at >= 90:
                break
        print(f"브라우저 수집 결과: {len(collected)}건")
        return collected
    finally:
        driver.quit()


def extract_reviews(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    reviews: list[dict[str, str]] = []
    seen: set[str] = set()

    for date_node in soup.find_all(string=DATE_PATTERN):
        date_match = DATE_PATTERN.search(date_node)
        if date_match is None:
            continue
        container = date_node.parent
        for _ in range(8):
            if container is None:
                break
            text = clean_text(container.get_text(" ", strip=True))
            if 30 <= len(text) <= 3000 and "도움돼요" in text:
                content = extract_content(text, date_match.group())
                key = re.sub(r"\s+", " ", content)
                if len(content) >= 5 and key not in seen:
                    seen.add(key)
                    reviews.append(
                        {
                            "작성일": date_match.group().replace(".", "-"),
                            "리뷰": content,
                        }
                    )
                break
            container = container.parent
    return reviews


def extract_content(container_text: str, date: str) -> str:
    text = container_text.replace(date, " ")
    text = re.sub(r"VIP|VVIP|멤버스|프렌즈|라이트|퍼플|골드|다이아", " ", text)
    text = re.sub(r"\d+\s*대/?[가-힣]*", " ", text)
    text = re.sub(r"도움돼요\s*\d*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_advertisement(review: str) -> bool:
    return any(re.search(pattern, review, flags=re.IGNORECASE) for pattern in AD_PATTERNS)


def classify_sentiment(review: str) -> tuple[str, int, int]:
    positive_score = sum(review.count(word) for word in POSITIVE_WORDS)
    negative_score = sum(review.count(word) for word in NEGATIVE_WORDS)
    if positive_score > negative_score:
        label = "긍정"
    elif negative_score > positive_score:
        label = "부정"
    else:
        label = "중립"
    return label, positive_score, negative_score


def analyze_reviews(reviews: list[dict[str, str]]) -> pd.DataFrame:
    data = pd.DataFrame(reviews).drop_duplicates(subset=["리뷰"]).copy()
    if data.empty:
        raise ValueError("리뷰를 찾지 못했습니다. 컬리 페이지의 접근 상태를 확인하세요.")
    data["광고성"] = data["리뷰"].map(is_advertisement)
    if len(data) < TARGET_REVIEWS:
        raise ValueError(
            f"중복 제거 후 리뷰가 {len(data)}건만 수집되었습니다. "
            f"필요 건수: {TARGET_REVIEWS}건"
        )
    data = data.head(TARGET_REVIEWS).reset_index(drop=True)
    scores = data["리뷰"].map(classify_sentiment)
    data[["감성", "긍정점수", "부정점수"]] = pd.DataFrame(
        scores.tolist(), index=data.index
    )
    data.insert(0, "번호", range(1, len(data) + 1))
    return data


def plot_results(data: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    counts = data["감성"].value_counts().reindex(["긍정", "중립", "부정"], fill_value=0)
    colors = ["#2a9d8f", "#9aa0a6", "#e76f51"]

    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    figure.suptitle("컬리 상품 리뷰 10건 감성 분석", fontsize=16, fontweight="bold")

    axes[0].bar(counts.index, counts.values, color=colors, width=0.62)
    axes[0].set_title("의견별 리뷰 수")
    axes[0].set_ylabel("리뷰 수")
    axes[0].grid(axis="y", alpha=0.25)
    for index, value in enumerate(counts.values):
        axes[0].text(index, value + 1, str(value), ha="center", fontweight="bold")

    axes[1].pie(
        counts.values,
        labels=counts.index,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    axes[1].set_title("의견 비율")
    figure.tight_layout()
    output_path = OUTPUT_DIR / "kurly_review_sentiment.png"
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


class ReviewWorker(QObject):
    completed = pyqtSignal(object, str)
    status_changed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.status_changed.emit("컬리 리뷰 페이지를 여는 중입니다...")
            reviews = load_reviews()
            self.status_changed.emit(
                f"리뷰 {len(reviews)}건을 수집했습니다. 감성을 분석하는 중입니다..."
            )
            data = analyze_reviews(reviews)
            OUTPUT_DIR.mkdir(exist_ok=True)
            csv_path = OUTPUT_DIR / "kurly_reviews_sentiment.csv"
            data.to_csv(csv_path, index=False, encoding="utf-8-sig")
            self.completed.emit(data, str(csv_path.resolve()))
        except Exception as error:
            self.failed.emit(str(error))


class ReviewAnalysisWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.thread: QThread | None = None
        self.worker: ReviewWorker | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setWindowTitle("컬리 리뷰 감성 분석")
        self.resize(1500, 850)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title = QLabel("컬리 리뷰 감성 분석")
        title.setObjectName("title")
        self.start_button = QPushButton("리뷰 10건 수집 및 분석")
        self.start_button.clicked.connect(self.start_analysis)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.start_button)
        root_layout.addLayout(header_layout)

        self.status_label = QLabel("버튼을 눌러 리뷰 수집을 시작하세요.")
        self.status_label.setObjectName("status")
        root_layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.review_table = QTableWidget(0, 5)
        self.review_table.setHorizontalHeaderLabels(
            ["번호", "작성일", "감성", "광고성", "리뷰 내용"]
        )
        self.review_table.setAlternatingRowColors(True)
        self.review_table.setWordWrap(True)
        self.review_table.setColumnWidth(0, 58)
        self.review_table.setColumnWidth(1, 100)
        self.review_table.setColumnWidth(2, 75)
        self.review_table.setColumnWidth(3, 75)
        self.review_table.horizontalHeader().setStretchLastSection(True)
        self.review_table.verticalHeader().setDefaultSectionSize(58)

        chart_panel = QWidget()
        chart_layout = QVBoxLayout(chart_panel)
        self.summary_label = QLabel("분석 결과가 여기에 표시됩니다.")
        self.summary_label.setObjectName("summary")
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(7, 5)))
        chart_layout.addWidget(self.summary_label)
        chart_layout.addWidget(self.canvas)

        splitter.addWidget(self.review_table)
        splitter.addWidget(chart_panel)
        splitter.setSizes([760, 700])
        root_layout.addWidget(splitter)

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
                font-size: 20pt;
                font-weight: 700;
            }
            QLabel#status, QLabel#summary {
                color: #52606d;
                padding: 4px;
            }
            QPushButton {
                background-color: #1f5f8b;
                border: 1px solid #1f5f8b;
                border-radius: 4px;
                color: white;
                font-weight: 700;
                padding: 9px 16px;
            }
            QPushButton:hover { background-color: #17496d; }
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
                padding: 8px;
                border: 0;
            }
            """
        )

    def start_analysis(self) -> None:
        if self.thread is not None:
            return
        self.start_button.setEnabled(False)
        self.review_table.setRowCount(0)
        self.summary_label.setText("분석 준비 중입니다.")
        self.status_label.setText("리뷰를 수집하는 중입니다...")

        self.thread = QThread()
        self.worker = ReviewWorker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.completed.connect(self.show_results)
        self.worker.failed.connect(self.show_error)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.analysis_finished)
        self.thread.start()

    def show_results(self, data: pd.DataFrame, csv_path: str) -> None:
        self.review_table.setRowCount(len(data))
        for row, (_, review) in enumerate(data.iterrows()):
            values = [
                str(review["번호"]),
                str(review["작성일"]),
                str(review["감성"]),
                "예" if review["광고성"] else "아니오",
                str(review["리뷰"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.review_table.setItem(row, column, item)

        counts = data["감성"].value_counts().reindex(
            ["긍정", "중립", "부정"], fill_value=0
        )
        self.summary_label.setText(
            " | ".join(f"{label}: {count}건" for label, count in counts.items())
            + f"\nCSV 저장: {csv_path}"
        )
        self.draw_chart(counts)

    def draw_chart(self, counts: pd.Series) -> None:
        figure = self.canvas.figure
        figure.clear()
        axes = figure.subplots(1, 2)
        colors = ["#2a9d8f", "#9aa0a6", "#e76f51"]
        axes[0].bar(counts.index, counts.values, color=colors, width=0.62)
        axes[0].set_title("의견별 리뷰 수")
        axes[0].set_ylabel("리뷰 수")
        axes[0].grid(axis="y", alpha=0.25)
        for index, value in enumerate(counts.values):
            axes[0].text(index, value + 1, str(value), ha="center")
        axes[1].pie(
            counts.values,
            labels=counts.index,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
        )
        axes[1].set_title("의견 비율")
        figure.tight_layout()
        OUTPUT_DIR.mkdir(exist_ok=True)
        figure.savefig(OUTPUT_DIR / "kurly_review_sentiment.png", dpi=160)
        self.canvas.draw()

    def show_error(self, message: str) -> None:
        self.status_label.setText("분석에 실패했습니다.")
        QMessageBox.critical(self, "리뷰 분석 오류", message)

    def analysis_finished(self) -> None:
        self.start_button.setEnabled(True)
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None


if __name__ == "__main__":
    app = QApplication([])
    window = ReviewAnalysisWindow()
    window.show()
    raise SystemExit(app.exec())
