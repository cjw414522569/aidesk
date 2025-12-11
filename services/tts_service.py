import requests
import tempfile
import os
from pygame import mixer
import threading
import config
import re

class TTSService:
    def __init__(self):
        self.api_url = config.TTS_API_URL
        self.api_key = config.TTS_API_KEY
        self.is_speaking = False
        self.current_thread = None
        self.mixer_initialized = False
        self._init_mixer()
    
    def _init_mixer(self):
        """安全初始化pygame mixer"""
        try:
            if not self.mixer_initialized:
                mixer.init()
                self.mixer_initialized = True
                print("[TTS] pygame mixer 初始化成功")
        except Exception as e:
            print(f"[TTS] pygame mixer 初始化失败: {e}")
            # 尝试使用不同的音频驱动
            try:
                mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                self.mixer_initialized = True
                print("[TTS] pygame mixer 使用备用参数初始化成功")
            except Exception as e2:
                print(f"[TTS] pygame mixer 备用初始化也失败: {e2}")
    
    def clean_text(self, text):
        """清理文本"""
        if config.TTS_REMOVE_MARKDOWN:
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = re.sub(r'__(.+?)__', r'\1', text)
            text = re.sub(r'_(.+?)_', r'\1', text)
            text = re.sub(r'~~(.+?)~~', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
            text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        if config.TTS_REMOVE_EMOJI:
            # 只删除常见的Emoji表情，使用更安全的范围，避免误删中文
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # 表情符号
                "\U0001F300-\U0001F5FF"  # 符号和象形文字
                "\U0001F680-\U0001F6FF"  # 交通和地图符号
                "\U0001F1E0-\U0001F1FF"  # 旗帜
                "\U0001F900-\U0001F9FF"  # 补充符号和象形文字
                "\U0001FA00-\U0001FA6F"  # 扩展A
                "\U0001FA70-\U0001FAFF"  # 扩展B
                "]+",
                flags=re.UNICODE
            )
            text = emoji_pattern.sub('', text)
        
        if config.TTS_REMOVE_URL:
            text = re.sub(r'https?://\S+', '', text)
            text = re.sub(r'www\.\S+', '', text)
        
        if config.TTS_REMOVE_REFERENCE:
            text = re.sub(r'\[\d+\]', '', text)
        
        if config.TTS_REMOVE_WHITESPACE:
            # 将多个空白字符替换为单个空格，但保留必要的空格
            text = re.sub(r'\n+', ' ', text)  # 换行替换为空格
            text = re.sub(r'\s+', ' ', text)  # 多个空格替换为单个空格
            text = text.strip()
        
        return text
    
    def stop(self):
        """停止当前播放"""
        if self.mixer_initialized and mixer.music.get_busy():
            mixer.music.stop()
        self.is_speaking = False
    
    def speak(self, text):
        """使用TTS API播放语音，支持打断"""
        # 打断当前播放
        self.stop()
        
        def _speak():
            try:
                self.is_speaking = True
                
                # 清理文本
                cleaned_text = self.clean_text(text)
                
                # 如果清理后文本为空，使用原文本
                if not cleaned_text or not cleaned_text.strip():
                    cleaned_text = text
                
                # 确保文本不为空
                if not cleaned_text:
                    print("[TTS] 错误: 文本为空")
                    return
                
                print(f"[TTS] 发送文本: {cleaned_text[:100]}")
                
                response = requests.post(
                    self.api_url,
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'tts-1',
                        'input': cleaned_text,
                        'voice': config.TTS_VOICE,
                        'speed': config.TTS_SPEED,
                        'pitch': config.TTS_PITCH,
                        'stream': config.TTS_STREAM
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                        f.write(response.content)
                        temp_file = f.name
                    
                    if self.mixer_initialized:
                        mixer.music.load(temp_file)
                        mixer.music.play()
                        
                        while mixer.music.get_busy() and self.is_speaking:
                            pass
                        
                        # 播放完成后卸载音频，释放文件
                        mixer.music.unload()
                    else:
                        print("[TTS] mixer未初始化，无法播放音频")
                    
                    try:
                        # 确保文件完全释放后再删除
                        import time
                        time.sleep(0.1)
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception as e:
                        print(f"[TTS] 删除临时文件失败: {e}")
                else:
                    print(f"[TTS] API错误: {response.status_code}")
                    print(f"[TTS] 响应: {response.text}")
            except Exception as e:
                print(f"[TTS] 播放失败: {e}")
            finally:
                self.is_speaking = False
                # 清理线程引用
                self.current_thread = None
        
        self.current_thread = threading.Thread(target=_speak, daemon=True)
        self.current_thread.start()