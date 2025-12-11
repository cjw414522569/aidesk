import os
import sys

# 获取应用程序的基础路径（支持打包后的exe）
def get_base_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

# SiliconFlow API配置
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "sk-*******************")
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"

# 模型配置
VOICE_MODEL = "FunAudioLLM/SenseVoiceSmall"
OCR_MODEL = "deepseek-ai/DeepSeek-OCR"
AI_MODEL = "Qwen/Qwen3-32B"

# 天气API配置
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "-*******************")
WEATHER_API_URL = "https://p96tufjwcb.re.qweatherapi.com/v7"

# PushPlus通知配置
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "*******************")

# 日程数据库文件
SCHEDULE_DB = "schedules.db"

# 日程窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
SCHEDULE_WINDOW_OPACITY = 81

# 全局窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
GLOBAL_WINDOW_OPACITY = 90

# 设置窗口透明度 (0-100, 0为完全透明, 100为完全不透明)
SETTINGS_WINDOW_OPACITY = 86

# 对话框透明度 (0-100, 0为完全透明, 100为完全不透明)
DIALOG_OPACITY = 24

# 主题颜色配置 (RGB格式)
THEME_PRIMARY_COLOR = "25,174,255"  # 主色调 (默认: 钢蓝色)
THEME_LISTENING_COLOR = "255,100,100"  # 录音状态颜色 (默认: 红色)

# 界面主题模式 (dark/light)
THEME_MODE = "dark"

# 热键配置
HOTKEY_VOICE = "ctrl+1"  # 语音控制热键
HOTKEY_CHAT = "ctrl+2"   # AI对话框热键

# 语音唤醒配置
WAKE_WORD = "助理助理"  # 唤醒词
WAKE_WORD_ENABLED = True  # 是否启用语音唤醒
WAKE_WORD_RESPONSE = "我在"  # 唤醒词回复语句
VOSK_MODEL_PATH = os.path.join(BASE_PATH, "vosk-model-small-cn-0.22")  # Vosk模型路径

# 麦克风设备配置
MICROPHONE_DEVICE_INDEX = None  # None表示使用默认麦克风，否则为设备索引
SILENCE_DURATION = 2.0  # 静音多少秒后自动停止录音

# 系统设置
AUTOSTART_ENABLED = False  # 开机自启（此配置仅用于显示，实际状态从注册表读取)

# TTS API配置
TTS_API_URL = "https://tts.*******************.cn/api/v1/audio/speech"
TTS_API_KEY = "123456789"
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 音色
TTS_SPEED = 1.0  # 语速 (0.25-2.0)
TTS_PITCH = 1.0  # 音调
TTS_STREAM = True  # 是否使用流式响应
TTS_REMOVE_MARKDOWN = True  # 移除Markdown
TTS_REMOVE_EMOJI = True  # 移除Emoji
TTS_REMOVE_URL = True  # 移除URL
TTS_REMOVE_WHITESPACE = True  # 移除所有空白/换行
TTS_REMOVE_REFERENCE = True  # 移除引用标记数字
TTS_CHAT_DIALOG_ENABLED = True  # AI对话框是否启用TTS语音输出

# 提醒设置
REMINDER_REPEAT_COUNT = 1  # 重复提醒次数（1表示只提醒一次）
REMINDER_REPEAT_INTERVAL = 60  # 重复提醒间隔（秒）
