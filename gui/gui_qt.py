from PyQt5.QtWidgets import (QApplication, QWidget, QMenu, QAction, QTextEdit,
                             QVBoxLayout, QDialog, QPushButton, QLineEdit, QLabel, QFormLayout, QListWidget, QHBoxLayout, QSlider, QColorDialog, QComboBox, QStackedWidget, QFrame, QCalendarWidget, QGridLayout)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QObject, QDate
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QFont, QRegion, QIcon, QKeyEvent, QTextCharFormat
import sys
import threading
import config
from core.ai_core_with_tools import AIWithTools
from core.schedule_manager import ScheduleManager
from services.hotkey_manager import HotkeyManager
from services.wake_word_detector import WakeWordDetector
from services.tts_service import TTSService

def get_theme_colors():
    """根据主题模式返回颜色配置"""
    if config.THEME_MODE == "light":
        return {
            'bg': 'rgba(240, 240, 240, 250)',
            'secondary_bg': 'rgba(255, 255, 255, 200)',
            'text': 'black',
            'border': 'rgba(0, 0, 0, 100)',
            'menu_bg': 'rgba(250, 250, 250, 230)',
            'menu_hover': 'rgba(200, 200, 200, 200)',
        }
    else:  # dark
        return {
            'bg': 'rgba(40, 40, 40, 250)',
            'secondary_bg': 'rgba(60, 60, 60, 200)',
            'text': 'white',
            'border': 'rgba(255, 255, 255, 100)',
            'menu_bg': 'rgba(50, 50, 50, 230)',
            'menu_hover': 'rgba(70, 130, 180, 200)',
        }

