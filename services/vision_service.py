import pyautogui
import requests
import base64
import config
import os
from PIL import Image

class VisionService:
    def screenshot(self, filename="temp/screenshot.png"):
        os.makedirs("temp", exist_ok=True)
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return filename
    
    def ocr_image(self, image_path):
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        url = f"{config.SILICONFLOW_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.SILICONFLOW_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": config.OCR_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                        {"type": "text", "text": "请识别图片中的所有文字内容"}
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def analyze_screen(self):
        screenshot_file = self.screenshot()
        analysis = self.ocr_image(screenshot_file)
        return analysis