import requests
import config

class WeatherService:
    def get_weather(self, city):
        try:
            # 处理"当前城市"的情况，默认使用北京
            if city in ["当前城市", "当前位置", "这里"]:
                city = "北京"
            
            # 常见城市名称映射到城市代码
            city_codes = {
                "北京": "101010100",
                "上海": "101020100",
                "广州": "101280101",
                "深圳": "101280601",
                "成都": "101270101",
                "杭州": "101210101",
                "重庆": "101040100",
                "西安": "101110101",
                "武汉": "101200101",
                "南京": "101190101",
                "天津": "101030100",
                "苏州": "101190401",
                "郑州": "101180101",
                "长沙": "101250101",
                "东莞": "101281601",
                "沈阳": "101070101",
                "青岛": "101120201",
                "合肥": "101220101",
                "佛山": "101280800",
                "济南": "101120101"
            }
            
            # 获取城市代码
            location = city_codes.get(city, city)  # 如果找不到，就直接使用输入的城市名
            
            # 获取实时天气
            weather_url = f"{config.WEATHER_API_URL}/weather/now"
            params = {"location": location, "key": config.WEATHER_API_KEY}
            response = requests.get(weather_url, params=params, timeout=10)
            
            print(f"[Weather Debug] 天气查询状态: {response.status_code}")
            print(f"[Weather Debug] 请求URL: {weather_url}")
            print(f"[Weather Debug] 参数: {params}")
            
            if response.status_code != 200:
                return f"天气API请求失败: HTTP {response.status_code}"
            
            weather_data = response.json()
            print(f"[Weather Debug] 响应数据: {weather_data}")
            
            if weather_data.get('code') != '200':
                return f"获取天气失败，错误代码: {weather_data.get('code')}"
            
            now = weather_data['now']
            return f"{city}当前天气：{now['text']}，温度{now['temp']}℃，湿度{now['humidity']}%，风向{now['windDir']}"
        except requests.exceptions.Timeout:
            return "天气查询超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            return f"网络请求错误: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"天气数据解析错误: {str(e)}"
        except Exception as e:
            return f"查询天气时出错: {str(e)}"
    
    def get_forecast(self, city, days=3):
        try:
            # 处理"当前城市"的情况
            if city in ["当前城市", "当前位置", "这里"]:
                city = "北京"
            
            # 常见城市名称映射到城市代码
            city_codes = {
                "北京": "101010100",
                "上海": "101020100",
                "广州": "101280101",
                "深圳": "101280601",
                "成都": "101270101",
                "杭州": "101210101",
                "重庆": "101040100",
                "西安": "101110101",
                "武汉": "101200101",
                "南京": "101190101",
                "天津": "101030100",
                "苏州": "101190401",
                "郑州": "101180101",
                "长沙": "101250101",
                "东莞": "101281601",
                "沈阳": "101070101",
                "青岛": "101120201",
                "合肥": "101220101",
                "佛山": "101280800",
                "济南": "101120101"
            }
            
            location = city_codes.get(city, city)
            
            forecast_url = f"{config.WEATHER_API_URL}/weather/7d"
            params = {"location": location, "key": config.WEATHER_API_KEY}
            response = requests.get(forecast_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return f"预报数据请求失败: HTTP {response.status_code}"
            
            forecast_data = response.json()
            
            if forecast_data.get('code') != '200':
                return f"获取预报失败: {forecast_data.get('code')}"
            
            result = f"{city}未来{days}天天气预报：\n"
            for day in forecast_data['daily'][:days]:
                result += f"{day['fxDate']}：{day['textDay']}，{day['tempMin']}~{day['tempMax']}℃\n"
            
            return result
        except requests.exceptions.Timeout:
            return "天气预报查询超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            return f"网络请求错误: {str(e)}"
        except (KeyError, IndexError) as e:
            return f"预报数据解析错误: {str(e)}"
        except Exception as e:
            return f"查询预报时出错: {str(e)}"