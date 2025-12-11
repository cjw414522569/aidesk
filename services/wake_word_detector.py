import pyaudio
from vosk import Model, KaldiRecognizer
import json
import threading
import config
import os

class WakeWordDetector:
    def __init__(self):
        self.running = False
        self.paused = False
        self.thread = None
        self.callback = None
        self.model = None
        self.audio_interface = None
        self.audio_stream = None
        self.stream_lock = __import__('threading').Lock()
        
    def start(self, callback):
        """启动唤醒词检测"""
        if self.running or not config.WAKE_WORD_ENABLED:
            return
        
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._detect_loop, daemon=True)
        self.thread.start()
        print(f"[唤醒词] 已启动，唤醒词: {config.WAKE_WORD}")
    
    def pause(self):
        """暂停唤醒词检测"""
        with self.stream_lock:
            self.paused = True
        print("[唤醒词] 已暂停")
    
    def resume(self):
        """恢复唤醒词检测"""
        with self.stream_lock:
            self.paused = False
        print("[唤醒词] 已恢复")
    
    def stop(self):
        """停止唤醒词检测"""
        self.running = False
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.audio_interface:
            self.audio_interface.terminate()
        print("[唤醒词] 已停止")
    
    def _detect_loop(self):
        """检测循环"""
        import time
        
        while self.running:
            try:
                if not os.path.exists(config.VOSK_MODEL_PATH):
                    print(f"[唤醒词错误] 模型路径不存在: {config.VOSK_MODEL_PATH}")
                    time.sleep(5)  # 等待5秒后重试
                    continue
                
                if not self.model:
                    self.model = Model(config.VOSK_MODEL_PATH)
                
                if not self.audio_interface:
                    self.audio_interface = pyaudio.PyAudio()
                
                # 尝试打开音频流
                success = self._open_audio_stream()
                if not success:
                    print("[唤醒词] 5秒后重试...")
                    time.sleep(5)
                    continue
                
                recognizer = KaldiRecognizer(self.model, 16000)
                
                print("[唤醒词] 开始监听唤醒词...")
                
                while self.running:
                    with self.stream_lock:
                        is_paused = self.paused
                    
                    if is_paused:
                        # 暂停期间等待
                        time.sleep(0.1)
                        continue
                    
                    try:
                        # 检查流是否仍然活跃
                        if not self.audio_stream or not self.audio_stream.is_active():
                            print("[唤醒词] 音频流断开，尝试重新连接...")
                            break
                        
                        data = self.audio_stream.read(4000, exception_on_overflow=False)
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            text = result.get("text", "")
                            if text:
                                print(f"[唤醒词识别] {text}")
                            # 移除空格进行匹配，支持识别结果中有空格的情况
                            text_no_space = text.replace(" ", "")
                            wake_word_no_space = config.WAKE_WORD.replace(" ", "")
                            if wake_word_no_space in text_no_space:
                                print(f"[唤醒词] 检测到唤醒词: {config.WAKE_WORD}")
                                if self.callback:
                                    self.callback()
                    except Exception as e:
                        # 如果是流关闭错误，重新尝试连接
                        if "Stream closed" in str(e) or "-9988" in str(e) or "Input overflowed" in str(e):
                            print(f"[唤醒词] 音频流异常: {e}")
                            break
                        # 其他错误继续运行
                        print(f"[唤醒词] 读取音频出错: {e}")
                        time.sleep(0.1)
                
                # 清理当前音频流
                if self.audio_stream:
                    try:
                        self.audio_stream.stop_stream()
                        self.audio_stream.close()
                    except:
                        pass
                    self.audio_stream = None
                
            except Exception as e:
                print(f"[唤醒词错误] {e}")
                time.sleep(5)  # 出错后等待5秒重试
    
    def _open_audio_stream(self):
        """打开音频流"""
        try:
            # 列出所有可用的音频设备
            print("[唤醒词] 扫描音频设备...")
            input_devices = []
            for i in range(self.audio_interface.get_device_count()):
                device_info = self.audio_interface.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    input_devices.append((i, device_info))
                    print(f"[唤醒词] 找到输入设备 {i}: {device_info['name']}")
            
            if not input_devices:
                print("[唤醒词错误] 未找到任何音频输入设备")
                print("[唤醒词] 请检查:")
                print("  1. 麦克风是否已连接")
                print("  2. 麦克风驱动是否已安装")
                print("  3. 麦克风权限是否已授予")
                return False
            
            # 获取可用的音频设备
            device_index = config.MICROPHONE_DEVICE_INDEX
            if device_index is not None:
                # 验证指定的设备是否存在且为输入设备
                try:
                    device_info = self.audio_interface.get_device_info_by_index(device_index)
                    if device_info['maxInputChannels'] == 0:
                        print(f"[唤醒词错误] 设备 {device_index} 不是输入设备")
                        device_index = None
                    else:
                        print(f"[唤醒词] 使用指定麦克风设备: {device_index} - {device_info['name']}")
                except Exception as e:
                    print(f"[唤醒词错误] 无法访问设备 {device_index}: {e}")
                    device_index = None
            
            if device_index is None:
                # 使用第一个可用的输入设备
                device_index = input_devices[0][0]
                device_info = input_devices[0][1]
                print(f"[唤醒词] 使用第一个可用麦克风设备: {device_index} - {device_info['name']}")
            
            # 尝试打开音频流
            try:
                self.audio_stream = self.audio_interface.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=4000,
                    input_device_index=device_index
                )
                print(f"[唤醒词] 音频流已成功打开，使用设备: {device_index}")
                return True
            except Exception as e:
                print(f"[唤醒词错误] 无法打开音频流: {e}")
                print(f"[唤醒词错误] 错误详情: {type(e).__name__}: {str(e)}")
                
                # 尝试其他可用设备
                for idx, device_info in input_devices:
                    if idx == device_index:
                        continue
                    try:
                        print(f"[唤醒词] 尝试设备 {idx}: {device_info['name']}")
                        self.audio_stream = self.audio_interface.open(
                            format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            frames_per_buffer=4000,
                            input_device_index=idx
                        )
                        print(f"[唤醒词] 成功使用设备 {idx}: {device_info['name']}")
                        return True
                    except Exception as e2:
                        print(f"[唤醒词] 设备 {idx} 失败: {e2}")
                        continue
                else:
                    print("[唤醒词错误] 所有音频设备都无法打开")
                    return False
                    
        except Exception as e:
            print(f"[唤醒词错误] 打开音频流时出错: {e}")
            return False