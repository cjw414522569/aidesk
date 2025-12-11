import os
import pyautogui
import threading
import time
import pyperclip

class SystemController:
    def __init__(self):
        self.gesture_running = False
        
    def open_app(self, app_name):
        """通过Windows开始菜单搜索功能打开应用"""
        try:
            # 按下Win键打开开始菜单
            pyautogui.press('win')
            # 等待开始菜单打开
            time.sleep(0.5)
            # 将应用名复制到剪贴板
            pyperclip.copy(app_name)
            # 粘贴应用名（使用Ctrl+V）
            pyautogui.hotkey('ctrl', 'v')
            # 等待应用名粘贴完成
            time.sleep(0.5)
            # 按回车键启动应用
            pyautogui.press('enter')
            time.sleep(0.5)
            return f"已启动{app_name}"
        except Exception as e:
            return f"启动{app_name}失败: {str(e)}"
    
    def press_key(self, key):
        pyautogui.press(key)
        return f"已按下{key}键"
    
    def hotkey(self, *keys):
        pyautogui.hotkey(*keys)
        return f"已执行快捷键：{'+'.join(keys)}"
    
    def media_control(self, action):
        actions = {
            "播放": "playpause",
            "暂停": "playpause",
            "下一首": "nexttrack",
            "上一首": "prevtrack",
            "音量增大": "volumeup",
            "音量减小": "volumedown"
        }
        key = actions.get(action)
        if key:
            pyautogui.press(key)
            return f"已执行：{action}"
        return "未知操作"
    
    def start_gesture_control(self):
        return "手势控制功能需要安装mediapipe库（Python 3.13暂不支持）"
    
    def stop_gesture_control(self):
        return "手势控制功能需要安装mediapipe库（Python 3.13暂不支持）"