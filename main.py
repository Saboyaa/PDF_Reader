import sys
import json
import os
import time
import threading
import subprocess
import math
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QMessageBox
)
from pathlib import Path


class PacmanProgress(QWidget):
    def __init__(self):
        super().__init__()
        self.total = 0
        self.done = 0
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)

    def animate(self):
        self.angle = (self.angle + 40) % 360
        self.update()

    def setProgress(self, done, total):
        self.done = done
        self.total = max(total, 1)
        self.update()

    def paintEvent(self, event):
        if self.total == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        y_center = h / 2

        # Número fixo de bolinhas para representar o progresso visual
        num_dots = 20
        dot_radius = 6
        left_margin = 60
        right_margin = 60
        spacing = (w - left_margin - right_margin - num_dots * dot_radius * 2) / (num_dots - 1)

        # Progresso percentual
        progress = self.done / self.total

        # Bolinhas fixas
        for i in range(num_dots):
            x = left_margin + i * (2 * dot_radius + spacing)
            color = QColor("#a3c4c2") if (i / (num_dots - 1)) <= progress else QColor("#3a4a4a")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x), int(y_center - dot_radius), int(dot_radius * 2), int(dot_radius * 2))

        # Pac-Man dourado se movendo do início ao fim
        pac_size = 30
        pac_x = left_margin + (w - left_margin - right_margin - pac_size) * progress
        pac_y = y_center - pac_size / 2
        mouth_angle = 50 * math.sin(math.radians(self.angle))
        painter.setBrush(QBrush(QColor("#f3daaa")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPie(QRectF(pac_x, pac_y, pac_size, pac_size),
                        int(mouth_angle * 16),
                        int((360 - 2 * mouth_angle) * 16))


class FastProcessorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Processador de Arquivos")
        self.resize(1000, 700)

        # 🌙 Tema pastel escuro
        self.setStyleSheet("""
            QWidget {
                background-color: #648285;
                color: #f3daaa;
                font-family: "Segoe UI Variable", "Roboto", sans-serif;
            }
            QPushButton {
                border-radius: 10px;
                padding: 10px 22px;
                font-size: 14px;
                font-weight: 600;
                border: none;
                background-color: #f3daaa;
                color: #080d0d;
            }
            QPushButton:hover {
                background-color: #a3c4c2;
            }
            QTextEdit {
                background-color: #648285;
                border: 1px solid #4e6668;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                color: #f3daaa;
                font-family: "Cascadia Code", monospace;
            }
            QLabel#title {
                font-size: 22px;
                font-weight: bold;
                color: #f3daaa;
                margin-bottom: 4px;
            }
            QLabel#subtitle {
                color: #a3c4c2;
                font-size: 13px;
                margin-bottom: 15px;
            }
            QLabel#status {
                font-size: 14px;
                color: #b4a68e;
            }
    	    QScrollBar:vertical {
        	background: transparent;
        	width: 8px;
        	margin: 4px 0;
        	border-radius: 4px;
    	    }
    	    QScrollBar::handle:vertical {
        	background: #a3c4c2;
        	border-radius: 4px;
        	min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
        	background: #f3daaa;
    	    }
    	    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        	height: 0;
        	background: none;
    	    }
    	    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        	background: none;
    	    }
        """)

        self.json_path = "json/result.json"
        self.buffered_path = "json/buffed.json"  # Caminho padrão do buffed.json
        self.files = []
        self.monitoring = False
        self.start_time = 0

        self._setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_json_view)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Extrator de PDF - Saboya")
        title.setObjectName("title")
        subtitle = QLabel("Atualizando result.json em tempo real")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Botões
        button_row = QHBoxLayout()
        self.file_button = QPushButton("Selecionar Arquivos")
        self.file_button.clicked.connect(self.select_files)

        self.folder_button = QPushButton("Selecionar Pasta")
        self.folder_button.clicked.connect(self.select_folder)

        self.buff_button = QPushButton("Selecionar Schema")
        self.buff_button.clicked.connect(self.select_buffed)

        self.process_button = QPushButton("▶ PROCESSAR")
        self.process_button.clicked.connect(self.start_processing)

        self.clear_button = QPushButton("Limpar")
        self.clear_button.clicked.connect(self.clear_all)

        for btn in [self.file_button, self.folder_button, self.buff_button, self.process_button, self.clear_button]:
            button_row.addWidget(btn)
        layout.addLayout(button_row)

        self.status_label = QLabel("Nenhum arquivo selecionado.")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        # Pac-Man progress
        self.pacman_progress = PacmanProgress()
        self.pacman_progress.setFixedHeight(100)
        layout.addWidget(self.pacman_progress)

        # JSON Viewer
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        layout.addWidget(self.json_view, stretch=1)

    # --- Funções principais ---
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar Arquivos")
        if files:
            self.files = files
            self.status_label.setText(f"{len(files)} arquivo(s) selecionado(s) ✓")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta")
        if folder:
            self.files = [str(f) for f in Path(folder).iterdir() if f.is_file()]
            self.status_label.setText(f"{len(self.files)} arquivo(s) selecionado(s) ✓")

    def select_buffed(self):
        file, _ = QFileDialog.getOpenFileName(self, "Selecionar dataset.json", "", "Arquivos JSON (*.json)")
        if file:
            self.buffered_path = file
            self.status_label.setText(f"buffed.json personalizado: {os.path.basename(file)} ✓")

    def clear_all(self):
        self.files = []
        self.json_view.clear()
        self.status_label.setText("Nenhum arquivo selecionado.")
        self.pacman_progress.setProgress(0, 0)
        self.monitoring = False
        if os.path.exists(self.json_path):
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def start_processing(self):
        if not self.files:
            QMessageBox.warning(self, "Aviso", "Selecione arquivos ou uma pasta antes!")
            return

        try:
            with open(self.buffered_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
                self.total_expected = len(dataset)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível ler {self.buffered_path}:\n{e}")
            return
        
        self.status_label.setText("Processando...")
        self.start_time = time.perf_counter()
        self.pacman_progress.setProgress(0, self.total_expected)
        
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump([], f)

        with open("json/files_to_process.json", "w", encoding="utf-8") as f:
            json.dump(self.files, f)

        threading.Thread(target=self.run_external_process, daemon=True).start()
        self.monitoring = True
        self.timer.start(500)

    def run_external_process(self):
        try:
            self.process = subprocess.Popen([sys.executable, "Extractor.py", *self.files,self.buffered_path])
        except subprocess.CalledProcessError as e:
            print("Erro ao executar script:", e)
        finally:
            self.monitoring = False

    def update_json_view(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.json_view.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            self.json_view.verticalScrollBar().setValue(
                self.json_view.verticalScrollBar().maximum()
            )
            self.pacman_progress.setProgress(len(data), self.total_expected)
            if len(data) >= self.total_expected:
                elapsed = time.perf_counter() - self.start_time
                self.status_label.setText(f"Os {self.total_expected} schemas mapeados foram concluídos em {elapsed:.2f}s")
                self.timer.stop()
                if self.process.poll() is None:  # ainda está rodando
                    self.process.kill()   
        
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    ui = FastProcessorUI()
    ui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
