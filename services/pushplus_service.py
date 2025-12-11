import requests
import json
import config
from datetime import datetime

class PushPlusService:
    def __init__(self):
        self.token = config.PUSHPLUS_TOKEN
        self.base_url = "http://www.pushplus.plus/send"
    
    def send_notification(self, title, content, template="html"):
        """发送PushPlus通知"""
        if not self.token:
            print("[PushPlus] Token未配置，无法发送通知")
            return False
        
        try:
            data = {
                "token": self.token,
                "title": title,
                "content": content,
                "template": template
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, data=json.dumps(data), headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                print(f"[PushPlus] 通知发送成功: {title}")
                return True
            else:
                error_msg = result.get("msg", "未知错误")
                print(f"[PushPlus] 通知发送失败: {error_msg}")
                return False
                
        except Exception as e:
            print(f"[PushPlus] 发送通知异常: {e}")
            return False
    
    def test_connection(self):
        """测试PushPlus连接"""
        return self.send_notification("测试通知", "AI助手PushPlus服务测试成功！")
    
    def update_token(self, token):
        """更新Token"""
        self.token = token
        config.PUSHPLUS_TOKEN = token