import keyboard
import config

class HotkeyManager:
    def __init__(self):
        self.registered = False
        
    def register(self, voice_callback, chat_callback):
        """注册热键"""
        if self.registered:
            self.unregister()
        
        try:
            keyboard.add_hotkey(config.HOTKEY_VOICE, voice_callback)
            keyboard.add_hotkey(config.HOTKEY_CHAT, chat_callback)
            self.registered = True
            print(f"[热键] 已注册: {config.HOTKEY_VOICE}=语音, {config.HOTKEY_CHAT}=对话")
        except Exception as e:
            print(f"[热键错误] {e}")
    
    def unregister(self):
        """注销热键"""
        if self.registered:
            try:
                keyboard.unhook_all_hotkeys()
                self.registered = False
            except:
                pass