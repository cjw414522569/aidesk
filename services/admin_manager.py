import sys
import ctypes
import os
from win32event import CreateMutex
from win32api import GetLastError
from winerror import ERROR_ALREADY_EXISTS

class AdminManager:
    """Windows管理员权限管理"""
    
    mutex = None
    
    @staticmethod
    def check_single_instance():
        """检查是否已有实例在运行"""
        AdminManager.mutex = CreateMutex(None, False, 'AIDesk_SingleInstance_Mutex')
        return GetLastError() != ERROR_ALREADY_EXISTS
    
    @staticmethod
    def is_admin():
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def run_as_admin():
        """以管理员权限重新启动程序"""
        if AdminManager.is_admin():
            return True
        
        # 检查是否已经尝试过提权（避免无限循环）
        if '--elevated' in sys.argv:
            print("[Admin] 提权后仍无管理员权限，以普通权限运行")
            return False
        
        try:
            if getattr(sys, 'frozen', False):
                # 打包后的exe
                script = sys.executable
            else:
                # 开发环境
                script = os.path.abspath(sys.argv[0])
            
            # 添加标记参数，避免重复提权
            params = ' '.join(sys.argv[1:] + ['--elevated'])
            
            # 使用ShellExecute以管理员权限运行
            # SW_HIDE = 0 隐藏窗口
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 0
            )
            
            if ret > 32:  # 成功
                sys.exit(0)
            return False
        except Exception as e:
            print(f"[Admin] 提权失败: {e}")
            return False