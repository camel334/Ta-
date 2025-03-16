import sys
import time
import subprocess  # Paket yükleme için eklendi
from pypresence import Presence  # Discord RPC için eklendi
import pyautogui
import google.generativeai as genai
from PIL import Image
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QIcon, QPainter, QPainterPath, QBrush, QPen
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
                           QLineEdit, QFileDialog, QTextEdit, QGraphicsDropShadowEffect, 
                           QSizePolicy, QFrame, QScrollArea, QCheckBox, QDialog, QMessageBox,
                           QGraphicsOpacityEffect, QSpacerItem)
import threading
import os
import datetime
import requests
from bs4 import BeautifulSoup
import re  # Düzenli ifadeler için
import shutil  # Dosya işlemleri için
import json  # Zamanlanmış görevler için eklendi

# Gerekli paketleri kontrol et ve eksik olanları yükle
def check_and_install_packages():
    packages = [
        "pyautogui",
        "google-generativeai",
        "pillow",
        "PyQt5"
    ]
    
    for package in packages:
        try:
            if package == "pillow":
                __import__("PIL")
            elif package == "PyQt5":
                __import__("PyQt5")
            elif package == "google-generativeai":
                __import__("google.generativeai")
            else:
                __import__(package)
            print(f"{package} zaten yüklü.")
        except ImportError:
            print(f"{package} bulunamadı, yükleniyor...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
                print(f"{package} başarıyla yüklendi.")
            except subprocess.CalledProcessError:
                print(f"{package} yüklenirken hata oluştu!")

# Uygulama başlamadan önce paketleri kontrol et
check_and_install_packages()

# API anahtarı diyalogu
class APIKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini API Anahtarı")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #282a36;
                color: white;
                font-family: 'Segoe UI', 'Arial';
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #383850;
                color: white;
                border: 1px solid #44445a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #6272a4;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
                color: white;
                font-size: 14px;
            }
            QPushButton#okButton {
                background-color: #50fa7b;
                color: #282a36;
            }
            QPushButton#okButton:hover {
                background-color: #5af78e;
            }
            QPushButton#cancelButton {
                background-color: #ff5555;
            }
            QPushButton#cancelButton:hover {
                background-color: #ff6e6e;
            }
            QTextEdit {
                background-color: #383850;
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                border: 1px solid #44445a;
            }
        """)
        
        self.api_key = ""
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Başlık ve açıklama
        title_label = QLabel("Gemini API Anahtarını Girin")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        info_label = QLabel("TAI'yi kullanmak için Google Gemini API anahtarı gereklidir. "
                          "Eğer API anahtarınız yoksa aşağıdaki adımları izleyebilirsiniz.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # API anahtarı alanı
        key_layout = QVBoxLayout()
        key_layout.setSpacing(8)
        key_label = QLabel("API Anahtarı:")
        key_label.setStyleSheet("font-weight: bold;")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Gemini API anahtarınızı buraya yapıştırın")
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        layout.addLayout(key_layout)
        
        # API anahtarı alma talimatları
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setText("API Anahtarı Alma Adımları:\n\n"
                             "1. https://aistudio.google.com/app/apikey adresine gidin\n"
                             "2. Google hesabınızla giriş yapın\n"
                             "3. 'Create API Key' butonuna tıklayın\n"
                             "4. Oluşturulan API anahtarını kopyalayın\n"
                             "5. Yukarıdaki alana yapıştırın\n\n"
                             "API anahtarınız güvenle saklanacaktır.")
        instructions.setFixedHeight(150)
        layout.addWidget(instructions)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Tamam")
        self.ok_button.setObjectName("okButton")
        self.ok_button.clicked.connect(self.accept_key)
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.resize(450, 450)
        
    def accept_key(self):
        self.api_key = self.key_input.text().strip()
        if not self.api_key:
            QMessageBox.warning(self, "Uyarı", "API anahtarı boş olamaz!")
            return
        
        # Minimal API anahtarı kontrolü (format ve uzunluk kontrolü)
        if not self.api_key.startswith("AIza") or len(self.api_key) < 30:
            response = QMessageBox.warning(
                self, 
                "Geçersiz API Anahtarı", 
                "Girdiğiniz API anahtarı geçersiz görünüyor. Devam etmek istiyor musunuz?", 
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                return
        
        self.accept()

# Gemini API anahtarı
GEMINI_API_KEY = ""

# UI güncellemesi için sinyal sınıfı
class UISignals(QObject):
    update_ui = pyqtSignal(object)
    show_error = pyqtSignal(object, object)

class ChatMessage(QFrame):
    def __init__(self, text, is_user=False, parent=None):
        super().__init__(parent)
        self.setObjectName("chatMessage")
        self.is_user = is_user
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Kullanıcı mesajını sağa, AI mesajını sola hizala
        message_layout = QHBoxLayout()
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        # Mesaj içeriği için çerçeve
        self.content_frame = QFrame(self)
        self.content_frame.setObjectName("messageContentFrame")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(12, 8, 12, 8)
        
        # Mesaj metni
        self.message = QTextEdit()
        self.message.setReadOnly(True)
        self.message.setPlainText(text)
        self.message.setObjectName("messageText")
        self.message.setFrameStyle(QFrame.NoFrame)
        self.message.setMinimumHeight(30)
        self.message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.message.document().setDocumentMargin(2)
        self.message.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_layout.addWidget(self.message)
        
        # Kullanıcı mesajını sağa, AI mesajını sola hizala
        if is_user:
            message_layout.addStretch(1)
            self.content_frame.setStyleSheet("""
                QFrame#messageContentFrame {
                    background-color: #4285f4;
                    border-radius: 15px;
                    border-top-right-radius: 5px;
                }
                QTextEdit#messageText {
                    background-color: transparent;
                    color: white;
                    font-size: 15px;
                    border: none;
                }
            """)
        else:
            self.content_frame.setStyleSheet("""
                QFrame#messageContentFrame {
                    background-color: #444654;
                    border-radius: 15px;
                    border-top-left-radius: 5px;
                }
                QTextEdit#messageText {
                    background-color: transparent;
                    color: white;
                    font-size: 15px;
                    border: none;
                }
            """)
            message_layout.addStretch(1)
        
        # Mesaj çerçevesini maksimum genişliğe ayarla
        self.content_frame.setMaximumWidth(600)
        message_layout.addWidget(self.content_frame)
        layout.addLayout(message_layout)

# Zamanlanmış görevler yöneticisi sınıfı
class ScheduledTaskManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.tasks = []  # Görevleri saklayacak liste
        self.task_file = os.path.join(os.path.expanduser("~"), ".tai_tasks.json")
        self.load_tasks()  # Kaydedilmiş görevleri yükle
        
        # Zamanlayıcı oluştur ve dakikada bir kontrol et
        self.timer = QTimer(parent)
        self.timer.timeout.connect(self.check_tasks)
        self.timer.start(60000)  # 60 saniye = 1 dakika
        
        # Anlık görevler için zamanlayıcı
        self.immediate_timer = QTimer(parent)
        self.immediate_timer.timeout.connect(self.check_immediate_tasks)
        self.immediate_timer.start(1000)  # Her saniye kontrol et
        
        # Anlık görevler listesi
        self.immediate_tasks = []
    
    def load_tasks(self):
        # Kayıtlı görevleri dosyadan yükle
        if os.path.exists(self.task_file):
            try:
                with open(self.task_file, 'r') as f:
                    self.tasks = json.load(f)
                print(f"{len(self.tasks)} zamanlanmış görev yüklendi.")
            except Exception as e:
                print(f"Görevler yüklenirken hata: {e}")
                self.tasks = []
        else:
            print("Görev dosyası bulunamadı, yeni oluşturulacak.")
            self.tasks = []
    
    def save_tasks(self):
        # Görevleri dosyaya kaydet
        try:
            with open(self.task_file, 'w') as f:
                json.dump(self.tasks, f)
            print(f"{len(self.tasks)} görev kaydedildi.")
        except Exception as e:
            print(f"Görevler kaydedilirken hata: {e}")
    
    def add_task(self, time, action, parameters=None, repeat="daily"):
        # Yeni görev ekle
        task = {
            "time": time,
            "action": action,
            "parameters": parameters or {},
            "repeat": repeat,
            "last_run": None
        }
        self.tasks.append(task)
        self.save_tasks()
        return len(self.tasks) - 1  # Görev ID'sini döndür
    
    def delete_task(self, task_id):
        # Görevi sil
        if 0 <= task_id < len(self.tasks):
            del self.tasks[task_id]
            self.save_tasks()
            return True
        return False
    
    def check_tasks(self):
        # Mevcut zamanı al
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()
        
        # Tüm görevleri kontrol et
        for task in self.tasks:
            # Görevin zamanı geldi mi?
            if task["time"] == current_time:
                # Tekrar ayarına göre kontrol
                if task["repeat"] == "daily" or \
                   (task["repeat"] == "weekdays" and current_day not in ["saturday", "sunday"]) or \
                   (task["repeat"] == "weekends" and current_day in ["saturday", "sunday"]) or \
                   (task["repeat"] == current_day):
                    
                    # Son çalıştırma zamanını kontrol et
                    last_run = task.get("last_run")
                    if not last_run or not last_run.startswith(now.strftime("%Y-%m-%d")):
                        # Görevi çalıştır
                        self.execute_task(task)
                        
                        # Son çalıştırma zamanını güncelle
                        task["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                        self.save_tasks()
    
    def execute_task(self, task):
        # Görev tipine göre işlem yap
        action = task["action"]
        params = task["parameters"]
        
        print(f"Görev çalıştırılıyor: {action}, parametreler: {params}")
        
        if action == "shutdown":
            # PC'yi kapat
            shutdown_time = params.get("delay", 60)  # Varsayılan 60 saniye
            
            # Kullanıcıya bildir
            QMessageBox.information(
                None, 
                "Zamanlanmış Görev", 
                f"Bilgisayarınız {shutdown_time} saniye içinde kapatılacak.",
                QMessageBox.Ok
            )
            
            # Kapatma komutunu çalıştır
            os.system(f"shutdown /s /t {shutdown_time}")
        
        elif action == "restart":
            # PC'yi yeniden başlat
            restart_time = params.get("delay", 60)  # Varsayılan 60 saniye
            
            # Kullanıcıya bildir
            QMessageBox.information(
                None, 
                "Zamanlanmış Görev", 
                f"Bilgisayarınız {restart_time} saniye içinde yeniden başlatılacak.",
                QMessageBox.Ok
            )
            
            # Yeniden başlatma komutunu çalıştır
            os.system(f"shutdown /r /t {restart_time}")
        
        elif action == "reminder":
            # Hatırlatıcı göster
            QMessageBox.information(
                None, 
                "Hatırlatıcı", 
                params.get("message", "Zamanlanmış hatırlatıcı"),
                QMessageBox.Ok
            )
        
        elif action == "run_app":
            # Uygulama çalıştır
            app_name = params.get("app_name", "")
            app_exe = params.get("app_exe", f"{app_name}.exe")
            if app_name and self.parent:
                # Mevcut uygulama açma fonksiyonunu çağır
                self.parent.find_and_run_app(app_name, app_exe)

    def add_immediate_task(self, delay_minutes, action, parameters=None):
        """Hemen/kısa süreli görev ekler"""
        task = {
            "execute_time": time.time() + (delay_minutes * 60),  # Şu andan X dakika sonra
            "action": action,
            "parameters": parameters or {}
        }
        self.immediate_tasks.append(task)
        return len(self.immediate_tasks) - 1  # Görev ID'sini döndür

    def check_immediate_tasks(self):
        """Anlık görevleri kontrol eder"""
        current_time = time.time()
        tasks_to_remove = []
        
        for i, task in enumerate(self.immediate_tasks):
            if current_time >= task["execute_time"]:
                # Görevi çalıştır
                self.execute_task(task)
                tasks_to_remove.append(i)
        
        # Tamamlanan görevleri listeden kaldır
        for i in reversed(tasks_to_remove):
            del self.immediate_tasks[i]

class App(QWidget):
    def __init__(self):
        super().__init__()
        
        # Discord RPC başlatma
        try:
            self.rpc = Presence("1350774636391956542")  # Discord uygulama ID'nizi buraya yazın
            self.rpc.connect()
            self.update_discord_status("Ana Menü", "TAI ile sohbet ediyor")
        except Exception as e:
            print(f"Discord RPC başlatılamadı: {e}")
            self.rpc = None
        
        # API anahtarını sor
        self.get_api_key()
        
        # API anahtarı yoksa uygulamayı kapat
        if not GEMINI_API_KEY:
            sys.exit()
            
        # API anahtarını ayarla
        genai.configure(api_key=GEMINI_API_KEY)

        self.setWindowTitle('TAI - Yapay Zeka Asistanı')
        self.setGeometry(100, 100, 1100, 800)
        
        # Ana uygulama stili
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                font-family: 'Segoe UI', 'Arial';
                color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d3a;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #6272a4;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QLineEdit {
                padding: 8px 12px;
                background-color: #383850;
                border: 1px solid #44445a;
                border-radius: 12px;
                color: white;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #6272a4;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.85;
            }
            QCheckBox {
                spacing: 8px;
                color: white;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #6272a4;
                background-color: #2d2d3a;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #6272a4;
                background-color: #6272a4;
            }
        """)
        
        # Görsel analizi için değişkenler
        self.current_image_path = None
        
        # Ekran görüntüsü için değişkenler
        self.screenshot_dir = "screenshots"
        self.is_auto_screenshot_enabled = False
        self.screenshot_timer = QTimer(self)
        self.screenshot_timer.timeout.connect(self.take_auto_screenshot)
        
        # UI güncellemeleri için sinyal
        self.ui_signals = UISignals()
        self.ui_signals.update_ui.connect(self.on_update_ui)
        self.ui_signals.show_error.connect(self.on_show_error)
        
        # Zamanlanmış görevler yöneticisi
        self.task_manager = ScheduledTaskManager(self)
        
        # Screenshots klasörünü oluştur
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

        self.initUI()
        
    def get_api_key(self):
        """Kullanıcıdan API anahtarı alır"""
        global GEMINI_API_KEY
        
        # Daha önce kaydedilmiş API anahtarını kontrol et
        api_key_file = os.path.join(os.path.expanduser("~"), ".tai_api_key")
        
        if os.path.exists(api_key_file):
            try:
                with open(api_key_file, "r") as f:
                    saved_key = f.read().strip()
                    if saved_key:
                        # API anahtarını doğrulamak için bir onay mesajı göster
                        response = QMessageBox.question(
                            None,
                            "Kayıtlı API Anahtarı",
                            "Kayıtlı API anahtarınız bulundu. Bu anahtarı kullanmak istiyor musunuz?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if response == QMessageBox.Yes:
                            GEMINI_API_KEY = saved_key
                            return
            except Exception as e:
                print(f"API anahtarı okuma hatası: {e}")
        
        # API anahtarı diyaloğunu göster
        dialog = APIKeyDialog()
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.api_key:
            GEMINI_API_KEY = dialog.api_key
            
            # API anahtarını kaydetme seçeneği sor
            save_response = QMessageBox.question(
                None,
                "API Anahtarını Kaydet",
                "API anahtarınızı bilgisayarınıza kaydetmek istiyor musunuz?\n"
                "Bu sayede uygulamayı her açtığınızda tekrar girmenize gerek kalmaz.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if save_response == QMessageBox.Yes:
                try:
                    with open(api_key_file, "w") as f:
                        f.write(GEMINI_API_KEY)
                    QMessageBox.information(None, "Başarılı", "API anahtarınız kaydedildi.")
                except Exception as e:
                    QMessageBox.warning(None, "Hata", f"API anahtarı kaydedilemedi: {str(e)}")

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Başlık kısmı
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_frame.setStyleSheet("""
            QFrame#titleFrame {
                background-color: #2d2d3a;
                border-bottom: 1px solid #44445a;
                min-height: 60px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 10, 20, 10)
        
        # Logo/İkon
        logo_label = QLabel()
        logo_label.setText("TAI")
        logo_label.setMaximumSize(40, 40)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("background-color: #6272a4; border-radius: 20px; color: white; font-weight: bold; font-size: 16px;")
        title_layout.addWidget(logo_label)
        
        # Başlık
        title_label = QLabel("TAI - Türkçe Yapay Zeka Asistanı")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin-left: 10px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # API Anahtarı değiştirme butonu
        api_button = QPushButton("API Anahtarını Değiştir")
        api_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b3b3cc;
                border: none;
                font-size: 13px;
                font-weight: normal;
                text-decoration: underline;
                padding: 5px;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        api_button.clicked.connect(self.change_api_key)
        title_layout.addWidget(api_button)
        
        main_layout.addWidget(title_frame)

        # Mesaj geçmişi alanı
        message_container = QFrame()
        message_container.setObjectName("messageContainer")
        message_container.setStyleSheet("""
            QFrame#messageContainer {
                background-color: #282a36;
            }
        """)
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        self.messages_area = QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setFrameStyle(QFrame.NoFrame)
        self.messages_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messages_area.setStyleSheet("background-color: transparent;")
        
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: transparent;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(15)  # Mesajlar arası boşluk
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.addStretch()
        
        self.messages_area.setWidget(self.messages_container)
        message_layout.addWidget(self.messages_area)
        
        main_layout.addWidget(message_container, 1)  # Mesaj alanı esnek olarak büyüsün

        # Hoşgeldin mesajı
        welcome_message = ChatMessage("👋 Merhaba! Ben TAI, Türkçe yapay zeka asistanınızım. Size nasıl yardımcı olabilirim?", is_user=False)
        self.messages_layout.addWidget(welcome_message)

        # Alt kısım - mesaj gönderme alanı
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_frame.setStyleSheet("""
            QFrame#bottomFrame {
                background-color: #2d2d3a;
                border-top: 1px solid #44445a;
                min-height: 180px;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(20, 15, 20, 15)
        
        # Butonlar için layout
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        # İkonlu butonlar
        self.upload_button = QPushButton(" Görsel Yükle")
        self.upload_button.setIcon(QIcon.fromTheme("document-open", QIcon()))
        self.upload_button.setIconSize(QSize(18, 18))
        self.upload_button.setStyleSheet("""
            QPushButton {
                background-color: #50fa7b;
                color: #282a36;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #5af78e;
            }
        """)
        self.upload_button.clicked.connect(self.open_file)
        
        self.analyze_button = QPushButton(" Görseli Analiz Et")
        self.analyze_button.setIcon(QIcon.fromTheme("view-preview", QIcon()))
        self.analyze_button.setIconSize(QSize(18, 18))
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #f1fa8c;
                color: #282a36;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f4f99d;
            }
            QPushButton:disabled {
                background-color: #6272a4;
                color: #b3b3cc;
            }
        """)
        self.analyze_button.clicked.connect(self.analyze_image_with_ai)
        self.analyze_button.setEnabled(False)  # Başlangıçta devre dışı
        
        self.screenshot_button = QPushButton(" Ekran Görüntüsü Al")
        self.screenshot_button.setIcon(QIcon.fromTheme("camera-photo", QIcon()))
        self.screenshot_button.setIconSize(QSize(18, 18))
        self.screenshot_button.setStyleSheet("""
            QPushButton {
                background-color: #bd93f9;
                color: white;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #caa9fa;
            }
        """)
        self.screenshot_button.clicked.connect(self.take_screenshot)
        
        self.auto_screenshot_checkbox = QCheckBox("Dakikada Bir Ekran Analizi")
        self.auto_screenshot_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                padding: 10px;
            }
        """)
        self.auto_screenshot_checkbox.stateChanged.connect(self.toggle_auto_screenshot)
        
        self.web_search_button = QPushButton(" Web'de Ara")
        self.web_search_button.setIcon(QIcon.fromTheme("edit-find", QIcon()))
        self.web_search_button.setIconSize(QSize(18, 18))
        self.web_search_button.setStyleSheet("""
            QPushButton {
                background-color: #ff79c6;
                color: white;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #ff92d0;
            }
        """)
        self.web_search_button.clicked.connect(self.show_web_search_dialog)
        
        control_layout.addWidget(self.upload_button)
        control_layout.addWidget(self.analyze_button)
        control_layout.addWidget(self.screenshot_button)
        control_layout.addWidget(self.auto_screenshot_checkbox)
        control_layout.addWidget(self.web_search_button)
        bottom_layout.addLayout(control_layout)
        
        # Mesaj giriş alanı
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 10, 0, 0)
        input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Bir mesaj yazın veya 'Chrome'u aç' gibi bir komut verin...")
        self.chat_input.setMinimumHeight(50)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #383850;
                border: 1px solid #44445a;
                border-radius: 25px;
                color: white;
                font-size: 15px;
                padding: 0 20px;
            }
            QLineEdit:focus {
                border: 1px solid #6272a4;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        
        send_button = QPushButton()
        send_button.setIcon(QIcon.fromTheme("arrow-right", QIcon()))
        send_button.setIconSize(QSize(20, 20))
        send_button.setFixedSize(50, 50)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #ff79c6;
                border-radius: 25px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #ff92d0;
            }
        """)
        send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(send_button)
        bottom_layout.addLayout(input_layout)
        
        main_layout.addWidget(bottom_frame)
        
        self.setLayout(main_layout)
        
        # Görsel önizleme alanı (başlangıçta gizli)
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("""
            background-color: #383850;
            border-radius: 10px;
            padding: 15px;
            margin: 10px;
        """)
        self.image_preview.hide()
        self.messages_layout.addWidget(self.image_preview)
    
    def change_api_key(self):
        """API anahtarını değiştirme fonksiyonu"""
        global GEMINI_API_KEY
        
        dialog = APIKeyDialog()
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.api_key:
            old_key = GEMINI_API_KEY
            GEMINI_API_KEY = dialog.api_key
            
            # API anahtarını kaydetme seçeneği sor
            save_response = QMessageBox.question(
                self,
                "API Anahtarını Kaydet",
                "Yeni API anahtarınızı bilgisayarınıza kaydetmek istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if save_response == QMessageBox.Yes:
                api_key_file = os.path.join(os.path.expanduser("~"), ".tai_api_key")
                try:
                    with open(api_key_file, "w") as f:
                        f.write(GEMINI_API_KEY)
                    QMessageBox.information(self, "Başarılı", "Yeni API anahtarınız kaydedildi.")
                except Exception as e:
                    QMessageBox.warning(self, "Hata", f"API anahtarı kaydedilemedi: {str(e)}")
            
            # Genai yapılandırmasını güncelle
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Kullanıcıya başarılı mesajı göster
            success_message = ChatMessage("API anahtarınız başarıyla değiştirildi.", is_user=False)
            self.messages_layout.addWidget(success_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )

    def button_style(self, color):
        # Artık kullanılmıyor - her buton kendi stilini alıyor
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 10px 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
            }}
        """

    def send_message(self):
        user_text = self.chat_input.text().strip()
        if not user_text:
            return
            
        # Discord durumunu güncelle
        self.update_discord_status("Sohbet", "TAI ile mesajlaşıyor")
            
        # Kullanıcı mesajını ekle
        user_message = ChatMessage(user_text, is_user=True)
        self.messages_layout.addWidget(user_message)
        
        # Giriş alanını temizle
        self.chat_input.clear()
        
        # Önce program açma komutunu kontrol et
        if self.check_and_run_app_command(user_text):
            # Program açma komutu başarıyla işlendiyse, AI yanıtı istenmiyor
            pass
        # Dosya işlemleri komutunu kontrol et
        elif self.check_and_run_file_command(user_text):
            # Dosya işlemi komutu başarıyla işlendiyse, AI yanıtı istenmiyor
            pass
        # Zamanlanmış görev komutlarını kontrol et
        elif self.check_and_run_scheduled_task_command(user_text):
            # Zamanlanmış görev komutu başarıyla işlendiyse, AI yanıtı istenmiyor
            pass
        else:
            # Hiçbir özel komut değilse, normal AI yanıtını al
            self.get_ai_response(user_text)
        
        # Otomatik olarak en aşağıya kaydır
        QApplication.processEvents()
        self.messages_area.verticalScrollBar().setValue(
            self.messages_area.verticalScrollBar().maximum()
        )

    def check_and_run_app_command(self, text):
        """Kullanıcı mesajını analiz eder ve program açma komutu varsa uygulamayı açar"""
        # Program açma komutlarını tespit etmek için düzenli ifadeler
        app_patterns = [
            r'(.*?)(?:\'u|\'ı|\'i|\'yi|\'yı|yi|yı|i|ı|u|ü)\s+aç(?:ar\s+mısın)?',  # X'i aç, X'ı aç, X'u aç, X'ü aç, Xi aç, Xı aç, Xu aç, Xü aç
            r'(.*?)\s+programını\s+aç(?:ar\s+mısın)?',  # X programını aç
            r'(.*?)\s+çalıştır(?:ır\s+mısın)?'  # X çalıştır
        ]
        
        for pattern in app_patterns:
            match = re.search(pattern, text.lower())
            if match:
                app_name = match.group(1).strip()
                # Yaygın program adı düzeltmeleri
                app_map = {
                    'chrome': 'chrome.exe',
                    'krom': 'chrome.exe',
                    'google chrome': 'chrome.exe',
                    'edge': 'msedge.exe',
                    'microsoft edge': 'msedge.exe',
                    'firefox': 'firefox.exe',
                    'mozilla firefox': 'firefox.exe',
                    'explorer': 'explorer.exe',
                    'dosya gezgini': 'explorer.exe',
                    'word': 'winword.exe',
                    'excel': 'excel.exe',
                    'powerpoint': 'powerpnt.exe',
                    'notepad': 'notepad.exe',
                    'not defteri': 'notepad.exe',
                    'hesap makinesi': 'calc.exe',
                    'hesap makinası': 'calc.exe',
                    'calculator': 'calc.exe',
                    'paint': 'mspaint.exe',
                    'spotify': 'spotify.exe',
                    'discord': 'discord.exe',
                    'telegram': 'telegram.exe',
                    'whatsapp': 'whatsapp.exe',
                    'vs code': 'code.exe',
                    'visual studio code': 'code.exe',
                    'visual studio': 'devenv.exe',
                }
                
                # Eşleşen program adı varsa düzelt
                if app_name in app_map:
                    app_exe = app_map[app_name]
                else:
                    # Yoksa .exe ekle
                    app_exe = f"{app_name}.exe"
                
                # Programı bul ve çalıştır
                if self.find_and_run_app(app_name, app_exe):
                    return True  # Program açma komutu işlendi
        
        return False  # Program açma komutu değil
    
    def find_and_run_app(self, app_name, app_exe):
        """Programı sistemde arar ve bulursa çalıştırır"""
        try:
            # Program bilgisi mesajı
            info_message = ChatMessage(f"'{app_name}' programını arıyorum...", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            
            # Yaygın program yolları
            common_paths = [
                r"C:\Program Files",
                r"C:\Program Files (x86)",
                os.path.join(os.environ['LOCALAPPDATA'], "Programs"),
                os.environ['APPDATA'],
                os.path.join(os.environ['LOCALAPPDATA']),
                os.path.join(os.environ['USERPROFILE'], "AppData", "Local"),
                os.path.join(os.environ['USERPROFILE'], "AppData", "Roaming"),
                os.path.join(os.environ['USERPROFILE'], "AppData", "Local", "Programs"),
                r"C:\Windows",
                r"C:\Windows\System32"
            ]
            
            # Program exe'sini ara
            app_path = None
            for path in common_paths:
                if not os.path.exists(path):
                    continue
                    
                # İlk arama yöntemi: direkt exe arama
                for root, dirs, files in os.walk(path):
                    if app_exe.lower() in [f.lower() for f in files]:
                        for file in files:
                            if file.lower() == app_exe.lower():
                                app_path = os.path.join(root, file)
                                # Bulundu, aramayı durdur
                                break
                    # Bulunduysa ana döngüyü kır
                    if app_path:
                        break
                        
                # Bulunduysa sonraki dizinlere bakma
                if app_path:
                    break
            
            # Program bulunamadıysa PATH'de ara
            if not app_path:
                try:
                    # Sistemde programın yolunu bulmak için where komutunu kullan
                    result = subprocess.run(['where', app_exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        app_path = result.stdout.strip().split('\n')[0]
                except Exception as e:
                    print(f"PATH'de arama hatası: {e}")
            
            # Program bulunduysa çalıştır
            if app_path:
                # Programı başlat
                subprocess.Popen(app_path)
                
                # Başarı mesajı
                success_message = ChatMessage(f"✅ '{app_name}' programı başarıyla açıldı.", is_user=False)
                self.messages_layout.addWidget(success_message)
                return True
            else:
                # Bulunamadı mesajı
                not_found = ChatMessage(f"❌ '{app_name}' programı bulunamadı. Lütfen farklı bir program adı deneyin.", is_user=False)
                self.messages_layout.addWidget(not_found)
                return True  # Yine de komutu işlenmiş olarak kabul et
                
        except Exception as e:
            # Hata mesajı
            error_message = ChatMessage(f"Programı açarken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
            return True  # Komutu işlenmiş olarak kabul et
        
    def get_ai_response(self, user_input):
        try:
            # İşleniyor mesajı
            processing_msg = ChatMessage("⌛ Yanıt hazırlanıyor...", is_user=False)
            self.messages_layout.addWidget(processing_msg)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
            
            # AI yanıtını al
            response = genai.GenerativeModel("gemini-1.5-flash").generate_content([user_input])
            ai_text = response.text.strip()
            
            # İşleniyor mesajını kaldır
            self.messages_layout.removeWidget(processing_msg)
            processing_msg.deleteLater()
            
            # AI mesajını ekle
            ai_message = ChatMessage(ai_text, is_user=False)
            self.messages_layout.addWidget(ai_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
        except Exception as e:
            # İşleniyor mesajını kaldır
            self.messages_layout.removeWidget(processing_msg)
            processing_msg.deleteLater()
            
            # Hata mesajını ekle
            error_message = ChatMessage(f"❌ Bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)

    def open_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Bir Görsel Seçin", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)

        if file_path:
            self.preview_image(file_path)
            self.current_image_path = file_path
            self.analyze_button.setEnabled(True)  # Görsel yüklendiğinde analiz butonunu aktif et

    def preview_image(self, image_path):
        try:
            image = Image.open(image_path)
            image.thumbnail((400, 300))  # Boyutu sınırla
            
            # Görseli PyQt5 uyumlu hale getir
            qimage = QImage(image_path)
            pixmap = QPixmap.fromImage(qimage).scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Yuvarlak köşeli çerçevede görüntüle
            self.image_preview.setPixmap(pixmap)
            self.image_preview.show()
            
            # Resim yüklendi mesajı
            message = ChatMessage(f"📸 Görsel yüklendi: {os.path.basename(image_path)}", is_user=True)
            self.messages_layout.addWidget(message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
        except Exception as e:
            error_message = ChatMessage(f"Görsel yüklenirken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)

    def analyze_image_with_ai(self):
        if not self.current_image_path:
            message = ChatMessage("❗ Lütfen önce bir görsel yükleyin!", is_user=False)
            self.messages_layout.addWidget(message)
            return
            
        try:
            # Discord durumunu güncelle
            self.update_discord_status("Görsel Analizi", "Yapay zeka ile görsel analiz ediyor")
            
            # Analiz işlemi başladı mesajı
            self.process_message = ChatMessage("🔍 Görsel analiz ediliyor...", is_user=False)
            self.messages_layout.addWidget(self.process_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
            
            # Görsel analizi için Gemini'ye istek gönder
            def analyze_thread():
                try:
                    image = Image.open(self.current_image_path)
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content(["Bu görseli analiz et ve açıkla.", image])
                    analysis_text = response.text
                    
                    # Sinyali kullanarak UI'ı güncelle
                    self.ui_signals.update_ui.emit({"type": "image_analysis", "text": analysis_text})
                    
                except Exception as e:
                    # Hata durumunda sinyali kullanarak hata mesajı göster
                    self.ui_signals.show_error.emit(f"❌ Görsel analiz edilirken bir hata oluştu: {str(e)}", self.process_message)
            
            # Analiz işlemini ayrı bir thread'de başlat
            threading.Thread(target=analyze_thread, daemon=True).start()
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Görsel analiz edilirken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
    
    def take_screenshot(self):
        """Manuel olarak ekran görüntüsü alma ve analiz etme"""
        try:
            # Discord durumunu güncelle
            self.update_discord_status("Ekran Analizi", "Ekran görüntüsü analiz ediyor")
            
            # Bilgi mesajı
            self.info_message = ChatMessage("📷 Ekran görüntüsü alınıyor...", is_user=False)
            self.messages_layout.addWidget(self.info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
            
            # Ekran görüntüsü alma ve kaydetme işlemi
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"screenshot_{timestamp}.png")
            
            # Uygulama kısa süreliğine minimize edilir (opsiyonel)
            self.showMinimized()
            time.sleep(0.5)  # Ekranın minimize olması için kısa bir bekleme
            
            # Ekran görüntüsü alma
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            
            # Uygulamayı tekrar göster
            self.showNormal()
            
            # Analiz etmek için görüntüyü yükle ve analiz et
            self.current_image_path = screenshot_path
            self.analyze_screenshot(screenshot_path, self.info_message)
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Ekran görüntüsü alınırken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
    
    def take_auto_screenshot(self):
        """Otomatik olarak ekran görüntüsü alma ve analiz etme"""
        try:
            # Ekran görüntüsü alma ve kaydetme işlemi
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"auto_screenshot_{timestamp}.png")
            
            # Uygulama minimize edilir (opsiyonel)
            self.showMinimized()
            time.sleep(0.5)  # Ekranın minimize olması için kısa bir bekleme
            
            # Ekran görüntüsü alma
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            
            # Uygulamayı tekrar göster
            self.showNormal()
            
            # Bilgi mesajı
            self.info_message = ChatMessage(f"Otomatik ekran görüntüsü alındı: {timestamp}", is_user=False)
            self.messages_layout.addWidget(self.info_message)
            
            # Analiz et
            self.current_image_path = screenshot_path
            self.analyze_screenshot(screenshot_path, self.info_message, is_auto=True)
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Otomatik ekran görüntüsü alınırken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
    
    def analyze_screenshot(self, screenshot_path, info_message=None, is_auto=False):
        """Ekran görüntüsünü analiz eden fonksiyon"""
        try:
            def analyze_thread():
                try:
                    image = Image.open(screenshot_path)
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    if is_auto:
                        prompt = [
                            "Bu bir ekran görüntüsüdür. Lütfen şunları yap:"
                            "1. Ekranda ne olduğunu kısaca açıkla"
                            "2. Kullanıcının ne yaptığını tahmin et"
                            "3. Kullanıcıya faydalı ipuçları ve öneriler ver"
                            "4. Kullanıcının daha verimli çalışması için tavsiyelerde bulun"
                            "Yanıtını Türkçe olarak, madde madde ve rehber formatında hazırla.",
                            image
                        ]
                    else:
                        prompt = ["Bu ekran görüntüsünü detaylı olarak analiz et ve eğer görüntüde kod varsa kodda hata vs. varsa uyar", image]
                    
                    response = model.generate_content(prompt)
                    analysis_text = response.text
                    
                    # Sinyali kullanarak UI'ı güncelle
                    data = {
                        "type": "screenshot_analysis", 
                        "text": analysis_text, 
                        "is_auto": is_auto,
                        "info_message": info_message
                    }
                    self.ui_signals.update_ui.emit(data)
                    
                except Exception as e:
                    # Hata durumunda sinyali kullanarak hata mesajı göster
                    self.ui_signals.show_error.emit(f"❌ Ekran görüntüsü analiz edilirken bir hata oluştu: {str(e)}", info_message)
            
            # Analiz işlemini ayrı bir thread'de başlat
            threading.Thread(target=analyze_thread, daemon=True).start()
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Ekran görüntüsü analiz işlemi başlatılırken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
    
    def on_update_ui(self, data):
        """UI güncellemelerini yapan metot (Sinyal tarafından çağrılır)"""
        try:
            if data["type"] == "image_analysis":
                result_message = ChatMessage(data["text"], is_user=False)
                self.messages_layout.addWidget(result_message)
                
                # Process mesajını kaldır
                self.messages_layout.removeWidget(self.process_message)
                self.process_message.deleteLater()
                
            elif data["type"] == "screenshot_analysis":
                info_message = data["info_message"]
                if info_message:
                    # Mevcut bilgi mesajını kaldır
                    self.messages_layout.removeWidget(info_message)
                    info_message.deleteLater()
                
                if data["is_auto"]:
                    title = f"🖥️ EKRAN ANALİZ RAPORU ({datetime.datetime.now().strftime('%H:%M')})"
                    result_message = ChatMessage(f"{title}\n\n{data['text']}", is_user=False)
                else:
                    result_message = ChatMessage(data["text"], is_user=False)
                    
                self.messages_layout.addWidget(result_message)
            
            elif data["type"] == "web_search":
                # Web arama işleme
                processing_msg = data["processing_msg"]
                query = data["query"]
                results = data["results"]
                
                # İşleme mesajını kaldır
                self.messages_layout.removeWidget(processing_msg)
                processing_msg.deleteLater()
                
                if results:
                    # Sonuçları hazırla
                    result_text = f"📊 '{query}' için arama sonuçları:\n\n"
                    
                    for idx, result in enumerate(results, 1):
                        result_text += f"{idx}. {result['title']}\n"
                        result_text += f"   {result['link']}\n"
                        result_text += f"   {result['description']}\n\n"
                    
                    # Veya sonuç yok
                    if not results:
                        result_text += "Arama sonucu bulunamadı."
                    
                    # Sonuç mesajını ekle
                    result_message = ChatMessage(result_text, is_user=False)
                    self.messages_layout.addWidget(result_message)
                else:
                    # Sonuç bulunamazsa
                    no_result = ChatMessage("Bu arama için sonuç bulunamadı. Lütfen farklı anahtar kelimelerle tekrar deneyin.", is_user=False)
                    self.messages_layout.addWidget(no_result)
            
            # Otomatik olarak en aşağıya kaydır
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"UI güncelleme hatası: {e}")
    
    def on_show_error(self, error_text, info_message=None):
        """Hata mesajlarını gösteren metot (Sinyal tarafından çağrılır)"""
        try:
            error_message = ChatMessage(error_text, is_user=False)
            self.messages_layout.addWidget(error_message)
            
            if info_message:
                # Bilgi mesajını kaldır
                self.messages_layout.removeWidget(info_message)
                info_message.deleteLater()
                
            # Otomatik olarak en aşağıya kaydır
            self.messages_area.verticalScrollBar().setValue(
                self.messages_area.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Hata gösterme hatası: {e}")
    
    def toggle_auto_screenshot(self, state):
        """Otomatik ekran görüntüsü alma özelliğini açıp kapatır"""
        if state == Qt.Checked:
            # Otomatik ekran görüntüsü alma özelliğini aktifleştir
            self.is_auto_screenshot_enabled = True
            self.screenshot_timer.start(60000)  # 60000 ms = 1 dakika
            
            # Bilgi mesajı
            info_message = ChatMessage("Otomatik ekran analizi başlatıldı. Dakikada bir analiz yapılacak.", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # İlk ekran görüntüsünü hemen al
            QTimer.singleShot(1000, self.take_auto_screenshot)
            
        else:
            # Otomatik ekran görüntüsü alma özelliğini devre dışı bırak
            self.is_auto_screenshot_enabled = False
            self.screenshot_timer.stop()
            
            # Bilgi mesajı
            info_message = ChatMessage("Otomatik ekran analizi durduruldu.", is_user=False)
            self.messages_layout.addWidget(info_message)

    def show_web_search_dialog(self):
        """Web arama dialogunu gösterir"""
        search_dialog = QDialog(self)
        search_dialog.setWindowTitle("Web'de Ara")
        search_dialog.setMinimumWidth(450)
        search_dialog.setStyleSheet("""
            QDialog {
                background-color: #282a36;
                color: white;
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 15px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLineEdit {
                background-color: #383850;
                color: white;
                border: 1px solid #44445a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #6272a4;
            }
            QPushButton {
                background-color: #ff79c6;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #ff92d0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Başlık
        title_label = QLabel("Web'de Ne Aramak İstersiniz?")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; margin-bottom: 15px;")
        
        # Arama girişi
        search_label = QLabel("Arama Sorgusu:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("Web'de aramak istediğiniz bilgiyi girin")
        
        # Arama butonu
        search_button = QPushButton("Ara")
        search_button.setIcon(QIcon.fromTheme("edit-find", QIcon()))
        
        # Layout düzenleme
        layout.addWidget(title_label)
        layout.addWidget(search_label)
        layout.addWidget(search_input)
        layout.addWidget(search_button)
        
        search_dialog.setLayout(layout)
        
        # Arama butonuna fonksiyon bağlama
        search_button.clicked.connect(lambda: self.perform_web_search(search_input.text(), search_dialog))
        
        # Enter tuşuna fonksiyon bağlama
        search_input.returnPressed.connect(lambda: self.perform_web_search(search_input.text(), search_dialog))
        
        search_dialog.exec_()

    def perform_web_search(self, query, dialog=None):
        """Web araması yapar ve sonuçları gösterir"""
        if not query:
            return
        
        # Dialog'u kapat
        if dialog:
            dialog.accept()
        
        # Arama işlemi başladı bilgisi
        search_msg = ChatMessage(f"Web'de arıyorum: '{query}'", is_user=True)
        self.messages_layout.addWidget(search_msg)
        
        processing_msg = ChatMessage("Arama sonuçları alınıyor...", is_user=False)
        self.messages_layout.addWidget(processing_msg)
        
        # Otomatik olarak en aşağıya kaydır
        QApplication.processEvents()
        self.messages_area.verticalScrollBar().setValue(
            self.messages_area.verticalScrollBar().maximum()
        )
        
        # Thread'de web araması yap
        def search_thread():
            try:
                results = self.search_web(query)
                
                # Sonuçları ana thread'de göster
                self.ui_signals.update_ui.emit({
                    "type": "web_search", 
                    "results": results,
                    "query": query,
                    "processing_msg": processing_msg
                })
            except Exception as e:
                self.ui_signals.show_error.emit(f"❌ Web araması sırasında bir hata oluştu: {str(e)}", processing_msg)
        
        # Arama thread'ini başlat
        threading.Thread(target=search_thread, daemon=True).start()

    def search_web(self, query):
        """Web araması yapıp sonuçları döndürür"""
        try:
            print(f"Arama sorgusu: {query}")
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
            headers = {'User-Agent': user_agent}
            
            results = []
            
            # 1. Google/Gemini araması (birincil)
            print("Google/Gemini ile arama yapılıyor...")
            try:
                # Gemini modelini kullan
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"""'{query}' için web'de arama yapıyorum. 
                Lütfen bu konuda kısa bilgi ver ve 5 tane web sitesi öner.
                Her site için başlık, URL ve kısa açıklaması olmalı. 
                Yanıtını TÜRKÇE olarak ver ve bilgileri aşağıdaki formatta düzenle:
                
                1. [Başlık 1]
                   [URL 1]
                   [Açıklama 1]
                
                2. [Başlık 2]
                   [URL 2]
                   [Açıklama 2]
                
                (vs. diğer sonuçlar)
                """
                
                response = model.generate_content(prompt)
                if response and response.text:
                    # Gemini yanıtını işle ve uygun formata çevir
                    ai_text = response.text
                    
                    # Gemini yanıtını satırlara böl
                    lines = ai_text.split('\n')
                    
                    current_result = {}
                    counter = 0
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Yeni bir sonuç başlangıcı mı?
                        if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                            # Önceki sonucu kaydet (eğer varsa)
                            if current_result and 'title' in current_result and 'link' in current_result and 'description' in current_result:
                                results.append(current_result)
                                print(f"Google/Gemini sonucu eklendi: {current_result['title']}")
                            
                            # Yeni sonuç başlat
                            current_result = {}
                            # Başlığı ayıkla (numara kısmını kaldır: "1. Başlık" -> "Başlık")
                            title_parts = line.split('. ', 1)
                            if len(title_parts) > 1:
                                current_result['title'] = title_parts[1].strip()
                            counter = 1  # Sonraki satır URL olacak
                            
                        elif counter == 1 and 'title' in current_result:
                            # URL satırı
                            if line.startswith('http'):
                                current_result['link'] = line
                            else:
                                # URL değilse, başlığın devamı olabilir
                                current_result['title'] += ' ' + line
                                counter = 0  # URL gelmedi, hala başlık içindeyiz
                            counter = 2  # Sonraki satır açıklama olacak
                            
                        elif counter == 2 and 'link' in current_result:
                            # Açıklama satırı
                            current_result['description'] = line
                            counter = 0
                    
                    # Son sonucu da ekle
                    if current_result and 'title' in current_result and 'link' in current_result and 'description' in current_result:
                        results.append(current_result)
                        print(f"Google/Gemini sonucu eklendi: {current_result['title']}")
                    
                    # Eğer hiç düzgün sonuç çıkaramadıysak, tam metni tek bir sonuç olarak ekle
                    if not results:
                        results.append({
                            'title': "Google Arama Sonuçları",
                            'link': "https://www.google.com/search?q=" + query.replace(' ', '+') + "&hl=tr",
                            'description': ai_text[:200] + "..."  # İlk 200 karakteri al
                        })
            except Exception as e:
                print(f"Google/Gemini arama hatası: {e}")
            
            # Google'da sonuç bulunamazsa Bing ile dene
            if not results:
                print("Google/Gemini'de sonuç bulunamadı, Bing deneniyor...")
                
                # 2. Bing araması (ikincil)
                bing_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&setlang=tr&cc=TR"
                print(f"Bing Arama URL: {bing_url}")
                
                bing_response = requests.get(bing_url, headers=headers)
                print(f"Bing response status: {bing_response.status_code}")
                
                if bing_response.status_code == 200:
                    bing_soup = BeautifulSoup(bing_response.text, 'html.parser')
                    
                    # Bing sonuçlarını çek
                    bing_results = bing_soup.find_all('li', class_='b_algo')
                    print(f"Bing sonuç sayısı: {len(bing_results)}")
                    
                    for result in bing_results[:5]:
                        try:
                            title_el = result.find('h2')
                            link_el = result.find('a')
                            desc_el = result.find('p')
                            
                            if title_el and link_el and desc_el:
                                title = title_el.text.strip()
                                link = link_el['href']
                                description = desc_el.text.strip()
                                
                                results.append({
                                    'title': title,
                                    'link': link,
                                    'description': description
                                })
                                print(f"Bing sonucu eklendi: {title}")
                        except Exception as e:
                            print(f"Bing sonuç ayrıştırma hatası: {e}")
            
            # Bing'de de sonuç bulunamazsa DuckDuckGo ile dene
            if not results:
                print("Bing'de sonuç bulunamadı, DuckDuckGo deneniyor...")
                
                # 3. DuckDuckGo araması (yedek)
                # Türkçe sonuçlar için bölge parametresi ekle
                search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')} site:.tr&kl=tr-tr"
                print(f"DuckDuckGo Arama URL: {search_url}")
                
                response = requests.get(search_url, headers=headers)
                print(f"DuckDuckGo response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # DuckDuckGo sonuçlarını çek
                    search_results = soup.find_all('div', class_='result')
                    print(f"Bulunan DuckDuckGo sonuç sayısı: {len(search_results)}")
                    
                    for result in search_results[:5]:
                        try:
                            title_el = result.find('a', class_='result__a')
                            snippet_el = result.find('a', class_='result__snippet')
                            
                            if title_el and snippet_el:
                                title = title_el.text.strip()
                                link = title_el['href']
                                description = snippet_el.text.strip()
                                
                                # Eğer link başlangıcı "//" ise "https:" ekle
                                if link.startswith('//'):
                                    link = 'https:' + link
                                    
                                # Eğer link başlangıcı "http" değilse ve "//" ile başlamıyorsa
                                elif not link.startswith(('http://', 'https://')):
                                    # DuckDuckGo yönlendirme URL'sini temizle
                                    if '/l/?kh=' in link:
                                        # Link parametresini bul
                                        start_idx = link.find('uddg=')
                                        if start_idx != -1:
                                            start_idx += 5  # 'uddg=' uzunluğu
                                            link = link[start_idx:]
                                            # URL decode
                                            import urllib.parse
                                            link = urllib.parse.unquote(link)
                                
                                results.append({
                                    'title': title,
                                    'link': link,
                                    'description': description
                                })
                                print(f"DuckDuckGo sonucu eklendi: {title}")
                        except Exception as e:
                            print(f"DuckDuckGo sonuç ayrıştırma hatası: {e}")
            
            return results
        except Exception as e:
            print(f"Arama işleminde hata: {str(e)}")
            # Hata durumunda boş liste döndür ama hata fırlatma
            return []

    def check_and_run_file_command(self, text):
        """Kullanıcı mesajını analiz eder ve dosya işlemi komutu varsa çalıştırır"""
        # Ortak kullanılan klasörlerin yolları
        common_folders = {
            "belgeler": os.path.join(os.path.expanduser("~"), "Documents"),
            "dökümanlar": os.path.join(os.path.expanduser("~"), "Documents"),
            "dokümanlar": os.path.join(os.path.expanduser("~"), "Documents"),
            "documents": os.path.join(os.path.expanduser("~"), "Documents"),
            "indirilenler": os.path.join(os.path.expanduser("~"), "Downloads"),
            "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
            "masaüstü": os.path.join(os.path.expanduser("~"), "Desktop"),
            "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
            "resimler": os.path.join(os.path.expanduser("~"), "Pictures"),
            "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
            "müzik": os.path.join(os.path.expanduser("~"), "Music"),
            "music": os.path.join(os.path.expanduser("~"), "Music"),
            "videolar": os.path.join(os.path.expanduser("~"), "Videos"),
            "videos": os.path.join(os.path.expanduser("~"), "Videos"),
        }
        
        # Debug mesajı
        print(f"Dosya işlemi analiz ediliyor: '{text}'")
        print("Mevcut klasör yolları:", common_folders)
        
        # Küçük harfe çevir
        text_lower = text.lower()
        
        # Bir klasördeki tüm dosyaları taşıma komutu
        if ("klasöründeki" in text_lower or "içindeki" in text_lower) and "dosyaları" in text_lower and "taşı" in text_lower:
            print("Çoklu dosya taşıma komutu tespit edildi")
            
            # Kaynak ve hedef klasörü belirlemek için pattern
            patterns = [
                r'(.*?)\s+klasöründeki\s+dosyaları\s+(.*?)(?:\'a|\'e|e|a)\s+taşı',  # X klasöründeki dosyaları Y'e taşı
                r'(.*?)\s+içindeki\s+dosyaları\s+(.*?)(?:\'a|\'e|e|a)\s+taşı',      # X içindeki dosyaları Y'e taşı
                r'(.*?)deki\s+dosyaları\s+(.*?)(?:\'a|\'e|e|a)\s+taşı',             # Xdeki dosyaları Y'e taşı
                r'(.*?)daki\s+dosyaları\s+(.*?)(?:\'a|\'e|e|a)\s+taşı',             # Xdaki dosyaları Y'e taşı
                r'(.*?)\s+(?:klasöründe|içinde)\s+bulunan\s+(?:tüm\s+)?dosyaları\s+(.*?)(?:\'a|\'e|e|a)\s+taşı'  # X klasöründe bulunan dosyaları Y'e taşı
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    print(f"Çoklu dosya pattern eşleşti: {pattern}")
                    source = match.group(1).strip()
                    destination = match.group(2).strip()
                    print(f"Eşleşen kaynak klasör: {source}, hedef: {destination}")
                    
                    # Tam yol ise doğrudan kullan, aksi takdirde ortak klasörleri kontrol et
                    source_path = source
                    if ":\\" not in source and source in common_folders:
                        source_path = common_folders[source]
                    
                    dest_path = destination
                    if destination in common_folders:
                        dest_path = common_folders[destination]
                    
                    return self.move_all_files(source_path, dest_path)
        
        # Basitleştirilmiş dosya taşıma komutu
        if "dosya" in text_lower and "taşı" in text_lower:
            print("Dosya taşıma komutu tespit edildi")
            
            # İndirilenler/Downloads klasöründen bir dosyayı belgeler/documents klasörüne taşıma
            if ("indir" in text_lower or "download" in text_lower) and ("belge" in text_lower or "dokü" in text_lower or "document" in text_lower):
                # Dosya adını bul
                for word in text_lower.split():
                    if "." in word:  # Muhtemelen dosya adı (uzantısı var)
                        source = word
                        print(f"Muhtemel dosya adı: {source}")
                        
                        # Kaynak klasörü belirle (Downloads)
                        source_folder = common_folders.get("downloads", os.path.join(os.path.expanduser("~"), "Downloads"))
                        
                        # Hedef klasörü belirle (Documents)
                        dest_folder = common_folders.get("documents", os.path.join(os.path.expanduser("~"), "Documents"))
                        
                        return self.move_file(os.path.join(source_folder, source), dest_folder, common_folders)
            
            # Diğer taşıma komutları için düzenli ifadeleri deneyelim
            # Basitleştirilmiş regex pattern'ler
            patterns = [
                r'([\w\.]+)\s+dosyasını\s+([\w]+)(?:\'e|\'a|a|e)\s+taşı',  # X dosyasını Y'e taşı
                r'([\w\.]+)(?:\'i|i)\s+([\w]+)(?:\'e|\'a|a|e)\s+taşı',     # X'i Y'e taşı
                r'taşı\s+([\w\.]+)(?:\'i|i)?\s+([\w]+)(?:\'e|\'a|a|e)?'    # taşı X'i Y'e
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    print(f"Pattern eşleşti: {pattern}")
                    source = match.group(1).strip()
                    destination = match.group(2).strip()
                    print(f"Eşleşen kaynak: {source}, hedef: {destination}")
                    return self.move_file(source, destination, common_folders)
        
        # Dosya kopyalama komutu (basitleştirilmiş)
        if "kopyala" in text_lower:
            print("Dosya kopyalama komutu tespit edildi")
            patterns = [
                r'([\w\.]+)\s+dosyasını\s+([\w]+)(?:\'e|\'a|a|e)\s+kopyala',  # X dosyasını Y'e kopyala
                r'([\w\.]+)(?:\'i|i)\s+([\w]+)(?:\'e|\'a|a|e)\s+kopyala',     # X'i Y'e kopyala
                r'kopyala\s+([\w\.]+)(?:\'i|i)?\s+([\w]+)(?:\'e|\'a|a|e)?'    # kopyala X'i Y'e
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    print(f"Pattern eşleşti: {pattern}")
                    source = match.group(1).strip()
                    destination = match.group(2).strip()
                    print(f"Eşleşen kaynak: {source}, hedef: {destination}")
                    return self.copy_file(source, destination, common_folders)
        
        # Dosya silme komutu (basitleştirilmiş)
        if "sil" in text_lower:
            print("Dosya silme komutu tespit edildi")
            patterns = [
                r'([\w\.]+)\s+dosyasını\s+sil',  # X dosyasını sil
                r'([\w\.]+)(?:\'i|i)\s+sil',     # X'i sil
                r'sil\s+([\w\.]+)'               # sil X
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    print(f"Pattern eşleşti: {pattern}")
                    source = match.group(1).strip()
                    print(f"Eşleşen dosya: {source}")
                    return self.delete_file(source, common_folders)
        
        print("Dosya işlemi komutu tespit edilemedi")
        return False  # Dosya işlemi komutu değil
    
    def move_all_files(self, source_dir, dest_dir):
        """Bir klasördeki tüm dosyaları başka bir klasöre taşır"""
        try:
            # Debug mesajları
            print(f"Tüm dosyaları taşıma işlemi başlatıldı")
            print(f"Kaynak klasör: {source_dir}")
            print(f"Hedef klasör: {dest_dir}")
            
            # Bilgi mesajı
            info_message = ChatMessage(f"🔄 Klasör taşıma işlemi: \"{source_dir}\" klasöründeki tüm dosyalar → \"{dest_dir}\"", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            
            # Kaynak klasörün var olup olmadığını kontrol et
            if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
                print(f"Kaynak klasör bulunamadı: {source_dir}")
                not_found = ChatMessage(f"❌ Kaynak klasör bulunamadı: {source_dir}", is_user=False)
                self.messages_layout.addWidget(not_found)
                return True
            
            # Hedef klasörün var olup olmadığını kontrol et
            if not os.path.exists(dest_dir):
                print(f"Hedef klasör bulunamadı, oluşturuluyor: {dest_dir}")
                os.makedirs(dest_dir)
            
            # Klasördeki tüm dosyaları listele
            files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
            
            if not files:
                print(f"Kaynak klasörde dosya bulunamadı: {source_dir}")
                no_files = ChatMessage(f"⚠️ Kaynak klasörde taşınacak dosya bulunamadı: {source_dir}", is_user=False)
                self.messages_layout.addWidget(no_files)
                return True
            
            # Dosyaları taşı
            moved_count = 0
            for file in files:
                source_path = os.path.join(source_dir, file)
                dest_path = os.path.join(dest_dir, file)
                
                # Eğer hedefte aynı isimde dosya varsa, üzerine yazılacak mı diye sor
                if os.path.exists(dest_path):
                    print(f"Hedefte aynı isimde dosya var: {dest_path}")
                    overwrite = QMessageBox.question(
                        self,
                        "Dosya Zaten Var",
                        f"Hedefte aynı isimde dosya var: {file}\nÜzerine yazmak istiyor musunuz?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if overwrite == QMessageBox.No:
                        print(f"Dosya atlandı: {file}")
                        continue
                
                try:
                    print(f"Dosya taşınıyor: {source_path} -> {dest_path}")
                    shutil.move(source_path, dest_path)
                    moved_count += 1
                except Exception as e:
                    print(f"Dosya taşıma hatası ({file}): {str(e)}")
            
            # Başarı mesajı
            success_message = ChatMessage(f"✅ {moved_count} dosya başarıyla taşındı:\n{source_dir} → {dest_dir}", is_user=False)
            self.messages_layout.addWidget(success_message)
            return True
            
        except Exception as e:
            print(f"Çoklu dosya taşıma hatası: {str(e)}")
            error_message = ChatMessage(f"❌ Dosyaları taşırken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
            return True  # Komutu işlenmiş olarak kabul et
    
    def resolve_path(self, path, common_folders):
        """Kullanıcının belirttiği dosya/klasör yolunu çözümler"""
        path = path.strip().lower()
        
        # Eğer 'klasöründeki', 'içindeki' gibi ifadeler varsa, klasör ve dosya adını ayırır
        folder_file_patterns = [
            r'(.*?)\s+klasöründeki\s+(.*)',
            r'(.*?)\s+dizinindeki\s+(.*)',
            r'(.*?)\s+konumundaki\s+(.*)',
            r'(.*?)\s+içindeki\s+(.*)',
            r'(.*?)(?:\'deki|deki)\s+(.*)',
            r'(.*?)(?:\'daki|daki)\s+(.*)',
        ]
        
        for pattern in folder_file_patterns:
            match = re.search(pattern, path)
            if match:
                folder = match.group(1).strip()
                file = match.group(2).strip()
                
                # Klasör yolunu çözümle
                folder_path = None
                if folder in common_folders:
                    folder_path = common_folders[folder]
                elif folder.startswith("c:") or folder.startswith("/"):
                    folder_path = folder  # Tam yol zaten belirtilmiş
                
                if folder_path and file:
                    return os.path.join(folder_path, file)
        
        # Bilinen klasör adlarını kontrol et
        if path in common_folders:
            return common_folders[path]
        
        # Tam yol olarak dön
        return path
    
    def move_file(self, source, destination, common_folders):
        """Dosyayı bir konumdan diğerine taşır"""
        try:
            # Debug mesajları
            print(f"Dosya taşıma işlemi başlatıldı")
            print(f"Kaynak: {source}")
            print(f"Hedef: {destination}")
            
            # Bilgi mesajı
            info_message = ChatMessage(f"🔄 Dosya taşıma işlemi: \"{source}\" → \"{destination}\"", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            
            # Kaynak ve hedef yolları çözümle
            source_path = self.resolve_path(source, common_folders)
            dest_path = self.resolve_path(destination, common_folders)
            
            print(f"Çözümlenen kaynak yolu: {source_path}")
            print(f"Çözümlenen hedef yolu: {dest_path}")
            
            # Eğer hedef bir klasörse, dosya adını koruyarak o klasöre taşı
            if os.path.isdir(dest_path):
                filename = os.path.basename(source_path)
                dest_path = os.path.join(dest_path, filename)
                print(f"Hedef klasör, tam hedef yolu: {dest_path}")
            
            # Kaynak dosyanın var olup olmadığını kontrol et
            if not os.path.exists(source_path):
                print(f"Kaynak dosya bulunamadı: {source_path}")
                not_found = ChatMessage(f"❌ Kaynak dosya bulunamadı: {source_path}", is_user=False)
                self.messages_layout.addWidget(not_found)
                return True
            
            # Dosyayı taşı
            print(f"Dosya taşınıyor: {source_path} -> {dest_path}")
            shutil.move(source_path, dest_path)
            print("Dosya başarıyla taşındı")
            
            # Başarı mesajı
            success_message = ChatMessage(f"✅ Dosya başarıyla taşındı:\n{source_path} → {dest_path}", is_user=False)
            self.messages_layout.addWidget(success_message)
            return True
            
        except Exception as e:
            print(f"Dosya taşıma hatası: {str(e)}")
            error_message = ChatMessage(f"❌ Dosya taşıma işlemi sırasında bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
            return True  # Komutu işlenmiş olarak kabul et
    
    def copy_file(self, source, destination, common_folders):
        """Dosyayı bir konumdan diğerine kopyalar"""
        try:
            # Bilgi mesajı
            info_message = ChatMessage(f"📋 Dosya kopyalama işlemi: \"{source}\" → \"{destination}\"", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            
            # Kaynak ve hedef yolları çözümle
            source_path = self.resolve_path(source, common_folders)
            dest_path = self.resolve_path(destination, common_folders)
            
            # Eğer hedef bir klasörse, dosya adını koruyarak o klasöre kopyala
            if os.path.isdir(dest_path):
                filename = os.path.basename(source_path)
                dest_path = os.path.join(dest_path, filename)
            
            # Kaynak dosyanın var olup olmadığını kontrol et
            if not os.path.exists(source_path):
                not_found = ChatMessage(f"❌ Kaynak dosya bulunamadı: {source_path}", is_user=False)
                self.messages_layout.addWidget(not_found)
                return True
            
            # Dosyayı kopyala
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
            
            # Başarı mesajı
            success_message = ChatMessage(f"✅ Dosya başarıyla kopyalandı:\n{source_path} → {dest_path}", is_user=False)
            self.messages_layout.addWidget(success_message)
            return True
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Dosya kopyalama işlemi sırasında bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
            return True  # Komutu işlenmiş olarak kabul et
    
    def delete_file(self, source, common_folders):
        """Dosyayı siler"""
        try:
            # Bilgi mesajı
            info_message = ChatMessage(f"🗑️ Dosya silme işlemi: \"{source}\"", is_user=False)
            self.messages_layout.addWidget(info_message)
            
            # Otomatik olarak en aşağıya kaydır
            QApplication.processEvents()
            
            # Kaynak yolu çözümle
            source_path = self.resolve_path(source, common_folders)
            
            # Kaynak dosyanın var olup olmadığını kontrol et
            if not os.path.exists(source_path):
                not_found = ChatMessage(f"❌ Silinecek dosya bulunamadı: {source_path}", is_user=False)
                self.messages_layout.addWidget(not_found)
                return True
            
            # Silme işlemi için onay iste
            confirm = QMessageBox.question(
                self,
                "Dosya Silme Onayı",
                f"Bu dosya/klasörü silmek istediğinizden emin misiniz?\n{source_path}",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Dosya veya klasörü sil
                if os.path.isdir(source_path):
                    shutil.rmtree(source_path)
                else:
                    os.remove(source_path)
                
                # Başarı mesajı
                success_message = ChatMessage(f"✅ Dosya başarıyla silindi: {source_path}", is_user=False)
                self.messages_layout.addWidget(success_message)
            else:
                # İptal mesajı
                cancel_message = ChatMessage("❌ Dosya silme işlemi iptal edildi.", is_user=False)
                self.messages_layout.addWidget(cancel_message)
                
            return True
            
        except Exception as e:
            error_message = ChatMessage(f"❌ Dosya silme işlemi sırasında bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
            return True  # Komutu işlenmiş olarak kabul et

    def check_and_run_scheduled_task_command(self, text):
        text_lower = text.lower()
        
        # Hemen bilgisayarı kapatma komutu
        if any(x in text_lower for x in ["pcyi kapat", "pc'yi kapat", "bilgisayarı kapat"]) and not any(x in text_lower for x in ["dakika", "saat"]):
            # Görevi hemen ekle
            self.task_manager.add_immediate_task(
                0,  # Hemen
                "shutdown",
                {"delay": 10}  # 10 saniye uyarı süresi
            )
            
            # Kullanıcıya bilgi ver
            success_msg = ChatMessage(
                "✅ Bilgisayarı kapatıyorum (10 saniye içinde)", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Hemen/kısa süreli görevler için regex
        immediate_shutdown_pattern = r"(\d+)\s+(?:dakika|dk)\s+sonra\s+(?:bilgisayarı|pc'yi|pc yi|bilgisayarımı)\s+(?:kapat|shutdown|kapa)"
        immediate_restart_pattern = r"(\d+)\s+(?:dakika|dk)\s+sonra\s+(?:bilgisayarı|pc'yi|pc yi|bilgisayarımı)\s+(?:yeniden\s+başlat|restart|reset)"
        immediate_reminder_pattern = r"(\d+)\s+(?:dakika|dk)\s+sonra\s+(?:bana)?\s+(.+?)\s+(?:hatırlat|hatırlatır mısın)"
        
        # Hemen/kısa süreli bilgisayarı kapatma görevi
        immediate_shutdown_match = re.search(immediate_shutdown_pattern, text_lower)
        if immediate_shutdown_match:
            delay = int(immediate_shutdown_match.group(1))
            
            # Görevi ekle
            self.task_manager.add_immediate_task(
                delay,
                "shutdown",
                {"delay": 60}  # 60 saniye uyarı süresi
            )
            
            # Kullanıcıya bilgi ver
            success_msg = ChatMessage(
                f"✅ {delay} dakika sonra bilgisayarı kapatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Hemen/kısa süreli bilgisayarı yeniden başlatma görevi
        immediate_restart_match = re.search(immediate_restart_pattern, text_lower)
        if immediate_restart_match:
            delay = int(immediate_restart_match.group(1))
            
            # Görevi ekle
            self.task_manager.add_immediate_task(
                delay,
                "restart",
                {"delay": 60}  # 60 saniye uyarı süresi
            )
            
            # Kullanıcıya bilgi ver
            success_msg = ChatMessage(
                f"✅ {delay} dakika sonra bilgisayarı yeniden başlatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Hemen/kısa süreli hatırlatıcı görevi
        immediate_reminder_match = re.search(immediate_reminder_pattern, text_lower)
        if immediate_reminder_match:
            delay = int(immediate_reminder_match.group(1))
            reminder_message = immediate_reminder_match.group(2).strip()
            
            # Görevi ekle
            self.task_manager.add_immediate_task(
                delay,
                "reminder",
                {"message": f"⏰ HATIRLATICI: {reminder_message}"}
            )
            
            # Kullanıcıya bilgi ver
            success_msg = ChatMessage(
                f"✅ {delay} dakika sonra size '{reminder_message}' hatırlatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True

        # Görev ekleme komutları için regex
        shutdown_pattern = r"(her\s+gün|hafta\s+içi|hafta\s+sonu|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)\s+saat\s+(\d{1,2})[:\.]?(\d{0,2})\s+(?:da|de)?\s+(bilgisayarı|pc'yi|pc yi|bilgisayarımı)\s+(kapat|shutdown|kapa)"
        
        restart_pattern = r"(her\s+gün|hafta\s+içi|hafta\s+sonu|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)\s+saat\s+(\d{1,2})[:\.]?(\d{0,2})\s+(?:da|de)?\s+(bilgisayarı|pc'yi|pc yi|bilgisayarımı)\s+(yeniden\s+başlat|restart|reset)"
        
        reminder_pattern = r"(her\s+gün|hafta\s+içi|hafta\s+sonu|pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)\s+saat\s+(\d{1,2})[:\.]?(\d{0,2})\s+(?:da|de)?\s+(?:bana)?\s+(.+?)\s+(?:hatırlat|hatırlatır mısın)"
        
        # Bilgisayarı kapatma görevi ekle
        shutdown_match = re.search(shutdown_pattern, text_lower)
        if shutdown_match:
            repeat = shutdown_match.group(1).strip()
            hour = int(shutdown_match.group(2))
            minute = int(shutdown_match.group(3)) if shutdown_match.group(3) else 0
            time_str = f"{hour:02d}:{minute:02d}"
            
            # Tekrarlama tipini belirle
            repeat_type = "daily"  # Varsayılan: her gün
            if repeat == "hafta içi":
                repeat_type = "weekdays"
            elif repeat == "hafta sonu":
                repeat_type = "weekends"
            elif repeat in ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]:
                repeat_type = repeat
            
            # Görevi ekle
            task_id = self.task_manager.add_task(
                time_str, 
                "shutdown", 
                {"delay": 60},  # 60 saniye sonra kapat
                repeat_type
            )
            
            # Kullanıcıya bilgi ver
            repeat_msg = {
                "daily": "Her gün",
                "weekdays": "Hafta içi her gün",
                "weekends": "Hafta sonu her gün",
                "pazartesi": "Her Pazartesi",
                "salı": "Her Salı",
                "çarşamba": "Her Çarşamba",
                "perşembe": "Her Perşembe",
                "cuma": "Her Cuma",
                "cumartesi": "Her Cumartesi",
                "pazar": "Her Pazar"
            }.get(repeat_type, repeat_type)
            
            success_msg = ChatMessage(
                f"✅ Zamanlanmış görev eklendi: {repeat_msg} saat {time_str}'de bilgisayarı kapatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Bilgisayarı yeniden başlatma görevi ekle
        restart_match = re.search(restart_pattern, text_lower)
        if restart_match:
            repeat = restart_match.group(1).strip()
            hour = int(restart_match.group(2))
            minute = int(restart_match.group(3)) if restart_match.group(3) else 0
            time_str = f"{hour:02d}:{minute:02d}"
            
            # Tekrarlama tipini belirle
            repeat_type = "daily"  # Varsayılan: her gün
            if repeat == "hafta içi":
                repeat_type = "weekdays"
            elif repeat == "hafta sonu":
                repeat_type = "weekends"
            elif repeat in ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]:
                repeat_type = repeat
            
            # Görevi ekle
            task_id = self.task_manager.add_task(
                time_str, 
                "restart", 
                {"delay": 60},  # 60 saniye sonra yeniden başlat
                repeat_type
            )
            
            # Kullanıcıya bilgi ver
            repeat_msg = {
                "daily": "Her gün",
                "weekdays": "Hafta içi her gün",
                "weekends": "Hafta sonu her gün",
                "pazartesi": "Her Pazartesi",
                "salı": "Her Salı",
                "çarşamba": "Her Çarşamba",
                "perşembe": "Her Perşembe",
                "cuma": "Her Cuma",
                "cumartesi": "Her Cumartesi",
                "pazar": "Her Pazar"
            }.get(repeat_type, repeat_type)
            
            success_msg = ChatMessage(
                f"✅ Zamanlanmış görev eklendi: {repeat_msg} saat {time_str}'de bilgisayarı yeniden başlatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Hatırlatıcı görevi ekle
        reminder_match = re.search(reminder_pattern, text_lower)
        if reminder_match:
            repeat = reminder_match.group(1).strip()
            hour = int(reminder_match.group(2))
            minute = int(reminder_match.group(3)) if reminder_match.group(3) else 0
            reminder_message = reminder_match.group(4).strip()
            time_str = f"{hour:02d}:{minute:02d}"
            
            # Tekrarlama tipini belirle
            repeat_type = "daily"  # Varsayılan: her gün
            if repeat == "hafta içi":
                repeat_type = "weekdays"
            elif repeat == "hafta sonu":
                repeat_type = "weekends"
            elif repeat in ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]:
                repeat_type = repeat
            
            # Görevi ekle
            task_id = self.task_manager.add_task(
                time_str, 
                "reminder", 
                {"message": f"⏰ HATIRLATICI: {reminder_message}"},
                repeat_type
            )
            
            # Kullanıcıya bilgi ver
            repeat_msg = {
                "daily": "Her gün",
                "weekdays": "Hafta içi her gün",
                "weekends": "Hafta sonu her gün",
                "pazartesi": "Her Pazartesi",
                "salı": "Her Salı",
                "çarşamba": "Her Çarşamba",
                "perşembe": "Her Perşembe",
                "cuma": "Her Cuma",
                "cumartesi": "Her Cumartesi",
                "pazar": "Her Pazar"
            }.get(repeat_type, repeat_type)
            
            success_msg = ChatMessage(
                f"✅ Hatırlatıcı eklendi: {repeat_msg} saat {time_str}'de size '{reminder_message}' hatırlatacağım.", 
                is_user=False
            )
            self.messages_layout.addWidget(success_msg)
            return True
        
        # Görev listeleme komutu
        if "görevleri listele" in text_lower or "zamanlanmış görevler" in text_lower or "görevlerimi göster" in text_lower:
            tasks = self.task_manager.tasks
            
            if not tasks:
                no_tasks_msg = ChatMessage("Henüz zamanlanmış görev bulunmuyor.", is_user=False)
                self.messages_layout.addWidget(no_tasks_msg)
            else:
                tasks_text = "📅 Zamanlanmış Görevler:\n\n"
                for i, task in enumerate(tasks):
                    action_name = {
                        "shutdown": "Bilgisayarı Kapat",
                        "restart": "Bilgisayarı Yeniden Başlat",
                        "reminder": "Hatırlatıcı",
                        "run_app": "Uygulama Çalıştır"
                    }.get(task["action"], task["action"])
                    
                    repeat_name = {
                        "daily": "Her gün",
                        "weekdays": "Hafta içi",
                        "weekends": "Hafta sonu",
                        "pazartesi": "Her Pazartesi",
                        "salı": "Her Salı",
                        "çarşamba": "Her Çarşamba",
                        "perşembe": "Her Perşembe",
                        "cuma": "Her Cuma",
                        "cumartesi": "Her Cumartesi",
                        "pazar": "Her Pazar"
                    }.get(task["repeat"], task["repeat"])
                    
                    # Görev detayları
                    details = ""
                    if task["action"] == "reminder":
                        details = f" - \"{task['parameters'].get('message', '')}\""
                    
                    tasks_text += f"{i+1}. {repeat_name} saat {task['time']} - {action_name}{details}\n"
                
                tasks_msg = ChatMessage(tasks_text, is_user=False)
                self.messages_layout.addWidget(tasks_msg)
            return True
        
        # Görev silme komutu
        if "görevi sil" in text_lower or "görevini sil" in text_lower:
            # Görev numarasını bul
            task_num_pattern = r"(\d+)[.\s]*(?:numaralı)?\s+görev"
            task_num_match = re.search(task_num_pattern, text_lower)
            
            if task_num_match:
                task_num = int(task_num_match.group(1))
                task_id = task_num - 1  # Kullanıcı 1'den başlayarak sayıyor, indeks 0'dan
                
                if self.task_manager.delete_task(task_id):
                    success_msg = ChatMessage(f"✅ {task_num} numaralı görev silindi.", is_user=False)
                    self.messages_layout.addWidget(success_msg)
                else:
                    error_msg = ChatMessage(f"❌ {task_num} numaralı görev bulunamadı.", is_user=False)
                    self.messages_layout.addWidget(error_msg)
                return True
        
        return False  # Zamanlanmış görev komutu değil

    def update_discord_status(self, details, state=None):
        """Discord durumunu günceller"""
        if self.rpc:
            try:
                self.rpc.update(
                    details=details,
                    state=state,
                    large_image="tai_logo",  # Discord uygulamanıza yüklediğiniz resmin adı
                    large_text="TAI - Türkçe Yapay Zeka Asistanı",
                    start=int(time.time())  # Aktivite başlangıç zamanı
                )
            except Exception as e:
                print(f"Discord durumu güncellenemedi: {e}")

if __name__ == '__main__':
    # QMessageBox stilini özelleştir
    qss = """
        QMessageBox {
            background-color: #282a36;
            color: white;
            font-family: 'Segoe UI', 'Arial';
        }
        QMessageBox QLabel {
            color: white;
        }
        QMessageBox QPushButton {
            background-color: #6272a4;
            color: white;
            border-radius: 5px;
            padding: 8px 16px;
            min-width: 80px;
        }
        QMessageBox QPushButton:hover {
            background-color: #7282b4;
        }
    """
    
    app = QApplication(sys.argv)
    app.setStyleSheet(qss)  # MessageBox stili uygula
    ex = App()
    ex.show()
    sys.exit(app.exec_())
