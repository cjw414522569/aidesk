import sys
import warnings
# 抑制pygame的pkg_resources弃用警告
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")
from services.voice_recognition import VoiceRecognition
from core.ai_core_with_tools import AIWithTools
from gui.gui_qt import run_gui
from services.admin_manager import AdminManager

class AIAssistant:
    def __init__(self):
        self.voice = VoiceRecognition()
        self.ai = AIWithTools()
        self.ai.schedule.start()
    
    def voice_to_text(self):
        result = self.voice.record_audio(5)
        if isinstance(result, str) and ("需要安装" in result or "录音失败" in result):
            return result
        return self.voice.transcribe(result)
    
    def process_command(self, command):
        return self.ai.chat(command)

    def set_speak_callback(self, callback):
        self.ai.set_speak_callback(callback)

if __name__ == "__main__":
    # 只在打包后的exe中检查单实例和管理员权限
    if getattr(sys, 'frozen', False):
        # 检查单实例
        if not AdminManager.check_single_instance():
            print("[启动] 程序已在运行")
            sys.exit(0)
        
        if not AdminManager.is_admin():
            print("[启动] 正在请求管理员权限...")
            if not AdminManager.run_as_admin():
                print("[启动] 提权失败，以普通权限运行")
        else:
            print("[启动] 已获得管理员权限")
    
    assistant = AIAssistant()
    run_gui(assistant)