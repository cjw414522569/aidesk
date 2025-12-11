import webbrowser
import requests
from bs4 import BeautifulSoup

class WebController:
    def open_url(self, url):
        if not url.startswith('http'):
            url = 'https://' + url
        webbrowser.open(url)
        return f"已打开：{url}"
    
    def search(self, keyword, engine="baidu"):
        urls = {
            "baidu": f"https://www.baidu.com/s?wd={keyword}",
            "google": f"https://www.google.com/search?q={keyword}"
        }
        url = urls.get(engine, urls["baidu"])
        webbrowser.open(url)
        return f"已在{engine}搜索：{keyword}"
    
    def read_webpage(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines[:50])
        except:
            return "读取网页失败"