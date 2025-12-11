import requests
import json
import config

class LocationService:
    def __init__(self):
        self.bilibili_api_url = "https://api.bilibili.com/x/web-interface/zone"
        
    def get_current_location(self):
        """
        获取当前设备的地理位置信息
        返回: 城市名称
        """
        try:
            # 添加请求头模拟浏览器
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.bilibili.com/'
            }
            
            # 使用B站API获取位置
            response = requests.get(self.bilibili_api_url, headers=headers, timeout=5)
            response.encoding = 'utf-8'
            
            print(f"[Location Debug] 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[Location Debug] 解析后数据: {data}")
                
                if data.get('code') == 0:
                    zone_info = data.get('data', {})
                    city = zone_info.get('city')
                    print(f"[Location Debug] 提取的城市: {city}")
                    if city:
                        return city
            
        except Exception as e:
            print(f"[Location Error] 获取位置失败: {str(e)}")
            
        # 默认返回北京
        print("[Location Debug] 使用默认城市: 北京")
        return "北京"
    
    def get_location_details(self):
        """
        获取详细的位置信息
        返回: 包含城市、国家、经纬度等信息的字典
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.bilibili.com/'
            }
            response = requests.get(self.bilibili_api_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    zone_info = data.get('data', {})
                    return {
                        'city': zone_info.get('city', '未知'),  # 修正：使用'city'字段
                        'region': zone_info.get('province', '未知'),
                        'country': zone_info.get('country', '未知'),
                        'lat': zone_info.get('latitude'),
                        'lon': zone_info.get('longitude'),
                        'query': 'B站IP定位'
                    }
        except Exception as e:
            print(f"[Location Error] 获取详细位置失败: {str(e)}")
            
        return {
            'city': '北京',
            'region': '北京',
            'country': '中国',
            'lat': 39.9042,
            'lon': 116.4074,
            'query': '默认位置'
        }
