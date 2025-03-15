import sys
import time
import subprocess  # Paket yükleme için eklendi
import pyautogui
import google.generativeai as genai
from PIL import Image
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
                           QLineEdit, QFileDialog, QTextEdit, QGraphicsDropShadowEffect, 
                           QSizePolicy, QFrame, QScrollArea, QCheckBox, QDialog, QMessageBox)
import threading
import os
import datetime

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
                background-color: #343541;
                color: white;
                font-family: 'Arial';
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #40414f;
                color: white;
                border: 1px solid #565869;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4285f4;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4285f4cc;
            }
            QTextEdit {
                background-color: #40414f;
                color: white;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        
        self.api_key = ""
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Başlık ve açıklama
        title_label = QLabel("Gemini API Anahtarını Girin")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        info_label = QLabel("TAI'yi kullanmak için Google Gemini API anahtarı gereklidir. "
                          "Eğer API anahtarınız yoksa aşağıdaki adımları izleyebilirsiniz.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # API anahtarı alanı
        key_layout = QVBoxLayout()
        key_label = QLabel("API Anahtarı:")
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
        self.ok_button.clicked.connect(self.accept_key)
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("background-color: #f44336;")
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.resize(450, 400)
        
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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Mesaj metni
        self.message = QTextEdit()
        self.message.setReadOnly(True)
        self.message.setPlainText(text)
        self.message.setFrameStyle(QFrame.NoFrame)
        self.message.setMinimumHeight(30)
        self.message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.message.document().setDocumentMargin(2)
        self.message.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Kullanıcı ya da AI mesajı stilini ayarla
        if is_user:
            self.setStyleSheet("""
                QFrame#chatMessage {
                    background-color: #343541;
                    border-top: 1px solid #444654;
                    border-bottom: 1px solid #444654;
                }
                QTextEdit {
                    background-color: transparent;
                    color: white;
                    font-size: 15px;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#chatMessage {
                    background-color: #444654;
                    border-top: 1px solid #343541;
                    border-bottom: 1px solid #343541;
                }
                QTextEdit {
                    background-color: transparent;
                    color: white;
                    font-size: 15px;
                    border: none;
                }
            """)
        
        layout.addWidget(self.message)
        self.setLayout(layout)

class App(QWidget):
    def __init__(self):
        super().__init__()
        
        # API anahtarını sor
        self.get_api_key()
        
        # API anahtarı yoksa uygulamayı kapat
        if not GEMINI_API_KEY:
            sys.exit()
            
        # API anahtarını ayarla
        genai.configure(api_key=GEMINI_API_KEY)

        self.setWindowTitle('TAI - Yapay Zeka Asistanı')
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("""
            QWidget {
                background-color: #343541;
                font-family: 'Arial';
                color: white;
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
        title_frame.setStyleSheet("background-color: #444654; border-bottom: 1px solid #565869;")
        title_layout = QHBoxLayout(title_frame)
        
        title_label = QLabel("TAI - Türkçe Yapay Zeka Asistanı")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        # API Anahtarı değiştirme butonu
        api_button = QPushButton("API Anahtarını Değiştir")
        api_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover {
                color: white;
                text-decoration: underline;
            }
        """)
        api_button.clicked.connect(self.change_api_key)
        title_layout.addWidget(api_button, alignment=Qt.AlignRight)
        
        main_layout.addWidget(title_frame)

        # Mesaj geçmişi alanı
        self.messages_area = QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_area.setFrameStyle(QFrame.NoFrame)
        self.messages_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(0)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.addStretch()
        
        self.messages_area.setWidget(self.messages_container)
        main_layout.addWidget(self.messages_area, 1)

        # Hoşgeldin mesajı
        welcome_message = ChatMessage("Merhaba! Ben TAI, Türkçe yapay zeka asistanınızım. Size nasıl yardımcı olabilirim?", is_user=False)
        self.messages_layout.addWidget(welcome_message)

        # Alt kısım - mesaj gönderme alanı
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: #343541;
                border-top: 1px solid #565869;
                padding: 10px;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_frame)
        
        # Mesaj giriş alanı
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #40414f;
                border-radius: 12px;
                margin: 10px 100px;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Herhangi bir şey sor")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 15px;
                padding: 8px;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        
        send_button = QPushButton()
        send_button.setIcon(self.style().standardIcon(self.style().SP_ArrowRight))
        send_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #565869;
                border-radius: 4px;
            }
        """)
        send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(send_button)
        
        bottom_layout.addWidget(input_frame)
        
        # Kontrol butonları
        control_layout = QHBoxLayout()
        
        self.upload_button = QPushButton("Görsel Yükle")
        self.upload_button.setStyleSheet(self.button_style("#3e8e41"))
        self.upload_button.clicked.connect(self.open_file)
        
        self.analyze_button = QPushButton("Görseli Analiz Et")
        self.analyze_button.setStyleSheet(self.button_style("#f4b400"))
        self.analyze_button.clicked.connect(self.analyze_image_with_ai)
        self.analyze_button.setEnabled(False)  # Başlangıçta devre dışı
        
        self.screenshot_button = QPushButton("Ekran Görüntüsü Al")
        self.screenshot_button.setStyleSheet(self.button_style("#4285f4"))
        self.screenshot_button.clicked.connect(self.take_screenshot)
        
        self.auto_screenshot_checkbox = QCheckBox("Dakikada Bir Ekran Analizi")
        self.auto_screenshot_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
                padding: 8px 16px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.auto_screenshot_checkbox.stateChanged.connect(self.toggle_auto_screenshot)
        
        control_layout.addStretch()
        control_layout.addWidget(self.upload_button)
        control_layout.addWidget(self.analyze_button)
        control_layout.addWidget(self.screenshot_button)
        control_layout.addWidget(self.auto_screenshot_checkbox)
        control_layout.addStretch()
        
        bottom_layout.addLayout(control_layout)
        
        main_layout.addWidget(bottom_frame)
        
        self.setLayout(main_layout)
        
        # Görsel önizleme alanı (başlangıçta gizli)
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setStyleSheet("padding: 10px;")
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
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
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
            
        # Kullanıcı mesajını ekle
        user_message = ChatMessage(user_text, is_user=True)
        self.messages_layout.addWidget(user_message)
        
        # Giriş alanını temizle
        self.chat_input.clear()
        
        # AI yanıtı (normalde burada Gemini API'ye istek atılır)
        self.get_ai_response(user_text)
        
        # Otomatik olarak en aşağıya kaydır
        QApplication.processEvents()
        self.messages_area.verticalScrollBar().setValue(
            self.messages_area.verticalScrollBar().maximum()
        )

    def get_ai_response(self, user_input):
        try:
            response = genai.GenerativeModel("gemini-1.5-flash").generate_content([user_input])
            ai_text = response.text.strip()
            
            # AI mesajını ekle
            ai_message = ChatMessage(ai_text, is_user=False)
            self.messages_layout.addWidget(ai_message)
        except Exception as e:
            error_message = ChatMessage(f"Bir hata oluştu: {str(e)}", is_user=False)
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
            
            self.image_preview.setPixmap(pixmap)
            self.image_preview.show()
            
            # Resim yüklendi mesajı
            message = ChatMessage(f"Görsel yüklendi: {image_path.split('/')[-1]}", is_user=True)
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
            message = ChatMessage("Lütfen önce bir görsel yükleyin!", is_user=False)
            self.messages_layout.addWidget(message)
            return
            
        try:
            # Analiz işlemi başladı mesajı
            self.process_message = ChatMessage("Görsel analiz ediliyor...", is_user=False)
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
                    self.ui_signals.show_error.emit(f"Görsel analiz edilirken bir hata oluştu: {str(e)}", self.process_message)
            
            # Analiz işlemini ayrı bir thread'de başlat
            threading.Thread(target=analyze_thread, daemon=True).start()
            
        except Exception as e:
            error_message = ChatMessage(f"Görsel analiz edilirken bir hata oluştu: {str(e)}", is_user=False)
            self.messages_layout.addWidget(error_message)
    
    def take_screenshot(self):
        """Manuel olarak ekran görüntüsü alma ve analiz etme"""
        try:
            # Bilgi mesajı
            self.info_message = ChatMessage("Ekran görüntüsü alınıyor...", is_user=False)
            self.messages_layout.addWidget(self.info_message)
            
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
            error_message = ChatMessage(f"Ekran görüntüsü alınırken bir hata oluştu: {str(e)}", is_user=False)
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
            error_message = ChatMessage(f"Otomatik ekran görüntüsü alınırken bir hata oluştu: {str(e)}", is_user=False)
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
                    self.ui_signals.show_error.emit(f"Ekran görüntüsü analiz edilirken bir hata oluştu: {str(e)}", info_message)
            
            # Analiz işlemini ayrı bir thread'de başlat
            threading.Thread(target=analyze_thread, daemon=True).start()
            
        except Exception as e:
            error_message = ChatMessage(f"Ekran görüntüsü analiz işlemi başlatılırken bir hata oluştu: {str(e)}", is_user=False)
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())