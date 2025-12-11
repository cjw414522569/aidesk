import os
import sys
import winreg

class AutostartManager:
    """Windows开机自启管理"""
    
    @staticmethod
    def get_exe_path():
        """获取可执行文件路径"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        return os.path.abspath(sys.argv[0])
    
    @staticmethod
    def is_enabled():
        """检查是否已启用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "AIDesk")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except:
            return False
    
    @staticmethod
    def enable():
        """启用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_SET_VALUE)
            exe_path = AutostartManager.get_exe_path()
            winreg.SetValueEx(key, "AIDesk", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[AutoStart] 启用失败: {e}")
            return False
    
    @staticmethod
    def disable():
        """禁用开机自启"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "AIDesk")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[AutoStart] 禁用失败: {e}")
            return False