class HotkeyEdit(QLineEdit):
    """热键捕获输入框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击后按下热键...")
        self.keys = []
        
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Escape:
            self.clear()
            self.keys = []
            return
        
        # 获取修饰键
        modifiers = event.modifiers()
        key_parts = []
        
        if modifiers & Qt.ControlModifier:
            key_parts.append("ctrl")
        if modifiers & Qt.AltModifier:
            key_parts.append("alt")
        if modifiers & Qt.ShiftModifier:
            key_parts.append("shift")
        
        # 获取主键名称
        key_map = {
            Qt.Key_F1: "f1", Qt.Key_F2: "f2", Qt.Key_F3: "f3", Qt.Key_F4: "f4",
            Qt.Key_F5: "f5", Qt.Key_F6: "f6", Qt.Key_F7: "f7", Qt.Key_F8: "f8",
            Qt.Key_F9: "f9", Qt.Key_F10: "f10", Qt.Key_F11: "f11", Qt.Key_F12: "f12",
        }
        
        if key in key_map:
            key_parts.append(key_map[key])
        elif key >= Qt.Key_A and key <= Qt.Key_Z:
            key_parts.append(chr(key).lower())
        elif key >= Qt.Key_0 and key <= Qt.Key_9:
            key_parts.append(chr(key))
        
        if len(key_parts) > (1 if modifiers else 0):
            hotkey = "+".join(key_parts)
            self.setText(hotkey)
            self.keys = key_parts

class MainApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.tts = TTSService()

    def speak(self, text):
        """播放语音"""
        self.tts.speak(text)

class CircleWidget(QWidget):
    hotkey_voice_signal = pyqtSignal()
    hotkey_chat_signal = pyqtSignal()
    wake_word_signal = pyqtSignal()
    show_response_signal = pyqtSignal(str)
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.dragging = False
        self.offset = QPoint()
        self.is_listening = False
        self.recording_thread = None
        self.schedule_window = None
        self.chat_dialog = None
        self.hotkey_manager = HotkeyManager()
        self.wake_word_detector = WakeWordDetector()
        self.init_ui()
        
        # 连接热键信号
        self.hotkey_voice_signal.connect(self.toggle_voice_recognition)
        self.hotkey_chat_signal.connect(self.toggle_chat_dialog)
        self.wake_word_signal.connect(lambda: self.start_voice_recognition(from_wake_word=True))
        self.show_response_signal.connect(self.show_response)
        
        # 直接传递speak方法给assistant
        app = QApplication.instance()
        if isinstance(app, MainApp):
            self.assistant.set_speak_callback(app.speak)
        
        # 创建并显示日程窗口
        self.schedule_window = ScheduleWindow(self.assistant)
        self.schedule_window.show()
        
        # 注册热键（使用lambda来发射信号）
        self.hotkey_manager.register(
            lambda: self.hotkey_voice_signal.emit(),
            lambda: self.hotkey_chat_signal.emit()
        )
        
        # 启动语音唤醒检测
        self.wake_word_detector.start(lambda: self.wake_word_signal.emit())
        
    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(60, 60)
        
        # 设置圆形区域
        region = QRegion(0, 0, 60, 60, QRegion.Ellipse)
        self.setMask(region)
        
        # 移动到屏幕右下角
        screen = QApplication.desktop().screenGeometry()
        self.move(screen.width() - 80, screen.height() - 80)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制圆形背景，使用配置的颜色
        if self.is_listening:
            r, g, b = map(int, config.THEME_LISTENING_COLOR.split(','))
            gradient = QColor(r, g, b, 220)
        else:
            r, g, b = map(int, config.THEME_PRIMARY_COLOR.split(','))
            gradient = QColor(r, g, b, 220)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawEllipse(2, 2, 56, 56)
        
        # 绘制中心点
        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(25, 25, 10, 10)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()
            self.press_pos = event.globalPos()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(self.mapToParent(event.pos() - self.offset))
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 判断是点击还是拖动
            if hasattr(self, 'press_pos'):
                move_distance = (event.globalPos() - self.press_pos).manhattanLength()
                if move_distance < 5:  # 移动距离小于5像素视为点击
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == Qt.ControlModifier:
                        self.show_text_input()
                    else:
                        if self.is_listening:
                            self.stop_voice_recognition()
                        else:
                            self.start_voice_recognition()
            self.dragging = False
    
    def toggle_voice_recognition(self):
        """切换语音识别状态"""
        if self.is_listening:
            self.stop_voice_recognition()
        else:
            self.start_voice_recognition()
    
    def start_voice_recognition(self, from_wake_word=False):
        if self.is_listening:
            print("[DEBUG] 已经在录音中，跳过")
            return
        
        # 如果是唤醒词触发，先播放回复
        if from_wake_word:
            app = QApplication.instance()
            if isinstance(app, MainApp):
                app.speak(config.WAKE_WORD_RESPONSE)
            
        self.is_listening = True
        self.update()
        
        def record_and_process():
            # 暂停唤醒词检测
            self.wake_word_detector.pause()
            
            text = self.assistant.voice_to_text()
            
            # 确保状态重置
            self.is_listening = False
            self.update()
            
            # 恢复唤醒词检测
            self.wake_word_detector.resume()
            
            print(f"[DEBUG] 语音识别结果: '{text}'")
            
            if text and "需要安装" not in text and "录音失败" not in text and "识别失败" not in text:
                print(f"[用户消息] {text}")
                response = self.assistant.process_command(text)
                print(f"[AI回复] {response}")
                
                # 使用自定义通知显示AI回复（5秒后自动关闭）
                try:
                    import subprocess
                    import sys
                    import os
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    script_path = os.path.join(project_root, 'services', 'custom_notification.py')
                    subprocess.Popen([sys.executable, script_path, response, "auto_close"])
                except Exception as e:
                    print(f"[通知错误] 显示AI回复通知失败: {e}")
                
                # 播报AI回复
                app = QApplication.instance()
                if isinstance(app, MainApp):
                    app.speak(response)
            else:
                print(f"[DEBUG] 语音识别被跳过，text='{text}'")
        
        self.recording_thread = threading.Thread(target=record_and_process, daemon=True)
        self.recording_thread.start()
    
    def stop_voice_recognition(self):
        self.is_listening = False
        self.update()
    
    def toggle_chat_dialog(self):
        """切换AI对话框显示状态"""
        if self.chat_dialog and self.chat_dialog.isVisible():
            self.chat_dialog.close()
        else:
            self.show_text_input()
    
    def show_text_input(self):
        if self.chat_dialog is None or not self.chat_dialog.isVisible():
            self.chat_dialog = ChatDialog(self.assistant, self)
            self.chat_dialog.show()
            # 延迟聚焦到输入框，确保窗口完全显示并激活
            QTimer.singleShot(200, self.focus_input)
        else:
            self.chat_dialog.raise_()
            self.chat_dialog.activateWindow()
            # 延迟聚焦到输入框
            QTimer.singleShot(200, self.focus_input)
    
    def focus_input(self):
        """聚焦到输入框"""
        if self.chat_dialog and self.chat_dialog.input_edit:
            self.chat_dialog.input_edit.setFocus()
            self.chat_dialog.input_edit.selectAll()  # 选中所有文本，方便直接输入
    
    def show_response(self, text):
        dialog = ResponseDialog(text, self)
        dialog.exec_()
    
    def show_context_menu(self, pos):
        colors = get_theme_colors()
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {colors['menu_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 25px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: {colors['menu_hover']};
            }}
        """)
        
        text_action = QAction("文本输入", self)
        text_action.triggered.connect(self.show_text_input)
        
        voice_action = QAction("语音识别", self)
        voice_action.triggered.connect(self.start_voice_recognition)
        
        schedule_action = QAction("显示/隐藏日程", self)
        schedule_action.triggered.connect(self.toggle_schedule_window)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.quit)
        
        menu.addAction(text_action)
        menu.addAction(voice_action)
        menu.addAction(schedule_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        
        menu.exec_(self.mapToGlobal(pos))
    
    def toggle_schedule_window(self):
        if self.schedule_window:
            if self.schedule_window.isVisible():
                self.schedule_window.hide()
            else:
                self.schedule_window.show()
                self.schedule_window.refresh_schedules()
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()


class ChatDialog(QWidget):
    response_signal = pyqtSignal(str)
    
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.response_signal.connect(self.append_response)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(screen.width() // 2 - 300, screen.height() // 2 - 250, 600, 500)
        
        # 主容器
        self.container = QWidget()
        self.update_background_opacity()
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 100, 100, 150);
                border-radius: 15px;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        # 顶部布局（关闭按钮）
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        layout.addLayout(top_layout)
        
        # 对话显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_display.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_display.setStyleSheet("QTextEdit { background: transparent; border: none; }")
        self.chat_display.setAttribute(Qt.WA_TranslucentBackground)
        self.chat_display.setHtml("")  # 清空初始内容
        layout.addWidget(self.chat_display, 1)
        
        # 半透明输入框
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入消息...")
        colors = get_theme_colors()
        self.input_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 30);
                color: {colors['text']};
                border: 2px solid rgba(255, 255, 255, 50);
                border-radius: 20px;
                padding: 12px 20px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid rgba(70, 130, 180, 150);
            }}
        """)
        self.input_edit.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_edit)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
    
    def update_background_opacity(self):
        """更新背景透明度"""
        opacity = int(config.DIALOG_OPACITY * 2.55)  # 转换为0-255
        self.container.setStyleSheet(f"background-color: rgba(50, 50, 50, {opacity}); border-radius: 15px;")
    
    def send_message(self):
        from datetime import datetime
        text = self.input_edit.text().strip()
        if not text:
            return
        
        self.input_edit.clear()
        time_str = datetime.now().strftime("%H:%M")
        
        # 用户消息：右对齐，蓝色气泡
        self.chat_display.append(f'''
            <div style="text-align:right; margin:15px 0;">
                <div style="background: linear-gradient(135deg, rgba(70,130,180,220), rgba(100,149,237,220));
                            padding:12px 18px; border-radius:18px 18px 4px 18px;
                            color:white; font-size:15px; line-height:1.5;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                            display:inline-block; text-align:left; max-width:70%;">
                    {text}
                </div>
                <div style="color:rgba(255,255,255,100); font-size:11px; margin-top:4px;">
                    {time_str}
                </div>
            </div>
        ''')
        
        def process():
            response = self.assistant.process_command(text)
            self.response_signal.emit(response)
        
        threading.Thread(target=process, daemon=True).start()
    
    def append_response(self, response):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M")
        
        # AI消息：左对齐，灰色气泡
        self.chat_display.append(f'''
            <div style="text-align:left; margin:15px 0;">
                <div style="background: linear-gradient(135deg, rgba(80,80,80,200), rgba(60,60,60,200));
                            padding:12px 18px; border-radius:18px 18px 18px 4px;
                            color:white; font-size:15px; line-height:1.5;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                            display:inline-block; text-align:left; max-width:70%;">
                    {response}
                </div>
                <div style="color:rgba(255,255,255,100); font-size:11px; margin-top:4px;">
                    AI · {time_str}
                </div>
            </div>
        ''')
        
        # 如果启用了AI对话框TTS输出，播放语音
        if config.TTS_CHAT_DIALOG_ENABLED:
            app = QApplication.instance()
            if isinstance(app, MainApp):
                app.speak(response)
    
    def showEvent(self, event):
        """窗口显示时自动聚焦到输入框"""
        super().showEvent(event)
        # 延迟聚焦，确保窗口完全显示和激活
        QTimer.singleShot(300, self.ensure_focus)
    
    def ensure_focus(self):
        """确保输入框获得焦点"""
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus(Qt.OtherFocusReason)
        self.input_edit.activateWindow()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

class ResponseDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("AI助手回复")
        self.setFixedSize(500, 400)
        colors = get_theme_colors()
        # 设置对话框透明度
        self.setWindowOpacity(config.DIALOG_OPACITY / 100.0)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg']};
            }}
            QTextEdit {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 15px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: rgba(70, 130, 180, 200);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(100, 160, 210, 200);
            }}
        """)
        
        layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(self.text)
        layout.addWidget(self.text_edit)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.setLayout(layout)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("设置")
        self.setFixedSize(900, 650)
        colors = get_theme_colors()
        
        # 设置窗口居中显示
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg']};
            }}
            QLabel {{
                color: {colors['text']};
                font-size: 14px;
            }}
            QLineEdit {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                min-height: 30px;
            }}
            QPushButton {{
                background-color: rgba(70, 130, 180, 200);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px 24px;
                font-size: 14px;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background-color: rgba(100, 160, 210, 200);
            }}
            QComboBox {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                min-height: 30px;
            }}
            QSlider {{
                min-height: 30px;
            }}
            QListWidget {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 5px;
                margin: 2px;
            }}
            QListWidget::item:selected {{
                background-color: rgba(70, 130, 180, 200);
            }}
            QListWidget::item:hover {{
                background-color: rgba(70, 130, 180, 100);
            }}
        """)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 左侧导航栏
        left_panel = QWidget()
        left_panel.setFixedWidth(200)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 导航标题
        nav_title = QLabel("设置分类")
        nav_title.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                color: {colors['text']};
            }}
        """)
        left_layout.addWidget(nav_title)
        
        # 导航列表
        self.nav_list = QListWidget()
        self.nav_list.addItem("API配置")
        self.nav_list.addItem("模型配置")
        self.nav_list.addItem("天气配置")
        self.nav_list.addItem("PushPlus配置")
        self.nav_list.addItem("主题设置")
        self.nav_list.addItem("透明度设置")
        self.nav_list.addItem("热键设置")
        self.nav_list.addItem("语音唤醒")
        self.nav_list.addItem("音频设置")
        self.nav_list.addItem("TTS设置")
        self.nav_list.addItem("系统设置")
        self.nav_list.setCurrentRow(0)
        self.nav_list.itemClicked.connect(self.switch_page)
        left_layout.addWidget(self.nav_list)
        
        # 右侧内容区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容标题
        self.content_title = QLabel("API配置")
        self.content_title.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
                color: {colors['text']};
                border-bottom: 2px solid {colors['border']};
            }}
        """)
        right_layout.addWidget(self.content_title)
        
        # 堆叠窗口管理不同设置页面
        self.stacked_widget = QStackedWidget()
        
        # API配置页面
        api_page = self.create_api_page()
        self.stacked_widget.addWidget(api_page)
        
        # 模型配置页面
        model_page = self.create_model_page()
        self.stacked_widget.addWidget(model_page)
        
        # 天气配置页面
        weather_page = self.create_weather_page()
        self.stacked_widget.addWidget(weather_page)
        
        # PushPlus配置页面
        pushplus_page = self.create_pushplus_page()
        self.stacked_widget.addWidget(pushplus_page)
        
        # 主题设置页面
        theme_page = self.create_theme_page()
        self.stacked_widget.addWidget(theme_page)
        
        # 透明度设置页面
        opacity_page = self.create_opacity_page()
        self.stacked_widget.addWidget(opacity_page)
        
        # 热键设置页面
        hotkey_page = self.create_hotkey_page()
        self.stacked_widget.addWidget(hotkey_page)
        
        # 语音唤醒设置页面
        wake_word_page = self.create_wake_word_page()
        self.stacked_widget.addWidget(wake_word_page)
        
        # 音频设置页面
        audio_page = self.create_audio_page()
        self.stacked_widget.addWidget(audio_page)
        
        # TTS设置页面
        tts_page = self.create_tts_page()
        self.stacked_widget.addWidget(tts_page)
        
        # 系统设置页面
        system_page = self.create_system_page()
        self.stacked_widget.addWidget(system_page)
        
        right_layout.addWidget(self.stacked_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        right_layout.addLayout(btn_layout)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)
    
    def create_api_page(self):
        """创建API配置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setText(config.SILICONFLOW_BASE_URL)
        self.api_url_input.setMinimumWidth(400)
        layout.addRow("API Base URL:", self.api_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setText(config.SILICONFLOW_API_KEY)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setMinimumWidth(400)
        layout.addRow("SiliconFlow API Key:", self.api_key_input)
        
        page.setLayout(layout)
        return page
    
    def create_model_page(self):
        """创建模型配置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.voice_model_input = QLineEdit()
        self.voice_model_input.setText(config.VOICE_MODEL)
        self.voice_model_input.setMinimumWidth(400)
        layout.addRow("语音模型:", self.voice_model_input)
        
        self.ocr_model_input = QLineEdit()
        self.ocr_model_input.setText(config.OCR_MODEL)
        self.ocr_model_input.setMinimumWidth(400)
        layout.addRow("OCR模型:", self.ocr_model_input)
        
        self.ai_model_input = QLineEdit()
        self.ai_model_input.setText(config.AI_MODEL)
        self.ai_model_input.setMinimumWidth(400)
        layout.addRow("AI模型:", self.ai_model_input)
        
        page.setLayout(layout)
        return page
    
    def create_weather_page(self):
        """创建天气配置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.weather_url_input = QLineEdit()
        self.weather_url_input.setText(config.WEATHER_API_URL)
        self.weather_url_input.setMinimumWidth(400)
        layout.addRow("天气API URL:", self.weather_url_input)

        self.weather_key_input = QLineEdit()
        self.weather_key_input.setText(config.WEATHER_API_KEY)
        self.weather_key_input.setEchoMode(QLineEdit.Password)
        self.weather_key_input.setMinimumWidth(400)
        layout.addRow("天气API Key:", self.weather_key_input)
        
        page.setLayout(layout)
        return page
    
    def create_theme_page(self):
        """创建主题设置页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # 颜色设置
        color_group = QFrame()
        color_group.setFrameStyle(QFrame.Box)
        color_group.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {get_theme_colors()['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        color_layout = QVBoxLayout(color_group)
        
        color_title = QLabel("主题颜色")
        color_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        color_layout.addWidget(color_title)
        
        color_control = QHBoxLayout()
        color_control.addWidget(QLabel("主题颜色:"))
        self.primary_color_btn = QPushButton("选择主色调")
        self.primary_color_btn.setFixedWidth(120)
        r, g, b = map(int, config.THEME_PRIMARY_COLOR.split(','))
        self.primary_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: white;
                border: 2px solid rgba(255, 255, 255, 100);
            }}
        """)
        self.primary_color_btn.clicked.connect(lambda: self.choose_color('primary'))
        color_control.addWidget(self.primary_color_btn)
        
        self.listening_color_btn = QPushButton("选择录音颜色")
        self.listening_color_btn.setFixedWidth(120)
        r, g, b = map(int, config.THEME_LISTENING_COLOR.split(','))
        self.listening_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: white;
                border: 2px solid rgba(255, 255, 255, 100);
            }}
        """)
        self.listening_color_btn.clicked.connect(lambda: self.choose_color('listening'))
        color_control.addWidget(self.listening_color_btn)
        color_control.addStretch()
        color_layout.addLayout(color_control)
        
        layout.addWidget(color_group)
        
        # 主题模式设置
        mode_group = QFrame()
        mode_group.setFrameStyle(QFrame.Box)
        mode_group.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {get_theme_colors()['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        mode_layout = QVBoxLayout(mode_group)
        
        mode_title = QLabel("界面主题")
        mode_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        mode_layout.addWidget(mode_title)
        
        mode_control = QHBoxLayout()
        mode_control.addWidget(QLabel("界面主题:"))
        self.theme_mode_combo = QComboBox()
        self.theme_mode_combo.addItems(["暗色主题", "亮色主题"])
        self.theme_mode_combo.setCurrentIndex(0 if config.THEME_MODE == "dark" else 1)
        self.theme_mode_combo.setFixedWidth(200)
        self.update_theme_combo_style()
        mode_control.addWidget(self.theme_mode_combo)
        mode_control.addStretch()
        mode_layout.addLayout(mode_control)
        
        layout.addWidget(mode_group)
        layout.addStretch()
        
        page.setLayout(layout)
        return page
    
    def create_opacity_page(self):
        """创建透明度设置页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # 透明度设置
        opacity_group = QFrame()
        opacity_group.setFrameStyle(QFrame.Box)
        opacity_group.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {get_theme_colors()['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        opacity_layout = QVBoxLayout(opacity_group)
        
        opacity_title = QLabel("窗口透明度")
        opacity_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        opacity_layout.addWidget(opacity_title)
        
        # 日程窗口透明度
        schedule_opacity_control = QHBoxLayout()
        self.schedule_opacity_slider = QSlider(Qt.Horizontal)
        self.schedule_opacity_slider.setMinimum(0)
        self.schedule_opacity_slider.setMaximum(100)
        self.schedule_opacity_slider.setValue(config.SCHEDULE_WINDOW_OPACITY)
        self.schedule_opacity_slider.setFixedWidth(300)
        self.schedule_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(100, 100, 100, 200);
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: rgba(70, 130, 180, 200);
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        self.schedule_opacity_label = QLabel(f"{config.SCHEDULE_WINDOW_OPACITY}%")
        self.schedule_opacity_label.setFixedWidth(50)
        self.schedule_opacity_slider.valueChanged.connect(lambda v: self.schedule_opacity_label.setText(f"{v}%"))
        
        schedule_opacity_control.addWidget(QLabel("日程窗口透明度:"))
        schedule_opacity_control.addWidget(self.schedule_opacity_slider)
        schedule_opacity_control.addWidget(self.schedule_opacity_label)
        schedule_opacity_control.addStretch()
        opacity_layout.addLayout(schedule_opacity_control)
        
        
        # 设置窗口透明度
        settings_opacity_control = QHBoxLayout()
        self.settings_opacity_slider = QSlider(Qt.Horizontal)
        self.settings_opacity_slider.setMinimum(0)
        self.settings_opacity_slider.setMaximum(100)
        self.settings_opacity_slider.setValue(config.SETTINGS_WINDOW_OPACITY)
        self.settings_opacity_slider.setFixedWidth(300)
        self.settings_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(100, 100, 100, 200);
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: rgba(70, 130, 180, 200);
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        self.settings_opacity_label = QLabel(f"{config.SETTINGS_WINDOW_OPACITY}%")
        self.settings_opacity_label.setFixedWidth(50)
        self.settings_opacity_slider.valueChanged.connect(lambda v: self.settings_opacity_label.setText(f"{v}%"))
        
        settings_opacity_control.addWidget(QLabel("设置窗口透明度:"))
        settings_opacity_control.addWidget(self.settings_opacity_slider)
        settings_opacity_control.addWidget(self.settings_opacity_label)
        settings_opacity_control.addStretch()
        opacity_layout.addLayout(settings_opacity_control)
        
        # 对话框透明度
        dialog_opacity_control = QHBoxLayout()
        self.dialog_opacity_slider = QSlider(Qt.Horizontal)
        self.dialog_opacity_slider.setMinimum(0)
        self.dialog_opacity_slider.setMaximum(100)
        self.dialog_opacity_slider.setValue(config.DIALOG_OPACITY)
        self.dialog_opacity_slider.setFixedWidth(300)
        self.dialog_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(100, 100, 100, 200);
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: rgba(70, 130, 180, 200);
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        self.dialog_opacity_label = QLabel(f"{config.DIALOG_OPACITY}%")
        self.dialog_opacity_label.setFixedWidth(50)
        self.dialog_opacity_slider.valueChanged.connect(lambda v: self.dialog_opacity_label.setText(f"{v}%"))
        
        dialog_opacity_control.addWidget(QLabel("对话框透明度:"))
        dialog_opacity_control.addWidget(self.dialog_opacity_slider)
        dialog_opacity_control.addWidget(self.dialog_opacity_label)
        dialog_opacity_control.addStretch()
        opacity_layout.addLayout(dialog_opacity_control)
        
        layout.addWidget(opacity_group)
        layout.addStretch()
        
        page.setLayout(layout)
        return page
    
    def create_pushplus_page(self):
        """创建PushPlus配置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.pushplus_token_input = QLineEdit()
        self.pushplus_token_input.setText(config.PUSHPLUS_TOKEN)
        self.pushplus_token_input.setEchoMode(QLineEdit.Password)
        self.pushplus_token_input.setMinimumWidth(400)
        layout.addRow("PushPlus Token:", self.pushplus_token_input)
        
        # 测试按钮
        test_btn = QPushButton("测试通知")
        test_btn.setFixedWidth(120)
        test_btn.clicked.connect(self.test_pushplus)
        layout.addRow("", test_btn)
        
        page.setLayout(layout)
        return page
    
    def create_hotkey_page(self):
        """创建热键设置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        self.hotkey_voice_input = HotkeyEdit()
        self.hotkey_voice_input.setText(config.HOTKEY_VOICE)
        self.hotkey_voice_input.setMinimumWidth(400)
        layout.addRow("语音控制热键:", self.hotkey_voice_input)
        
        self.hotkey_chat_input = HotkeyEdit()
        self.hotkey_chat_input.setText(config.HOTKEY_CHAT)
        self.hotkey_chat_input.setMinimumWidth(400)
        layout.addRow("AI对话框热键:", self.hotkey_chat_input)
        
        hint_label = QLabel("提示: 点击输入框后按下热键，支持组合键（如Ctrl+Alt+F1）")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addRow("", hint_label)
        
        page.setLayout(layout)
        return page
    
    def create_wake_word_page(self):
        """创建语音唤醒设置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        # 启用开关
        from PyQt5.QtWidgets import QCheckBox
        self.wake_word_enabled_check = QCheckBox()
        self.wake_word_enabled_check.setChecked(config.WAKE_WORD_ENABLED)
        layout.addRow("启用语音唤醒:", self.wake_word_enabled_check)
        
        # 唤醒词
        self.wake_word_input = QLineEdit()
        self.wake_word_input.setText(config.WAKE_WORD)
        self.wake_word_input.setMinimumWidth(400)
        layout.addRow("唤醒词:", self.wake_word_input)
        
        # 唤醒词回复
        self.wake_word_response_input = QLineEdit()
        self.wake_word_response_input.setText(config.WAKE_WORD_RESPONSE)
        self.wake_word_response_input.setMinimumWidth(400)
        layout.addRow("唤醒词回复:", self.wake_word_response_input)
        
        # 模型路径
        self.vosk_model_input = QLineEdit()
        self.vosk_model_input.setText(config.VOSK_MODEL_PATH)
        self.vosk_model_input.setMinimumWidth(400)
        layout.addRow("Vosk模型路径:", self.vosk_model_input)
        
        hint_label = QLabel("提示: 说出唤醒词后将自动启动语音识别")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addRow("", hint_label)
        
        page.setLayout(layout)
        return page
    
    def create_audio_page(self):
        """创建音频设置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        # 麦克风选择
        self.microphone_combo = QComboBox()
        self.microphone_combo.setMinimumWidth(400)
        
        # 获取麦克风列表
        from services.voice_recognition import VoiceRecognition
        devices = VoiceRecognition.get_microphone_list()
        
        # 添加默认选项
        self.microphone_combo.addItem("默认麦克风", None)
        
        # 添加所有麦克风设备
        for device in devices:
            self.microphone_combo.addItem(device['name'], device['index'])
        
        # 设置当前选中的麦克风
        if config.MICROPHONE_DEVICE_INDEX is not None:
            for i in range(self.microphone_combo.count()):
                if self.microphone_combo.itemData(i) == config.MICROPHONE_DEVICE_INDEX:
                    self.microphone_combo.setCurrentIndex(i)
                    break
        
        layout.addRow("麦克风设备:", self.microphone_combo)
        
        # 测试按钮
        test_layout = QHBoxLayout()
        test_mic_btn = QPushButton("测试麦克风")
        test_mic_btn.setFixedWidth(120)
        test_mic_btn.clicked.connect(self.test_microphone)
        test_layout.addWidget(test_mic_btn)
        
        test_wake_btn = QPushButton("测试唤醒词")
        test_wake_btn.setFixedWidth(120)
        test_wake_btn.clicked.connect(self.test_wake_word)
        test_layout.addWidget(test_wake_btn)
        
        test_api_btn = QPushButton("测试语音API")
        test_api_btn.setFixedWidth(120)
        test_api_btn.clicked.connect(self.test_voice_api)
        test_layout.addWidget(test_api_btn)
        test_layout.addStretch()
        
        layout.addRow("", test_layout)
        
        # 静音时长设置
        silence_layout = QHBoxLayout()
        self.silence_duration_input = QLineEdit()
        self.silence_duration_input.setText(str(config.SILENCE_DURATION))
        self.silence_duration_input.setFixedWidth(100)
        silence_layout.addWidget(self.silence_duration_input)
        silence_layout.addWidget(QLabel("秒"))
        silence_layout.addStretch()
        layout.addRow("静音停止时长:", silence_layout)
        
        hint_label = QLabel("提示: 检测到指定时长的静音后自动停止录音")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addRow("", hint_label)
        
        page.setLayout(layout)
        return page
    
    def create_tts_page(self):
        """创建TTS设置页面"""
        page = QWidget()
        layout = QFormLayout()
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignRight)
        
        # 音色选择
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setMinimumWidth(400)
        voices = [
            ("中文女声 (晓晓)", "zh-CN-XiaoxiaoNeural"),
            ("中文男声 (云希)", "zh-CN-YunxiNeural"),
            ("中文男声 (云扬)", "zh-CN-YunyangNeural"),
            ("中文女声 (晓伊)", "zh-CN-XiaoyiNeural"),
            ("中文男声 (云健)", "zh-CN-YunjianNeural"),
            ("中文女声 (晓辰)", "zh-CN-XiaochenNeural"),
            ("中文女声 (晓涵)", "zh-CN-XiaohanNeural"),
            ("中文女声 (晓梦)", "zh-CN-XiaomengNeural"),
            ("中文女声 (晓墨)", "zh-CN-XiaomoNeural"),
            ("中文女声 (晓秋)", "zh-CN-XiaoqiuNeural"),
            ("中文女声 (晓睿)", "zh-CN-XiaoruiNeural"),
            ("中文女声 (晓双)", "zh-CN-XiaoshuangNeural"),
            ("中文女声 (晓萱)", "zh-CN-XiaoxuanNeural"),
            ("中文女声 (晓颜)", "zh-CN-XiaoyanNeural"),
            ("中文女声 (晓悠)", "zh-CN-XiaoyouNeural"),
            ("中文女声 (晓甄)", "zh-CN-XiaozhenNeural"),
            ("中文男声 (云枫)", "zh-CN-YunfengNeural"),
            ("中文男声 (云皓)", "zh-CN-YunhaoNeural"),
            ("中文男声 (云夏)", "zh-CN-YunxiaNeural"),
            ("中文男声 (云野)", "zh-CN-YunyeNeural"),
            ("中文男声 (云泽)", "zh-CN-YunzeNeural"),
            ("英文女声 (Jenny)", "en-US-JennyNeural"),
            ("英文男声 (Guy)", "en-US-GuyNeural"),
            ("英文女声 (Aria)", "en-US-AriaNeural"),
            ("英文男声 (Davis)", "en-US-DavisNeural"),
        ]
        
        for name, value in voices:
            self.tts_voice_combo.addItem(name, value)
        
        # 设置当前选中的音色
        for i in range(self.tts_voice_combo.count()):
            if self.tts_voice_combo.itemData(i) == config.TTS_VOICE:
                self.tts_voice_combo.setCurrentIndex(i)
                break
        
        layout.addRow("音色:", self.tts_voice_combo)
        
        # 语速设置
        speed_layout = QHBoxLayout()
        self.tts_speed_input = QLineEdit()
        self.tts_speed_input.setText(str(config.TTS_SPEED))
        self.tts_speed_input.setFixedWidth(100)
        speed_layout.addWidget(self.tts_speed_input)
        speed_layout.addWidget(QLabel("(0.25-2.0)"))
        speed_layout.addStretch()
        layout.addRow("语速:", speed_layout)
        
        # 音调设置
        pitch_layout = QHBoxLayout()
        self.tts_pitch_input = QLineEdit()
        self.tts_pitch_input.setText(str(config.TTS_PITCH))
        self.tts_pitch_input.setFixedWidth(100)
        pitch_layout.addWidget(self.tts_pitch_input)
        pitch_layout.addStretch()
        layout.addRow("音调:", pitch_layout)
        
        # 流式响应
        from PyQt5.QtWidgets import QCheckBox
        self.tts_stream_check = QCheckBox("启用流式响应（降低长文本延迟）")
        self.tts_stream_check.setChecked(config.TTS_STREAM)
        layout.addRow("", self.tts_stream_check)
        
        # AI对话框TTS输出
        self.tts_chat_dialog_check = QCheckBox("AI对话框启用语音输出")
        self.tts_chat_dialog_check.setChecked(config.TTS_CHAT_DIALOG_ENABLED)
        layout.addRow("", self.tts_chat_dialog_check)
        
        # 文本清理选项
        layout.addRow("", QLabel(""))  # 空行
        cleanup_title = QLabel("文本清理选项:")
        cleanup_title.setStyleSheet("font-weight: bold;")
        layout.addRow("", cleanup_title)
        
        self.tts_remove_markdown_check = QCheckBox("移除 Markdown 标记")
        self.tts_remove_markdown_check.setChecked(config.TTS_REMOVE_MARKDOWN)
        layout.addRow("", self.tts_remove_markdown_check)
        
        self.tts_remove_emoji_check = QCheckBox("移除 Emoji 表情")
        self.tts_remove_emoji_check.setChecked(config.TTS_REMOVE_EMOJI)
        layout.addRow("", self.tts_remove_emoji_check)
        
        self.tts_remove_url_check = QCheckBox("移除 URL 链接")
        self.tts_remove_url_check.setChecked(config.TTS_REMOVE_URL)
        layout.addRow("", self.tts_remove_url_check)
        
        self.tts_remove_whitespace_check = QCheckBox("移除多余空白/换行")
        self.tts_remove_whitespace_check.setChecked(config.TTS_REMOVE_WHITESPACE)
        layout.addRow("", self.tts_remove_whitespace_check)
        
        self.tts_remove_reference_check = QCheckBox("移除引用标记数字 [1] [2]")
        self.tts_remove_reference_check.setChecked(config.TTS_REMOVE_REFERENCE)
        layout.addRow("", self.tts_remove_reference_check)
        
        hint_label = QLabel("提示: 文本清理选项实时生效，无需重启")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addRow("", hint_label)
        
        page.setLayout(layout)
        return page
    
    def create_system_page(self):
        """创建系统设置页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # 开机自启设置
        autostart_group = QFrame()
        autostart_group.setFrameStyle(QFrame.Box)
        autostart_group.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {get_theme_colors()['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        autostart_layout = QVBoxLayout(autostart_group)
        
        autostart_title = QLabel("开机自启")
        autostart_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        autostart_layout.addWidget(autostart_title)
        
        from PyQt5.QtWidgets import QCheckBox
        autostart_control = QHBoxLayout()
        self.autostart_check = QCheckBox("开机时自动启动应用")
        
        # 检查当前状态
        from services.autostart_manager import AutostartManager
        self.autostart_check.setChecked(AutostartManager.is_enabled())
        
        autostart_control.addWidget(self.autostart_check)
        autostart_control.addStretch()
        autostart_layout.addLayout(autostart_control)
        
        hint_label = QLabel("提示: 启用后应用将在Windows启动时自动运行")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        autostart_layout.addWidget(hint_label)
        
        layout.addWidget(autostart_group)
        
        # 提醒设置
        reminder_group = QFrame()
        reminder_group.setFrameStyle(QFrame.Box)
        reminder_group.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {get_theme_colors()['border']};
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        reminder_layout = QVBoxLayout(reminder_group)
        
        reminder_title = QLabel("提醒设置")
        reminder_title.setStyleSheet("font-weight: bold; font-size: 15px;")
        reminder_layout.addWidget(reminder_title)
        
        # 重复提醒次数
        repeat_count_layout = QHBoxLayout()
        repeat_count_layout.addWidget(QLabel("重复提醒次数:"))
        self.reminder_repeat_count_input = QLineEdit()
        self.reminder_repeat_count_input.setText(str(config.REMINDER_REPEAT_COUNT))
        self.reminder_repeat_count_input.setFixedWidth(100)
        repeat_count_layout.addWidget(self.reminder_repeat_count_input)
        repeat_count_layout.addWidget(QLabel("次"))
        repeat_count_layout.addStretch()
        reminder_layout.addLayout(repeat_count_layout)
        
        # 重复提醒间隔
        repeat_interval_layout = QHBoxLayout()
        repeat_interval_layout.addWidget(QLabel("重复提醒间隔:"))
        self.reminder_repeat_interval_input = QLineEdit()
        self.reminder_repeat_interval_input.setText(str(config.REMINDER_REPEAT_INTERVAL))
        self.reminder_repeat_interval_input.setFixedWidth(100)
        repeat_interval_layout.addWidget(self.reminder_repeat_interval_input)
        repeat_interval_layout.addWidget(QLabel("秒"))
        repeat_interval_layout.addStretch()
        reminder_layout.addLayout(repeat_interval_layout)
        
        reminder_hint = QLabel("提示: 设置为1次表示只提醒一次，大于1次将按间隔重复提醒")
        reminder_hint.setStyleSheet("color: gray; font-size: 12px;")
        reminder_layout.addWidget(reminder_hint)
        
        layout.addWidget(reminder_group)
        layout.addStretch()
        
        page.setLayout(layout)
        return page
    
    def test_microphone(self):
        """测试麦克风声音"""
        from PyQt5.QtWidgets import QMessageBox, QProgressDialog
        from PyQt5.QtCore import QThread
        import time
        
        # 临时保存当前麦克风设置
        old_device = config.MICROPHONE_DEVICE_INDEX
        config.MICROPHONE_DEVICE_INDEX = self.microphone_combo.currentData()
        
        try:
            import pyaudio
            import numpy as np
            
            p = pyaudio.PyAudio()
            device_index = config.MICROPHONE_DEVICE_INDEX
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000,
                          input=True, frames_per_buffer=1024,
                          input_device_index=device_index)
            
            # 创建进度对话框
            progress = QProgressDialog("正在检测麦克风声音...\n请对着麦克风说话", "停止", 0, 30, self)
            progress.setWindowTitle("麦克风测试")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            volumes = []
            for i in range(30):  # 测试3秒
                if progress.wasCanceled():
                    break
                data = stream.read(1024)
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                volumes.append(volume)
                progress.setValue(i)
                QApplication.processEvents()
                time.sleep(0.1)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            progress.close()
            
            if volumes:
                avg_volume = np.mean(volumes)
                max_volume = np.max(volumes)
                
                result = f"麦克风测试结果:\n\n"
                result += f"平均音量: {avg_volume:.0f}\n"
                result += f"最大音量: {max_volume:.0f}\n\n"
                
                if max_volume < 100:
                    result += "⚠️ 音量过低，请检查麦克风设置"
                elif max_volume < 500:
                    result += "✓ 音量正常"
                else:
                    result += "✓ 音量良好"
                
                QMessageBox.information(self, "麦克风测试", result)
        except Exception as e:
            QMessageBox.warning(self, "测试失败", f"麦克风测试失败: {str(e)}")
        finally:
            # 恢复原来的设置
            config.MICROPHONE_DEVICE_INDEX = old_device
    
    def test_wake_word(self):
        """测试唤醒词检测"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 临时保存当前麦克风设置
        old_device = config.MICROPHONE_DEVICE_INDEX
        config.MICROPHONE_DEVICE_INDEX = self.microphone_combo.currentData()
        
        try:
            from services.wake_word_detector import WakeWordDetector
            import os
            
            if not os.path.exists(config.VOSK_MODEL_PATH):
                QMessageBox.warning(self, "测试失败", f"Vosk模型不存在: {config.VOSK_MODEL_PATH}")
                return
            
            result_text = []
            
            def callback():
                result_text.append(f"✓ 检测到唤醒词: {config.WAKE_WORD}")
            
            detector = WakeWordDetector()
            
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("测试唤醒词")
            msg.setText(f"正在测试唤醒词检测...\n\n请说出唤醒词: {config.WAKE_WORD}\n\n测试将持续10秒")
            msg.setStandardButtons(QMessageBox.Cancel)
            msg.show()
            
            detector.start(callback)
            
            # 等待10秒
            import time
            for i in range(100):
                if not msg.isVisible():
                    break
                time.sleep(0.1)
                QApplication.processEvents()
            
            detector.stop()
            msg.close()
            
            if result_text:
                QMessageBox.information(self, "测试成功", "\n".join(result_text))
            else:
                QMessageBox.information(self, "测试结果", "未检测到唤醒词\n\n请确保:\n1. 麦克风工作正常\n2. 说话声音足够大\n3. 唤醒词发音清晰")
        
        except Exception as e:
            QMessageBox.warning(self, "测试失败", f"唤醒词测试失败: {str(e)}")
        finally:
            config.MICROPHONE_DEVICE_INDEX = old_device
    
    def test_voice_api(self):
        """测试语音识别API"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 临时保存当前麦克风设置
        old_device = config.MICROPHONE_DEVICE_INDEX
        config.MICROPHONE_DEVICE_INDEX = self.microphone_combo.currentData()
        
        self.test_cancelled = False
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("测试语音API")
        msg.setText("正在录音...\n\n请说话，系统将自动检测静音并停止")
        msg.setStandardButtons(QMessageBox.Cancel)
        msg.buttonClicked.connect(lambda: setattr(self, 'test_cancelled', True))
        msg.show()
        
        def test_in_thread():
            try:
                if self.test_cancelled:
                    return ("cancelled", "")
                
                from services.voice_recognition import VoiceRecognition
                voice = VoiceRecognition()
                audio_file = voice.record_audio()
                
                if self.test_cancelled:
                    return ("cancelled", "")
                
                if isinstance(audio_file, str) and ("需要安装" in audio_file or "录音失败" in audio_file):
                    return ("error", audio_file)
                
                text = voice.transcribe(audio_file)
                
                if text and "识别失败" not in text:
                    return ("success", text)
                else:
                    return ("error", text)
            except Exception as e:
                return ("error", str(e))
        
        def on_complete(result):
            if not msg.isVisible():
                config.MICROPHONE_DEVICE_INDEX = old_device
                return
            
            msg.close()
            config.MICROPHONE_DEVICE_INDEX = old_device
            
            status, text = result
            if status == "cancelled":
                return
            elif status == "success":
                QMessageBox.information(self, "测试成功", f"识别结果:\n\n{text}")
            else:
                QMessageBox.warning(self, "测试失败", f"语音API测试失败:\n\n{text}")
        
        # 在后台线程执行
        import threading
        def run():
            result = test_in_thread()
            QTimer.singleShot(0, lambda: on_complete(result))
        
        threading.Thread(target=run, daemon=True).start()
    
    def test_pushplus(self):
        """测试PushPlus通知"""
        from services.pushplus_service import PushPlusService
        pushplus = PushPlusService()
        success = pushplus.test_connection()
        
        from PyQt5.QtWidgets import QMessageBox
        if success:
            QMessageBox.information(self, "测试成功", "PushPlus通知测试成功！")
        else:
            QMessageBox.warning(self, "测试失败", "PushPlus通知测试失败，请检查Token配置")
    
    def switch_page(self, item):
        """切换设置页面"""
        index = self.nav_list.row(item)
        self.stacked_widget.setCurrentIndex(index)
        
        # 更新标题
        titles = ["API配置", "模型配置", "天气配置", "PushPlus配置", "主题设置", "透明度设置", "热键设置", "语音唤醒", "音频设置", "TTS设置", "系统设置"]
        self.content_title.setText(titles[index])
        
        # 如果切换到主题设置页面，更新下拉框样式
        if index == 4:  # 主题设置页面
            self.update_theme_combo_style()
    
    def update_theme_combo_style(self):
        """根据当前主题模式更新下拉框样式"""
        colors = get_theme_colors()
        if config.THEME_MODE == "light":
            arrow_color = "black"
            border_color = "rgba(0, 0, 0, 100)"
        else:
            arrow_color = "white"
            border_color = "rgba(255, 255, 255, 100)"
        
        self.theme_mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 8px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {arrow_color};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                selection-background-color: rgba(70, 130, 180, 200);
            }}
        """)
    
    def choose_color(self, color_type):
        """选择颜色"""
        if color_type == 'primary':
            r, g, b = map(int, config.THEME_PRIMARY_COLOR.split(','))
        else:
            r, g, b = map(int, config.THEME_LISTENING_COLOR.split(','))
        
        initial_color = QColor(r, g, b)
        color = QColorDialog.getColor(initial_color, self, "选择颜色")
        
        if color.isValid():
            rgb_str = f"{color.red()},{color.green()},{color.blue()}"
            if color_type == 'primary':
                config.THEME_PRIMARY_COLOR = rgb_str
                self.primary_color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                        color: white;
                        border: 2px solid rgba(255, 255, 255, 100);
                    }}
                """)
            else:
                config.THEME_LISTENING_COLOR = rgb_str
                self.listening_color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                        color: white;
                        border: 2px solid rgba(255, 255, 255, 100);
                    }}
                """)
    
    def save_settings(self):
        # 更新config模块的值
        config.SILICONFLOW_API_KEY = self.api_key_input.text()
        config.SILICONFLOW_BASE_URL = self.api_url_input.text()
        config.VOICE_MODEL = self.voice_model_input.text()
        config.OCR_MODEL = self.ocr_model_input.text()
        config.AI_MODEL = self.ai_model_input.text()
        config.WEATHER_API_KEY = self.weather_key_input.text()
        config.WEATHER_API_URL = self.weather_url_input.text()
        config.PUSHPLUS_TOKEN = self.pushplus_token_input.text()
        
        # 更新透明度设置
        config.SCHEDULE_WINDOW_OPACITY = self.schedule_opacity_slider.value()
        config.SETTINGS_WINDOW_OPACITY = self.settings_opacity_slider.value()
        config.DIALOG_OPACITY = self.dialog_opacity_slider.value()
        
        # 更新热键设置
        config.HOTKEY_VOICE = self.hotkey_voice_input.text()
        config.HOTKEY_CHAT = self.hotkey_chat_input.text()
        
        # 更新语音唤醒设置
        config.WAKE_WORD_ENABLED = self.wake_word_enabled_check.isChecked()
        config.WAKE_WORD = self.wake_word_input.text()
        config.WAKE_WORD_RESPONSE = self.wake_word_response_input.text()
        config.VOSK_MODEL_PATH = self.vosk_model_input.text()
        
        # 更新麦克风设置
        config.MICROPHONE_DEVICE_INDEX = self.microphone_combo.currentData()
        try:
            config.SILENCE_DURATION = float(self.silence_duration_input.text())
        except ValueError:
            config.SILENCE_DURATION = 3.5
        
        # 更新主题模式
        old_theme = config.THEME_MODE
        config.THEME_MODE = "dark" if self.theme_mode_combo.currentIndex() == 0 else "light"
        
        # 如果主题模式改变，更新下拉框样式
        if old_theme != config.THEME_MODE:
            self.update_theme_combo_style()
        
        # 更新TTS设置
        config.TTS_VOICE = self.tts_voice_combo.currentData()
        try:
            config.TTS_SPEED = float(self.tts_speed_input.text())
            if config.TTS_SPEED < 0.25:
                config.TTS_SPEED = 0.25
            elif config.TTS_SPEED > 2.0:
                config.TTS_SPEED = 2.0
        except ValueError:
            config.TTS_SPEED = 1.0
        
        try:
            config.TTS_PITCH = float(self.tts_pitch_input.text())
        except ValueError:
            config.TTS_PITCH = 1.0
        
        config.TTS_STREAM = self.tts_stream_check.isChecked()
        config.TTS_CHAT_DIALOG_ENABLED = self.tts_chat_dialog_check.isChecked()
        config.TTS_REMOVE_MARKDOWN = self.tts_remove_markdown_check.isChecked()
        config.TTS_REMOVE_EMOJI = self.tts_remove_emoji_check.isChecked()
        config.TTS_REMOVE_URL = self.tts_remove_url_check.isChecked()
        config.TTS_REMOVE_WHITESPACE = self.tts_remove_whitespace_check.isChecked()
        config.TTS_REMOVE_REFERENCE = self.tts_remove_reference_check.isChecked()
        
        # 更新开机自启设置
        from services.autostart_manager import AutostartManager
        if self.autostart_check.isChecked():
            AutostartManager.enable()
        else:
            AutostartManager.disable()
        
        # 保存到config.py文件
        config_content = f'''import os

# SiliconFlow API配置
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "{config.SILICONFLOW_API_KEY}")
SILICONFLOW_BASE_URL = "{config.SILICONFLOW_BASE_URL}"

# 模型配置
VOICE_MODEL = "{config.VOICE_MODEL}"
OCR_MODEL = "{config.OCR_MODEL}"
AI_MODEL = "{config.AI_MODEL}"

# 天气API配置
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "{config.WEATHER_API_KEY}")
WEATHER_API_URL = "{config.WEATHER_API_URL}"

# PushPlus通知配置
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "{config.PUSHPLUS_TOKEN}")

# 日程数据库文件
SCHEDULE_DB = "schedules.db"

# 日程窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
SCHEDULE_WINDOW_OPACITY = {config.SCHEDULE_WINDOW_OPACITY}

# 全局窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
GLOBAL_WINDOW_OPACITY = {config.GLOBAL_WINDOW_OPACITY}

# 设置窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
SETTINGS_WINDOW_OPACITY = {config.SETTINGS_WINDOW_OPACITY}

# 对话框透明度 (0-100, 0为完全透明, 100为完全不透明)
DIALOG_OPACITY = {config.DIALOG_OPACITY}

# 主题颜色配置 (RGB格式)
THEME_PRIMARY_COLOR = "{config.THEME_PRIMARY_COLOR}"  # 主色调 (默认: 钢蓝色)
THEME_LISTENING_COLOR = "{config.THEME_LISTENING_COLOR}"  # 录音状态颜色 (默认: 红色)

# 界面主题模式 (dark/light)
THEME_MODE = "{config.THEME_MODE}"

# 热键配置
HOTKEY_VOICE = "{config.HOTKEY_VOICE}"  # 语音控制热键
HOTKEY_CHAT = "{config.HOTKEY_CHAT}"   # AI对话框热键

# 语音唤醒配置
WAKE_WORD = "{config.WAKE_WORD}"  # 唤醒词
WAKE_WORD_ENABLED = {config.WAKE_WORD_ENABLED}  # 是否启用语音唤醒
WAKE_WORD_RESPONSE = "{config.WAKE_WORD_RESPONSE}"  # 唤醒词回复语句
VOSK_MODEL_PATH = "{config.VOSK_MODEL_PATH}"  # Vosk模型路径

# 麦克风设备配置
MICROPHONE_DEVICE_INDEX = {config.MICROPHONE_DEVICE_INDEX}  # None表示使用默认麦克风，否则为设备索引
SILENCE_DURATION = {config.SILENCE_DURATION}  # 静音多少秒后自动停止录音

# 系统设置
AUTOSTART_ENABLED = False  # 开机自启（此配置仅用于显示，实际状态从注册表读取)

# TTS API配置
TTS_API_URL = "{config.TTS_API_URL}"
TTS_API_KEY = "{config.TTS_API_KEY}"
TTS_VOICE = "{config.TTS_VOICE}"  # 音色
TTS_SPEED = {config.TTS_SPEED}  # 语速 (0.25-2.0)
TTS_PITCH = {config.TTS_PITCH}  # 音调
TTS_STREAM = {config.TTS_STREAM}  # 是否使用流式响应
TTS_REMOVE_MARKDOWN = {config.TTS_REMOVE_MARKDOWN}  # 移除Markdown
TTS_REMOVE_EMOJI = {config.TTS_REMOVE_EMOJI}  # 移除Emoji
TTS_REMOVE_URL = {config.TTS_REMOVE_URL}  # 移除URL
TTS_REMOVE_WHITESPACE = {config.TTS_REMOVE_WHITESPACE}  # 移除所有空白/换行
TTS_REMOVE_REFERENCE = {config.TTS_REMOVE_REFERENCE}  # 移除引用标记数字
TTS_CHAT_DIALOG_ENABLED = {config.TTS_CHAT_DIALOG_ENABLED}  # AI对话框是否启用TTS语音输出

# 提醒设置
REMINDER_REPEAT_COUNT = {config.REMINDER_REPEAT_COUNT}  # 重复提醒次数（1表示只提醒一次）
REMINDER_REPEAT_INTERVAL = {config.REMINDER_REPEAT_INTERVAL}  # 重复提醒间隔（秒）
'''
        
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # 更新所有窗口
        app = QApplication.instance()
        for widget in app.topLevelWidgets():
            if isinstance(widget, ScheduleWindow):
                widget.setWindowOpacity(config.SCHEDULE_WINDOW_OPACITY / 100.0)
                if hasattr(widget, 'apply_theme'):
                    widget.apply_theme()
            elif isinstance(widget, CircleWidget):
                widget.setWindowOpacity(config.GLOBAL_WINDOW_OPACITY / 100.0)
                widget.update()
        
        # 应用设置窗口透明度
        self.setWindowOpacity(config.SETTINGS_WINDOW_OPACITY / 100.0)
        
        # 更新所有ChatDialog的背景透明度
        for widget in app.topLevelWidgets():
            if isinstance(widget, ChatDialog):
                widget.update_background_opacity()
        
        # 不关闭窗口，显示保存成功提示
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("保存成功")
        msg.setText("设置已保存成功！")
        msg.setInformativeText("热键和语音唤醒设置需要重启应用后生效。")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

