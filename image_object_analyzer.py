import base64
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

load_dotenv()


class ImageAnalysisWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = Path(image_path)

    def analyze(self):
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY 환경 변수가 설정되지 않았습니다."
                )

            mime_type, _ = mimetypes.guess_type(self.image_path.name)
            if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
                raise ValueError("JPG, PNG, WEBP, GIF 이미지 파일만 지원합니다.")

            image_data = base64.b64encode(self.image_path.read_bytes()).decode("utf-8")
            image_url = f"data:{mime_type};base64,{image_data}"

            client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "사진을 한국어로 분석해 주세요. "
                                    "사진에 보이는 주요 사물을 빠짐없이 설명하고, "
                                    "각 사물의 위치와 용도를 추정해 주세요. "
                                    "확실하지 않은 내용은 추정이라고 표시하세요."
                                ),
                            },
                            {"type": "input_image", "image_url": image_url},
                        ],
                    }
                ],
            )
            result = response.output_text.strip()
            if not result:
                raise RuntimeError("API가 분석 결과를 반환하지 않았습니다.")
            self.finished.emit(result)
        except Exception as error:
            self.failed.emit(str(error))


class ImageAnalyzerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_image_path = None
        self.analysis_thread = None
        self.analysis_worker = None
        self.setWindowTitle("AI 사진 사물 분석")
        self.resize(900, 700)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(12)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #f4f7fb;
                color: #243447;
                font-family: 'Malgun Gothic';
                font-size: 10pt;
            }
            QLabel#title {
                color: #123b5d;
                font-size: 20pt;
                font-weight: 700;
            }
            QLabel#preview {
                background-color: #ffffff;
                border: 1px dashed #9fb3c8;
                border-radius: 6px;
                color: #718096;
                min-height: 320px;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #9fb3c8;
                border-radius: 4px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #e8f1f8;
                border-color: #2878b5;
            }
            QPushButton#analyzeButton {
                background-color: #176b87;
                border-color: #176b87;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#analyzeButton:disabled {
                background-color: #a8bac5;
                border-color: #a8bac5;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #c5d1dc;
                border-radius: 4px;
                padding: 8px;
            }
            """
        )

        title = QLabel("AI 사진 사물 분석")
        title.setObjectName("title")
        main_layout.addWidget(title)

        description = QLabel(
            "사진을 선택하면 OpenAI API가 이미지 속 주요 사물과 위치를 분석합니다."
        )
        main_layout.addWidget(description)

        button_layout = QHBoxLayout()
        self.select_button = QPushButton("사진 선택")
        self.select_button.clicked.connect(self.select_image)
        self.analyze_button = QPushButton("사물 분석 시작")
        self.analyze_button.setObjectName("analyzeButton")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.analyze_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.preview_label = QLabel("선택한 사진이 여기에 표시됩니다.")
        self.preview_label.setObjectName("preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.preview_label, 2)

        self.status_label = QLabel("분석 대기 중")
        main_layout.addWidget(self.status_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("분석 결과가 여기에 표시됩니다.")
        main_layout.addWidget(self.result_text, 1)

    def select_image(self):
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "분석할 사진 선택",
            "",
            "이미지 파일 (*.jpg *.jpeg *.png *.webp *.gif)",
        )
        if not image_path:
            return

        self.selected_image_path = image_path
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "파일 오류", "이미지를 불러올 수 없습니다.")
            self.selected_image_path = None
            return

        self.preview_label.setPixmap(
            pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.status_label.setText(f"선택됨: {Path(image_path).name}")
        self.result_text.clear()
        self.analyze_button.setEnabled(True)

    def start_analysis(self):
        if not self.selected_image_path:
            return

        self.select_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.result_text.setPlainText("OpenAI API에 분석을 요청하는 중입니다...")
        self.status_label.setText("분석 중...")

        self.analysis_thread = QThread(self)
        self.analysis_worker = ImageAnalysisWorker(self.selected_image_path)
        self.analysis_worker.moveToThread(self.analysis_thread)
        self.analysis_thread.started.connect(self.analysis_worker.analyze)
        self.analysis_worker.finished.connect(self.show_result)
        self.analysis_worker.failed.connect(self.show_error)
        self.analysis_worker.finished.connect(self.finish_analysis)
        self.analysis_worker.failed.connect(self.finish_analysis)
        self.analysis_thread.finished.connect(self.cleanup_thread)
        self.analysis_thread.start()

    def show_result(self, result):
        self.result_text.setPlainText(result)
        self.status_label.setText("분석 완료")

    def show_error(self, message):
        self.result_text.clear()
        self.status_label.setText("분석 실패")
        QMessageBox.critical(self, "분석 오류", message)

    def finish_analysis(self, _result):
        self.select_button.setEnabled(True)
        self.analyze_button.setEnabled(True)
        self.analysis_thread.quit()

    def cleanup_thread(self):
        self.analysis_worker.deleteLater()
        self.analysis_thread.deleteLater()
        self.analysis_worker = None
        self.analysis_thread = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageAnalyzerWindow()
    window.show()
    sys.exit(app.exec())
