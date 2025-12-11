import requests
import config
import os
import sys
import numpy as np

try:
    import pyaudio
    import wave
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

class VoiceRecognition:
    def __init__(self):
        if PYAUDIO_AVAILABLE:
            self.chunk = 1024
            self.format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000
    
    @staticmethod
    def get_microphone_list():
        """获取可用麦克风列表"""
        if not PYAUDIO_AVAILABLE:
            return []
        
        try:
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': info['name']
                    })
            p.terminate()
            return devices
        except:
            return []
    
    def record_audio(self, duration=30):
        """
        录音，检测到静音后自动停止
        :param duration: 最大录音时长（秒）
        """
        silence_duration = config.SILENCE_DURATION
        if not PYAUDIO_AVAILABLE:
            return "语音录制功能需要安装pyaudio库，请运行: conda install -c anaconda pyaudio"
        
        try:
            p = pyaudio.PyAudio()
            device_index = config.MICROPHONE_DEVICE_INDEX
            stream = p.open(format=self.format, channels=self.channels,
                           rate=self.rate, input=True, frames_per_buffer=self.chunk,
                           input_device_index=device_index)
            print(f"[录音] 使用麦克风设备: {device_index if device_index is not None else '默认'}")
            
            # 环境噪音校准（采样0.5秒）
            print("[录音] 正在校准环境噪音...")
            calibration_chunks = int(self.rate / self.chunk * 0.5)
            noise_samples = []
            for _ in range(calibration_chunks):
                data = stream.read(self.chunk)
                audio_data = np.frombuffer(data, dtype=np.int16)
                noise_samples.append(np.abs(audio_data).mean())
            
            # 计算环境噪音基线和动态阈值
            noise_baseline = np.mean(noise_samples)
            silence_threshold = noise_baseline * 1.5  # 阈值为噪音基线的1.5倍
            print(f"[录音] 环境噪音基线: {noise_baseline:.0f}, 静音阈值: {silence_threshold:.0f}")
            
            frames = []
            silent_chunks = 0
            speech_detected = False  # 是否检测到过语音
            max_silent_chunks = int(self.rate / self.chunk * silence_duration)
            max_chunks = int(self.rate / self.chunk * duration)
            
            print(f"[录音] 开始录音，静音{silence_duration}秒后自动停止")
            
            for i in range(max_chunks):
                data = stream.read(self.chunk)
                frames.append(data)
                
                # 计算音量
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                # 检测是否为语音
                if volume > silence_threshold:
                    speech_detected = True
                    silent_chunks = 0
                else:
                    # 只有在检测到语音后才开始计算静音
                    if speech_detected:
                        silent_chunks += 1
                        if silent_chunks >= max_silent_chunks:
                            print(f"[录音] 检测到{silence_duration}秒静音，停止录音")
                            break
            
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                print(f"[录音] 关闭音频流失败: {e}")
            try:
                p.terminate()
            except Exception as e:
                print(f"[录音] 终止PyAudio失败: {e}")
            
            # 使用正确的临时目录路径
            if getattr(sys, 'frozen', False):
                temp_dir = os.path.join(os.path.dirname(sys.executable), "temp")
            else:
                temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.join(temp_dir, "temp_audio.wav")
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            return filename
        except Exception as e:
            # 确保资源清理
            try:
                if 'stream' in locals():
                    stream.stop_stream()
                    stream.close()
                if 'p' in locals():
                    p.terminate()
            except:
                pass
            return f"录音失败: {str(e)}"
    
    def transcribe(self, audio_file):
        if isinstance(audio_file, str) and ("需要安装" in audio_file or "录音失败" in audio_file):
            return audio_file
        
        try:
            url = f"{config.SILICONFLOW_BASE_URL}/audio/transcriptions"
            headers = {"Authorization": f"Bearer {config.SILICONFLOW_API_KEY}"}
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                data = {'model': config.VOICE_MODEL}
                response = requests.post(url, headers=headers, files=files, data=data)
            text = response.json().get('text', '')
            print(f"[语音识别] {text}")
            return text
        except Exception as e:
            return f"语音识别失败: {str(e)}"