class ScheduleWindow(QWidget):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.show_history = False  # 是否显示历史日程
        self.view_mode = 'list'  # 'list' 或 'calendar'
        self.selected_date = None  # 日历模式下选中的日期
        self.init_ui()
        
        # 定时刷新日程列表
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_schedules)
        self.refresh_timer.start(5000)  # 每5秒刷新一次
        
        self.refresh_schedules()
    
    def init_ui(self):
        self.setWindowTitle("日程列表")
        # 移除WindowStaysOnTopHint，使窗口位于最底层
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 400)
        
        # 设置窗口透明度
        opacity = config.SCHEDULE_WINDOW_OPACITY / 100.0
        self.setWindowOpacity(opacity)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        container = QWidget()
        colors = get_theme_colors()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['bg']};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(container)
        
        # 标题栏 - 集成按钮
        title_layout = QHBoxLayout()
        self.title_label = QLabel("📅 日程列表")
        colors = get_theme_colors()
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }}
        """)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        # 直接在标题栏添加按钮
        self.view_btn = QPushButton("日历")
        self.view_btn.setFixedSize(60, 30)
        self.view_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 180, 100, 220);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(130, 210, 130, 230);
            }
            QPushButton:pressed {
                background-color: rgba(150, 230, 150, 240);
            }
        """)
        self.view_btn.clicked.connect(self.toggle_view_mode)
        title_layout.addWidget(self.view_btn)
        
        self.history_btn = QPushButton("历史")
        self.history_btn.setFixedSize(60, 30)
        self.history_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(70, 130, 180, 220);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(100, 160, 210, 230);
            }
            QPushButton:pressed {
                background-color: rgba(120, 180, 220, 240);
            }
        """)
        self.history_btn.clicked.connect(self.toggle_history)
        title_layout.addWidget(self.history_btn)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(50, 50, 50, 200);
                color: {colors['text']};
                border: none;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 100, 100, 150);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 120, 120, 180);
            }}
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        
        layout.addLayout(title_layout)
        
        # 堆叠窗口用于切换列表和日历视图
        self.stacked_widget = QStackedWidget()
        
        # 日程列表视图
        self.schedule_list = QListWidget()
        colors = get_theme_colors()
        self.schedule_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {colors['border']};
            }}
            QListWidget::item:selected {{
                background-color: rgba(70, 130, 180, 150);
            }}
        """)
        self.stacked_widget.addWidget(self.schedule_list)
        
        # 日历视图
        self.calendar_widget = QCalendarWidget()
        # 根据主题设置日历样式
        if config.THEME_MODE == "dark":
            calendar_text_color = "white"
            calendar_bg = colors['secondary_bg']
            header_color = "rgba(200, 200, 200, 255)"
        else:
            calendar_text_color = "black"
            calendar_bg = colors['secondary_bg']
            header_color = "rgba(50, 50, 50, 255)"
            
        self.calendar_widget.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {calendar_bg};
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {colors['secondary_bg']};
                color: {calendar_text_color};
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: {colors['secondary_bg']};
                color: {calendar_text_color};
                selection-background-color: rgba(70, 130, 180, 180);
                selection-color: white;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {colors['secondary_bg']};
            }}
            QCalendarWidget QToolButton {{
                color: {colors['text']};
                background-color: {colors['secondary_bg']};
                border: none;
                border-radius: 3px;
                padding: 5px;
                margin: 2px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: rgba(70, 130, 180, 150);
            }}
            QCalendarWidget QMenu {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                selection-background-color: rgba(70, 130, 180, 150);
            }}
            QCalendarWidget QTableView {{
                background-color: {colors['secondary_bg']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {calendar_text_color};
                background-color: {colors['secondary_bg']};
                selection-background-color: rgba(70, 130, 180, 180);
                selection-color: white;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: rgba(150, 150, 150, 150);
            }}
            /* 周一到周日的表头 */
            QCalendarWidget QWidget {{
                color: {header_color};
            }}
        """)
        self.calendar_widget.clicked.connect(self.on_date_selected)
        self.calendar_widget.currentPageChanged.connect(self.on_month_changed)
        self.stacked_widget.addWidget(self.calendar_widget)
        
        layout.addWidget(self.stacked_widget)
        
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        
        # 定位到屏幕右下角
        screen = QApplication.desktop().screenGeometry()
        self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 100)
    
    def update_button_positions(self):
        """更新所有按钮位置"""
        # 关闭按钮
        btn_x = self.x() + self.width() - 40
        btn_y = self.y() + 10
        self.close_btn_window.move(btn_x, btn_y)
        
        # 历史按钮
        history_x = self.x() + self.width() - 110
        history_y = self.y() + 12
        self.history_btn_window.move(history_x, history_y)
        
        # 视图切换按钮
        view_x = self.x() + self.width() - 180
        view_y = self.y() + 12
        self.view_btn_window.move(view_x, view_y)
    
    def moveEvent(self, event):
        """窗口移动时更新按钮位置"""
        super().moveEvent(event)
        if hasattr(self, 'close_btn_window'):
            self.update_button_positions()
    
    def hide_both(self):
        """隐藏窗口和所有按钮"""
        self.hide()
        self.close_btn_window.hide()
        self.history_btn_window.hide()
        self.view_btn_window.hide()
    
    def show(self):
        """显示窗口和所有按钮"""
        super().show()
        if hasattr(self, 'close_btn_window'):
            self.update_button_positions()
            self.close_btn_window.show()
            self.history_btn_window.show()
            self.view_btn_window.show()
    
    def hide(self):
        """隐藏窗口和所有按钮"""
        super().hide()
        if hasattr(self, 'close_btn_window'):
            self.close_btn_window.hide()
            self.history_btn_window.hide()
            self.view_btn_window.hide()
    
    def toggle_view_mode(self):
        """切换视图模式"""
        if self.view_mode == 'list':
            self.view_mode = 'calendar'
            self.view_btn.setText("列表")
            self.title_label.setText("📅 日历视图")
            self.stacked_widget.setCurrentIndex(1)
            self.history_btn.hide()
            self.highlight_dates_with_schedules()
        else:
            self.view_mode = 'list'
            self.view_btn.setText("日历")
            self.title_label.setText("📅 日程列表")
            self.stacked_widget.setCurrentIndex(0)
            self.history_btn.show()
            self.selected_date = None
            self.show_history = False
            self.history_btn.setText("历史")
            self.refresh_schedules()
    
    def on_date_selected(self, date):
        """日历日期被选中"""
        self.selected_date = date.toString('yyyy-MM-dd')
        self.view_mode = 'list'
        self.view_btn.setText("日历")
        self.show_history = False
        self.history_btn.setText("历史")
        self.title_label.setText(f"📅 {self.selected_date} 日程")
        self.stacked_widget.setCurrentIndex(0)
        self.history_btn.show()
        self.refresh_schedules()
    
    def on_month_changed(self, year, month):
        """月份改变时重新高亮日期"""
        self.highlight_dates_with_schedules()
    
    def toggle_history(self):
        """切换显示历史日程"""
        self.show_history = not self.show_history
        self.selected_date = None
        if self.show_history:
            self.history_btn.setText("今天")
            self.title_label.setText("📅 历史日程")
        else:
            self.history_btn.setText("历史")
            self.title_label.setText("📅 日程列表")
        self.refresh_schedules()
    
    def highlight_dates_with_schedules(self):
        """高亮显示有日程的日期"""
        try:
            # 获取当月所有日程
            current_date = self.calendar_widget.selectedDate()
            year = current_date.year()
            month = current_date.month()
            
            # 获取当月所有日程
            conn = __import__('sqlite3').connect(self.assistant.ai.schedule.db_path)
            cursor = conn.cursor()
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1}-01-01"
            else:
                end_date = f"{year}-{month+1:02d}-01"
            
            cursor.execute('SELECT DISTINCT DATE(datetime) FROM schedules WHERE datetime >= ? AND datetime < ?', (start_date, end_date))
            schedule_dates = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # 设置有日程的日期格式
            for date_str in schedule_dates:
                year, month, day = map(int, date_str.split('-'))
                date = QDate(year, month, day)
                
                # 创建格式
                format = QTextCharFormat()
                format.setBackground(QBrush(QColor(70, 130, 180, 100)))  # 半透明蓝色背景
                format.setForeground(QBrush(QColor(255, 255, 255)))  # 白色文字
                format.setFontWeight(QFont.Bold)
                
                self.calendar_widget.setDateTextFormat(date, format)
        except Exception as e:
            print(f"[Calendar] 高亮日期失败: {e}")
    
    def refresh_schedules(self):
        self.schedule_list.clear()
        
        if self.selected_date:
            # 显示选中日期的日程
            schedules = self.assistant.ai.schedule.load_schedules(date_filter=self.selected_date)
            
            if not schedules:
                self.schedule_list.addItem(f"📝 {self.selected_date} 无日程")
            else:
                for schedule in schedules:
                    datetime_str = schedule['datetime']
                    task = schedule['task']
                    repeat_type = schedule.get('repeat_type', 'once')
                    repeat_icon = {'once': '', 'daily': '🔁每日', 'weekly': '🔁每周', 'monthly': '🔁每月', 'yearly': '🔁每年'}.get(repeat_type, '')
                    self.schedule_list.addItem(f"⏰ {datetime_str}\n   {task} {repeat_icon}")
        elif self.show_history:
            # 显示所有历史日程（已过期的）
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = __import__('sqlite3').connect(self.assistant.ai.schedule.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT datetime, task FROM schedules WHERE datetime < ? ORDER BY datetime DESC LIMIT 20', (now,))
            schedules = [{"datetime": row[0], "task": row[1]} for row in cursor.fetchall()]
            conn.close()
            
            if not schedules:
                self.schedule_list.addItem("📝 暂无历史日程")
            else:
                for schedule in schedules:
                    datetime_str = schedule['datetime']
                    task = schedule['task']
                    repeat_type = schedule.get('repeat_type', 'once')
                    repeat_icon = {'once': '', 'daily': '🔁每日', 'weekly': '🔁每周', 'monthly': '🔁每月', 'yearly': '🔁每年'}.get(repeat_type, '')
                    self.schedule_list.addItem(f"✓ {datetime_str}\n   {task} {repeat_icon}")
        else:
            # 只显示今天的日程
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            schedules = self.assistant.ai.schedule.load_schedules(date_filter=today)
            
            if not schedules:
                self.schedule_list.addItem("📝 今天暂无日程")
            else:
                for schedule in schedules:
                    datetime_str = schedule['datetime']
                    task = schedule['task']
                    repeat_type = schedule.get('repeat_type', 'once')
                    repeat_icon = {'once': '', 'daily': '🔁每日', 'weekly': '🔁每周', 'monthly': '🔁每月', 'yearly': '🔁每年'}.get(repeat_type, '')
                    self.schedule_list.addItem(f"⏰ {datetime_str}\n   {task} {repeat_icon}")
    
    def apply_theme(self):
        """应用主题颜色"""
        colors = get_theme_colors()
        r, g, b = map(int, config.THEME_PRIMARY_COLOR.split(','))
        self.schedule_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {colors['secondary_bg']};
                color: {colors['text']};
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {colors['border']};
            }}
            QListWidget::item:selected {{
                background-color: rgba({r}, {g}, {b}, 150);
            }}
        """)

def run_gui(assistant):
    app = MainApp(sys.argv)
    window = CircleWidget(assistant)
    window.show()
    sys.exit(app.exec_())
