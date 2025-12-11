import requests
import config
from services.file_handler import FileHandler

class FileSummaryMCP:
    def __init__(self):
        self.file_handler = FileHandler()
    
    def generate_summary(self, filepath):
        """生成文件内容摘要"""
        try:
            content = self.file_handler.read_file(filepath)
            if "不支持" in content or "失败" in content:
                return content
            
            url = f"{config.SILICONFLOW_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": config.AI_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个专业的文档摘要助手，请用简洁的语言总结文档的核心内容。"},
                    {"role": "user", "content": f"请为以下内容生成摘要（200字以内）：\n\n{content[:3000]}"}
                ],
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            summary = result['choices'][0]['message']['content']
            return f"文件摘要：\n{summary}"
        except Exception as e:
            return f"生成摘要失败: {str(e)}"