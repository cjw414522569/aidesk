import requests
from bs4 import BeautifulSoup
import re

class WebExtractMCP:
    def extract_main_content(self, url):
        """智能提取网页主要内容"""
        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # 提取标题
            title = soup.find('title')
            title_text = title.get_text() if title else "无标题"
            
            # 查找主要内容区域
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile('content|main|article'))
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # 清理文本
            lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
            clean_text = '\n'.join(lines[:100])  # 限制行数
            
            return f"标题: {title_text}\n\n{clean_text}"
        except Exception as e:
            return f"提取失败: {str(e)}"
    
    def prepare_for_speech(self, text):
        """为语音阅读优化文本"""
        text = text.replace('\n\n', '。 ')
        text = text.replace('\n', ' ')
        text = ' '.join(text.split())
        return text