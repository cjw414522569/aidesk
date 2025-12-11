import requests
import json
import config
from datetime import datetime
from .schedule_manager import ScheduleManager
from services.weather_service import WeatherService
from services.web_controller import WebController
from services.vision_service import VisionService
from services.system_controller import SystemController
from services.file_handler import FileHandler
from services.location_service import LocationService
from services.pushplus_service import PushPlusService
from services.clipboard_mcp import ClipboardMCP
from services.web_extract_mcp import WebExtractMCP
from services.file_summary_mcp import FileSummaryMCP
from services.office_control_mcp import OfficeControlMCP

class AIWithTools:
    def __init__(self):
        self.conversation_history = []
        self.speak_callback = None
        self.schedule = ScheduleManager()
        self.weather = WeatherService()
        self.web = WebController()
        self.vision = VisionService()
        self.system = SystemController()
        self.file = FileHandler()
        self.location = LocationService()
        self.pushplus = PushPlusService()
        self.clipboard = ClipboardMCP()
        self.web_extract = WebExtractMCP()
        self.file_summary = FileSummaryMCP()
        self.office = OfficeControlMCP()
        
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_location",
                    "description": "获取当前设备的地理位置信息（城市名称）",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "获取当前系统时间，包括年月日时分秒",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_schedule",
                    "description": "添加日程提醒。当用户要求设置提醒时，必须调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time": {"type": "string", "description": "提醒时间，必须是以下格式之一：1) 完整日期时间 'YYYY-MM-DD HH:MM:SS'（如'2025-12-11 15:00:00'）2) 仅时间 'HH:MM:SS'（如'15:00:00'，表示今天）3) 相对时间（如'30秒后', '1分钟后', '1小时后'）"},
                            "task": {"type": "string", "description": "提醒的任务内容"}
                        },
                        "required": ["time", "task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_schedule",
                    "description": "修改已有的日程。当用户要求修改或更改提醒时，必须调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "old_task": {"type": "string", "description": "原任务内容"},
                            "old_time": {"type": "string", "description": "原提醒时间"},
                            "new_task": {"type": "string", "description": "新的任务内容"},
                            "new_time": {"type": "string", "description": "新的提醒时间，可以是绝对时间（如'13:45:00'）或相对时间（如'30秒后', '1分钟后', '1小时后'）"}
                        },
                        "required": ["old_task", "old_time", "new_task", "new_time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_schedule",
                    "description": "删除已有的日程。当用户要求删除或取消提醒时，必须调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "要删除的任务内容"},
                            "time": {"type": "string", "description": "要删除的提醒时间"}
                        },
                        "required": ["task", "time"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_all_schedules",
                    "description": "删除所有日程。当用户要求删除所有日程、清空日程表或类似请求时，必须调用此函数。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_schedule",
                    "description": "查找日程。当用户需要查看特定日程时，可以调用此函数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_keyword": {"type": "string", "description": "任务关键词，用于模糊搜索"},
                            "time": {"type": "string", "description": "精确的提醒时间"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "查询城市天气",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "城市名称"}
                        },
                        "required": ["city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_application",
                    "description": "打开应用程序",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "应用名称，如：微信、记事本、word"}
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "open_website",
                    "description": "打开网页",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "网址或网站名称"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "screenshot_and_analyze",
                    "description": "截图并分析屏幕内容",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "media_control",
                    "description": "控制媒体播放",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["播放", "暂停", "下一首", "上一首", "音量增大", "音量减小"]}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_clipboard",
                    "description": "获取剪贴板内容",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_clipboard",
                    "description": "设置剪贴板内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "要复制的文本"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_webpage_content",
                    "description": "智能提取网页主要内容，过滤广告和无关信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "网页URL"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "prepare_text_for_speech",
                    "description": "为语音阅读优化文本格式",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "原始文本"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_file_summary",
                    "description": "生成文件内容摘要",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "文件路径"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "word_insert_text",
                    "description": "在Word文档中插入文本",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Word文件路径"},
                            "text": {"type": "string", "description": "要插入的文本"},
                            "font_size": {"type": "integer", "description": "字体大小，默认12"}
                        },
                        "required": ["filepath", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "excel_write_cell",
                    "description": "写入Excel单元格",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Excel文件路径"},
                            "sheet_name": {"type": "string", "description": "工作表名称"},
                            "cell": {"type": "string", "description": "单元格位置，如A1"},
                            "value": {"type": "string", "description": "要写入的值"}
                        },
                        "required": ["filepath", "sheet_name", "cell", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "excel_read_cell",
                    "description": "读取Excel单元格",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Excel文件路径"},
                            "sheet_name": {"type": "string", "description": "工作表名称"},
                            "cell": {"type": "string", "description": "单元格位置，如A1"}
                        },
                        "required": ["filepath", "sheet_name", "cell"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ppt_add_slide",
                    "description": "在PPT中添加幻灯片",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "PPT文件路径"},
                            "title": {"type": "string", "description": "幻灯片标题"},
                            "content": {"type": "string", "description": "幻灯片内容"}
                        },
                        "required": ["filepath", "title", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pdf_merge",
                    "description": "合并多个PDF文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "output_file": {"type": "string", "description": "输出文件路径"},
                            "input_files": {"type": "array", "items": {"type": "string"}, "description": "要合并的PDF文件列表"}
                        },
                        "required": ["output_file", "input_files"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "pdf_split",
                    "description": "拆分PDF文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input_file": {"type": "string", "description": "输入PDF文件"},
                            "output_dir": {"type": "string", "description": "输出目录"},
                            "start_page": {"type": "integer", "description": "起始页码"},
                            "end_page": {"type": "integer", "description": "结束页码"}
                        },
                        "required": ["input_file", "output_dir", "start_page", "end_page"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "创建文件并写入内容，支持txt、md等文本文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "文件路径，如：C:/Users/用户名/Desktop/test.txt"},
                            "content": {"type": "string", "description": "文件内容，默认为空"}
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_folder",
                    "description": "创建文件夹",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder_path": {"type": "string", "description": "文件夹路径"}
                        },
                        "required": ["folder_path"]
                    }
                }
            }
        ]

    def set_speak_callback(self, callback):
        self.speak_callback = callback
        self.schedule.set_speak_callback(callback)
        self.schedule.set_ai_chat_callback(self.chat)
    
    def execute_tool(self, tool_name, arguments):
        print(f"[DEBUG] 执行工具: {tool_name}, 参数: {arguments}")
        
        if tool_name == "get_current_location":
            location = self.location.get_current_location()
            result = f"当前所在城市: {location}"
            print(f"[DEBUG] 工具返回: {result}")
            return result
        
        elif tool_name == "get_current_time":
            now = datetime.now()
            weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
            weekday = weekdays[now.weekday()]
            result = f"当前时间：{now.strftime('%Y年%m月%d日')} {weekday} {now.strftime('%H:%M:%S')}"
            print(f"[DEBUG] 工具返回: {result}")
            return result
        
        elif tool_name == "add_schedule":
            try:
                import re
                from datetime import timedelta

                time_str = arguments["time"]
                task = arguments["task"]
                
                # 解析相对时间
                seconds_match = re.search(r'(\d+)\s*秒', time_str)
                minutes_match = re.search(r'(\d+)\s*分', time_str)
                hours_match = re.search(r'(\d+)\s*小时', time_str)
                
                now = datetime.now()
                future_time = None

                if seconds_match:
                    future_time = now + timedelta(seconds=int(seconds_match.group(1)))
                elif minutes_match:
                    future_time = now + timedelta(minutes=int(minutes_match.group(1)))
                elif hours_match:
                    future_time = now + timedelta(hours=int(hours_match.group(1)))
                
                if future_time:
                    final_time_str = future_time.strftime('%H:%M:%S')
                else:
                    # 假设是绝对时间
                    final_time_str = time_str

                # 检查是否需要微信通知（检查任务描述中是否包含"微信"关键词）
                pushplus_notify = "微信" in task or "微信提醒" in arguments.get("original_message", "")
                
                self.schedule.add_schedule(final_time_str, task, pushplus_notify=pushplus_notify)
                result = f"已添加日程：{final_time_str} {task}"
                if pushplus_notify:
                    result += "（将发送微信通知）"
                print(f"[DEBUG] 工具返回: {result}")
                return result
            except Exception as e:
                error_msg = f"添加日程失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "update_schedule":
            try:
                import re
                from datetime import timedelta

                old_time = arguments["old_time"]
                old_task = arguments["old_task"]
                new_time = arguments["new_time"]
                new_task = arguments["new_task"]
                
                # 解析相对时间
                seconds_match = re.search(r'(\d+)\s*秒', new_time)
                minutes_match = re.search(r'(\d+)\s*分', new_time)
                hours_match = re.search(r'(\d+)\s*小时', new_time)
                
                now = datetime.now()
                future_time = None

                if seconds_match:
                    future_time = now + timedelta(seconds=int(seconds_match.group(1)))
                elif minutes_match:
                    future_time = now + timedelta(minutes=int(minutes_match.group(1)))
                elif hours_match:
                    future_time = now + timedelta(hours=int(hours_match.group(1)))
                
                if future_time:
                    final_time_str = future_time.strftime('%H:%M:%S')
                else:
                    # 假设是绝对时间
                    final_time_str = new_time
                
                # 先查找原日程的完整时间
                schedules = self.schedule.find_schedules(task_keyword=old_task)
                old_datetime = None
                
                for schedule in schedules:
                    if old_task in schedule['task']:
                        old_datetime = schedule['datetime']
                        break
                
                if not old_datetime:
                    return f"未找到任务为'{old_task}'的日程"
                
                success = self.schedule.update_schedule(old_datetime, old_task, final_time_str, new_task)
                if success:
                    result = f"已修改日程：{final_time_str} {new_task}"
                    print(f"[DEBUG] 工具返回: {result}")
                    return result
                else:
                    error_msg = f"修改日程失败，未找到匹配的日程：{old_time} {old_task}"
                    print(f"[DEBUG] 错误: {error_msg}")
                    return error_msg
            except Exception as e:
                error_msg = f"修改日程失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "delete_schedule":
            try:
                task = arguments.get("task", "")
                time = arguments.get("time", "")
                
                # 根据时间查找日程
                now = datetime.now()
                time_parts = time.split(':')
                if len(time_parts) >= 2:
                    hour, minute = int(time_parts[0]), int(time_parts[1])
                    target_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    datetime_pattern = target_datetime.strftime('%Y-%m-%d %H:%M')
                    
                    # 查找匹配时间的日程
                    all_schedules = self.schedule.load_schedules()
                    matching_schedules = [s for s in all_schedules if s['datetime'].startswith(datetime_pattern)]
                    
                    if not matching_schedules:
                        return f"未找到{time}的日程"
                    
                    # 删除找到的第一个日程
                    schedule = matching_schedules[0]
                    success = self.schedule.delete_schedule(schedule['datetime'], schedule['task'])
                    if success:
                        result = f"已删除日程：{time} {schedule['task']}"
                        print(f"[DEBUG] 工具返回: {result}")
                        return result
                else:
                    # 按任务名查找
                    schedules = self.schedule.find_schedules(task_keyword=task)
                    if not schedules:
                        return f"未找到任务为'{task}'的日程"
                    
                    schedule = schedules[0]
                    success = self.schedule.delete_schedule(schedule['datetime'], schedule['task'])
                    if success:
                        result = f"已删除日程：{schedule['datetime']} {schedule['task']}"
                        print(f"[DEBUG] 工具返回: {result}")
                        return result
                
                return "删除日程失败"
            except Exception as e:
                error_msg = f"删除日程失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "find_schedule":
            try:
                task_keyword = arguments.get("task_keyword")
                time = arguments.get("time")
                
                schedules = self.schedule.find_schedules(task_keyword=task_keyword, datetime_str=time)
                
                if schedules:
                    result = "找到以下日程：\n"
                    for schedule in schedules:
                        result += f"- {schedule['datetime']} {schedule['task']}\n"
                    print(f"[DEBUG] 工具返回: {result}")
                    return result
                else:
                    result = "未找到匹配的日程"
                    print(f"[DEBUG] 工具返回: {result}")
                    return result
            except Exception as e:
                error_msg = f"查找日程失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "delete_all_schedules":
            try:
                count = self.schedule.delete_all_schedules()
                result = f"已删除所有日程，共删除 {count} 个日程"
                print(f"[DEBUG] 工具返回: {result}")
                return result
            except Exception as e:
                error_msg = f"删除所有日程失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "get_weather":
            try:
                return self.weather.get_weather(arguments["city"])
            except Exception as e:
                error_msg = f"查询天气失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "open_application":
            try:
                return self.system.open_app(arguments["app_name"])
            except Exception as e:
                error_msg = f"打开应用失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "open_website":
            try:
                return self.web.open_url(arguments["url"])
            except Exception as e:
                error_msg = f"打开网页失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "screenshot_and_analyze":
            try:
                return self.vision.analyze_screen()
            except Exception as e:
                error_msg = f"截图分析失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "media_control":
            try:
                return self.system.media_control(arguments["action"])
            except Exception as e:
                error_msg = f"媒体控制失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "get_clipboard":
            return self.clipboard.get_clipboard()
        
        elif tool_name == "set_clipboard":
            return self.clipboard.set_clipboard(arguments["text"])
        
        elif tool_name == "extract_webpage_content":
            return self.web_extract.extract_main_content(arguments["url"])
        
        elif tool_name == "prepare_text_for_speech":
            return self.web_extract.prepare_for_speech(arguments["text"])
        
        elif tool_name == "generate_file_summary":
            return self.file_summary.generate_summary(arguments["filepath"])
        
        elif tool_name == "word_insert_text":
            font_size = arguments.get("font_size", 12)
            return self.office.word_insert_text(arguments["filepath"], arguments["text"], font_size)
        
        elif tool_name == "excel_write_cell":
            return self.office.excel_write_cell(arguments["filepath"], arguments["sheet_name"], arguments["cell"], arguments["value"])
        
        elif tool_name == "excel_read_cell":
            return self.office.excel_read_cell(arguments["filepath"], arguments["sheet_name"], arguments["cell"])
        
        elif tool_name == "ppt_add_slide":
            return self.office.ppt_add_slide(arguments["filepath"], arguments["title"], arguments["content"])
        
        elif tool_name == "pdf_merge":
            try:
                return self.office.pdf_merge(arguments["output_file"], *arguments["input_files"])
            except Exception as e:
                error_msg = f"PDF合并失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "pdf_split":
            try:
                return self.office.pdf_split(arguments["input_file"], arguments["output_dir"], arguments["start_page"], arguments["end_page"])
            except Exception as e:
                error_msg = f"PDF拆分失败: {str(e)}"
                print(f"[DEBUG] 错误: {error_msg}")
                return error_msg
        
        elif tool_name == "create_file":
            content = arguments.get("content", "")
            return self.file.create_file(arguments["filepath"], content)
        
        elif tool_name == "create_folder":
            return self.file.create_folder(arguments["folder_path"])
        
        return "未知工具"
    
    def chat(self, user_message):
        print(f"[DEBUG] 用户消息: {user_message}")
        
        # 添加系统提示（仅在对话开始时）
        if len(self.conversation_history) == 0:
            system_prompt = {
                "role": "system",
                "content": "你是一个AI助手。重要规则：\n1. 当用户要求设置提醒时，必须立即调用add_schedule工具。时间参数支持相对时间格式（如'1小时后'、'30分钟后'、'10秒后'）。\n2. 当用户查询天气但没有指定城市时，你必须在一次响应中同时调用get_current_location和get_weather两个工具。\n3. 当用户要求修改提醒时，必须先调用find_schedule查找相关日程，然后调用update_schedule修改日程。\n4. 当用户要求删除提醒时，必须先调用find_schedule查找相关日程，然后调用delete_schedule删除日程。\n5. 当用户要求删除所有日程时，必须直接调用delete_all_schedules工具。"
            }
            self.conversation_history.append(system_prompt)
        
        # 保存原始消息用于判断是否需要微信通知
        self.original_user_message = user_message
        
        # 添加当前时间信息到用户消息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        enhanced_message = f"[当前时间: {current_time}] {user_message}"
        
        self.conversation_history.append({"role": "user", "content": enhanced_message})
        
        try:
            url = f"{config.SILICONFLOW_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {config.SILICONFLOW_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": config.AI_MODEL,
                "messages": self.conversation_history,
                "tools": self.tools,
                "max_tokens": 2000
            }
            
            print(f"[DEBUG] 发送API请求...")
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            print(f"[DEBUG] API响应状态: {response.status_code}")
            
            if 'error' in result:
                error_msg = f"API错误: {result['error'].get('message', '未知错误')}"
                print(f"[DEBUG] {error_msg}")
                return error_msg
            
            if 'choices' not in result:
                error_msg = f"API响应格式错误: {result}"
                print(f"[DEBUG] {error_msg}")
                return error_msg
            
            message = result['choices'][0]['message']
            
            # 循环处理工具调用，支持多轮工具调用
            max_iterations = 5  # 最多5轮工具调用
            iteration = 0
            
            while message.get('tool_calls') and iteration < max_iterations:
                iteration += 1
                print(f"[DEBUG] 第{iteration}轮工具调用: {len(message['tool_calls'])}个")
                
                tool_results = []
                for tool_call in message['tool_calls']:
                    function_name = tool_call['function']['name']
                    arguments = json.loads(tool_call['function']['arguments'])
                    # 传递原始消息用于判断是否需要微信通知
                    if function_name == "add_schedule":
                        arguments["original_message"] = self.original_user_message
                    result = self.execute_tool(function_name, arguments)
                    tool_results.append(result)
                
                # 将工具调用结果添加到对话历史
                self.conversation_history.append(message)
                for i, tool_call in enumerate(message['tool_calls']):
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": tool_results[i]
                    })
                
                # 再次调用AI
                print(f"[DEBUG] 发送第{iteration+1}次API请求...")
                data['messages'] = self.conversation_history
                response = requests.post(url, headers=headers, json=data)
                result = response.json()
                
                if 'error' in result:
                    error_msg = f"API错误: {result['error'].get('message', '未知错误')}"
                    print(f"[DEBUG] {error_msg}")
                    return error_msg
                
                if 'choices' not in result:
                    error_msg = f"API响应格式错误: {result}"
                    print(f"[DEBUG] {error_msg}")
                    return error_msg
                
                message = result['choices'][0]['message']
            
            # 获取最终文本回复
            final_message = message.get('content')
            if not final_message:
                final_message = "操作已完成。"
            
            self.conversation_history.append({"role": "assistant", "content": final_message})
            print(f"[DEBUG] 最终回复: {final_message}")
            return final_message
            
                
        except Exception as e:
            error_msg = f"AI对话失败: {str(e)}"
            print(f"[DEBUG] 异常: {error_msg}")
            return error_msg
    
    def clear_history(self):
        self.conversation_history = []