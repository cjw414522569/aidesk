import sqlite3
import time
from datetime import datetime
import threading
import config
import subprocess
import sys
import os
from services.pushplus_service import PushPlusService

class ScheduleManager:
    def __init__(self):
        self.db_path = config.SCHEDULE_DB
        self.init_db()
        self.running = False
        self.speak_callback = None
        self.ai_chat_callback = None
        self.reminded_schedules = set()  # 记录已提醒的日程
        self.reminder_counts = {}  # 记录每个日程的提醒次数
        self.load_reminded_schedules()  # 加载已提醒的日程
        self.pushplus = PushPlusService()  # PushPlus通知服务
        
    def set_speak_callback(self, callback):
        self.speak_callback = callback
    
    def set_ai_chat_callback(self, callback):
        self.ai_chat_callback = callback
        
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在以及列结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schedules'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # 检查是否有datetime列
            cursor.execute("PRAGMA table_info(schedules)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 检查是否有repeat_type列
            if 'repeat_type' not in columns:
                cursor.execute("ALTER TABLE schedules ADD COLUMN repeat_type TEXT DEFAULT 'once'")
                print("[DB Migration] 添加repeat_type列")
            
            if 'datetime' not in columns and 'time' in columns:
                # 需要迁移：从time列迁移到datetime列
                print("[DB Migration] 迁移数据库结构...")
                
                # 创建新表
                cursor.execute('''
                    CREATE TABLE schedules_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        datetime TEXT NOT NULL,
                        task TEXT NOT NULL,
                        reminded INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 迁移数据：将time转换为今天的datetime
                cursor.execute("SELECT id, time, task, created_at FROM schedules")
                old_data = cursor.fetchall()
                
                from datetime import datetime as dt
                today = dt.now().strftime('%Y-%m-%d')
                
                for row in old_data:
                    old_id, time_str, task, created_at = row
                    # 将HH:MM:SS转换为YYYY-MM-DD HH:MM:SS
                    datetime_str = f"{today} {time_str}"
                    cursor.execute(
                        "INSERT INTO schedules_new (datetime, task, reminded, created_at) VALUES (?, ?, 0, ?)",
                        (datetime_str, task, created_at)
                    )
                
                # 删除旧表，重命名新表
                cursor.execute("DROP TABLE schedules")
                cursor.execute("ALTER TABLE schedules_new RENAME TO schedules")
                
                print("[DB Migration] 迁移完成")
            elif 'reminded' not in columns:
                # 添加reminded列
                cursor.execute("ALTER TABLE schedules ADD COLUMN reminded INTEGER DEFAULT 0")
            
            # 检查是否有pushplus_notify列
            if 'pushplus_notify' not in columns:
                # 添加pushplus_notify列
                cursor.execute("ALTER TABLE schedules ADD COLUMN pushplus_notify INTEGER DEFAULT 0")
                print("[DB Migration] 添加pushplus_notify列")
        else:
            # 创建新表
            cursor.execute('''
                CREATE TABLE schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    task TEXT NOT NULL,
                    reminded INTEGER DEFAULT 0,
                    pushplus_notify INTEGER DEFAULT 0,
                    repeat_type TEXT DEFAULT 'once',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        conn.commit()
        conn.close()
    
    def load_reminded_schedules(self):
        """加载已提醒过的日程，并自动标记所有过期日程为已提醒"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # 加载已标记为提醒的日程
            cursor.execute('SELECT datetime, task FROM schedules WHERE reminded = 1')
            for row in cursor.fetchall():
                task_id = f"{row[0]}-{row[1]}"
                self.reminded_schedules.add(task_id)
            
            # 自动标记所有过期的日程为已提醒（避免启动时重复提醒）
            cursor.execute('SELECT datetime, task FROM schedules WHERE datetime < ? AND reminded = 0', (now,))
            expired_schedules = cursor.fetchall()
            
            for row in expired_schedules:
                datetime_str, task = row
                task_id = f"{datetime_str}-{task}"
                self.reminded_schedules.add(task_id)
                # 更新数据库
                cursor.execute('UPDATE schedules SET reminded = 1 WHERE datetime = ? AND task = ?', (datetime_str, task))
            
            if expired_schedules:
                conn.commit()
                print(f"[Schedule] 自动标记了 {len(expired_schedules)} 个过期日程为已提醒")
        except Exception as e:
            print(f"[Schedule Error] 加载日程失败: {e}")
        
        conn.close()
    
    def mark_as_reminded(self, datetime_str, task):
        """标记日程为已提醒"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE schedules SET reminded = 1 WHERE datetime = ? AND task = ?', (datetime_str, task))
        conn.commit()
        conn.close()
    
    def load_schedules(self, limit=None, future_only=False, date_filter=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if date_filter:
            # 获取指定日期的日程
            date_start = f"{date_filter} 00:00:00"
            date_end = f"{date_filter} 23:59:59"
            cursor.execute('SELECT datetime, task, pushplus_notify, repeat_type FROM schedules WHERE datetime >= ? AND datetime <= ? AND reminded = 0 ORDER BY datetime', (date_start, date_end))
        elif future_only:
            # 只获取未来的日程
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if limit:
                cursor.execute('SELECT datetime, task, pushplus_notify, repeat_type FROM schedules WHERE datetime >= ? AND reminded = 0 ORDER BY datetime LIMIT ?', (now, limit))
            else:
                cursor.execute('SELECT datetime, task, pushplus_notify, repeat_type FROM schedules WHERE datetime >= ? AND reminded = 0 ORDER BY datetime', (now,))
        else:
            if limit:
                cursor.execute('SELECT datetime, task, pushplus_notify, repeat_type FROM schedules WHERE reminded = 0 ORDER BY datetime LIMIT ?', (limit,))
            else:
                cursor.execute('SELECT datetime, task, pushplus_notify, repeat_type FROM schedules WHERE reminded = 0 ORDER BY datetime')
        
        schedules = [{"datetime": row[0], "task": row[1], "pushplus_notify": row[2] if len(row) > 2 else 0, "repeat_type": row[3] if len(row) > 3 else 'once'} for row in cursor.fetchall()]
        conn.close()
        return schedules
    
    def update_schedule(self, old_datetime, old_task, new_datetime, new_task):
        """修改日程"""
        print(f"[DEBUG] 修改日程: 原时间={old_datetime}, 原任务={old_task} -> 新时间={new_datetime}, 新任务={new_task}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 将时间字符串转换为完整的日期时间
        now = datetime.now()
        try:
            # 尝试解析时间
            time_parts = new_datetime.split(':')
            if len(time_parts) == 3:
                hour, minute, second = map(int, time_parts)
                schedule_datetime = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
                # 如果时间已过，设置为明天
                if schedule_datetime < now:
                    from datetime import timedelta
                    schedule_datetime += timedelta(days=1)
                new_datetime_str = schedule_datetime.strftime('%Y-%m-%d %H:%M:%S')
            else:
                new_datetime_str = new_datetime
        except:
            new_datetime_str = new_datetime
        
        cursor.execute('UPDATE schedules SET datetime = ?, task = ? WHERE datetime = ? AND task = ?',
                     (new_datetime_str, new_task, old_datetime, old_task))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        if rows_affected > 0:
            # 如果修改成功，从已提醒集合中移除旧的日程ID
            old_task_id = f"{old_datetime}-{old_task}"
            self.reminded_schedules.discard(old_task_id)
            print(f"[DEBUG] 日程修改成功: {new_datetime_str} {new_task}")
            return True
        else:
            print(f"[DEBUG] 未找到匹配的日程: {old_datetime} {old_task}")
            return False
    
    def delete_schedule(self, datetime_str, task):
        """删除日程"""
        print(f"[DEBUG] 删除日程: 时间={datetime_str}, 任务={task}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schedules WHERE datetime = ? AND task = ?', (datetime_str, task))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        if rows_affected > 0:
            # 从已提醒集合中移除
            task_id = f"{datetime_str}-{task}"
            self.reminded_schedules.discard(task_id)
            print(f"[DEBUG] 日程删除成功: {datetime_str} {task}")
            return True
        else:
            print(f"[DEBUG] 未找到匹配的日程: {datetime_str} {task}")
            return False
    
    def find_schedules(self, task_keyword=None, datetime_str=None):
        """查找日程，支持按任务关键词或时间查找"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if task_keyword and datetime_str:
            cursor.execute('SELECT datetime, task FROM schedules WHERE task LIKE ? AND datetime = ?',
                         (f'%{task_keyword}%', datetime_str))
        elif task_keyword:
            cursor.execute('SELECT datetime, task FROM schedules WHERE task LIKE ?', (f'%{task_keyword}%',))
        elif datetime_str:
            cursor.execute('SELECT datetime, task FROM schedules WHERE datetime = ?', (datetime_str,))
        else:
            cursor.execute('SELECT datetime, task FROM schedules')
        
        schedules = [{"datetime": row[0], "task": row[1]} for row in cursor.fetchall()]
        conn.close()
        return schedules
    
    def delete_all_schedules(self):
        """删除所有日程"""
        print("[DEBUG] 删除所有日程")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schedules')
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        
        # 清空已提醒集合
        self.reminded_schedules.clear()
        
        print(f"[DEBUG] 已删除 {rows_affected} 个日程")
        return rows_affected
    
    def add_schedule(self, time_str, task, pushplus_notify=False, repeat_type='once'):
        print(f"[DEBUG] 添加日程: 时间={time_str}, 任务={task}, 微信通知={pushplus_notify}, 重复类型={repeat_type}")
        
        # 将时间字符串转换为完整的日期时间
        now = datetime.now()
        try:
            # 尝试解析时间
            time_parts = time_str.split(':')
            if len(time_parts) == 3:
                hour, minute, second = map(int, time_parts)
                schedule_datetime = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
                # 如果时间已过，设置为明天
                if schedule_datetime < now:
                    from datetime import timedelta
                    schedule_datetime += timedelta(days=1)
                datetime_str = schedule_datetime.strftime('%Y-%m-%d %H:%M:%S')
            else:
                datetime_str = time_str
        except:
            datetime_str = time_str
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO schedules (datetime, task, pushplus_notify, repeat_type) VALUES (?, ?, ?, ?)',
                      (datetime_str, task, 1 if pushplus_notify else 0, repeat_type))
        conn.commit()
        conn.close()
        print(f"[DEBUG] 日程已存入数据库: {datetime_str}, 重复类型: {repeat_type}")
    
    def create_next_repeat_schedule(self, current_datetime_str, task, pushplus_notify, repeat_type):
        """为重复日程创建下一次提醒"""
        from datetime import timedelta
        try:
            current_dt = datetime.strptime(current_datetime_str, '%Y-%m-%d %H:%M:%S')
            
            if repeat_type == 'daily':
                next_dt = current_dt + timedelta(days=1)
            elif repeat_type == 'weekly':
                next_dt = current_dt + timedelta(weeks=1)
            elif repeat_type == 'monthly':
                # 简单处理：加30天
                next_dt = current_dt + timedelta(days=30)
            elif repeat_type == 'yearly':
                next_dt = current_dt + timedelta(days=365)
            else:
                return
            
            next_datetime_str = next_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO schedules (datetime, task, pushplus_notify, repeat_type) VALUES (?, ?, ?, ?)',
                          (next_datetime_str, task, 1 if pushplus_notify else 0, repeat_type))
            conn.commit()
            conn.close()
            print(f"[DEBUG] 创建下一次重复日程: {next_datetime_str}, 类型: {repeat_type}")
        except Exception as e:
            print(f"[ERROR] 创建重复日程失败: {e}")
        
    def remind(self, task, pushplus_notify=False):
        # AI润色提醒文本
        polished_text = f"提醒：{task}"
        if self.ai_chat_callback:
            try:
                prompt = f"请以专业秘书的口吻，将以下提醒内容润色成完整的提醒语句。要求：1)必须包含完整的提醒内容 2)语气礼貌专业 3)直接输出润色后的语句，不要有任何解释或多余文字。提醒内容：{task}"
                ai_response = self.ai_chat_callback(prompt)
                # 智能提取润色后的文本
                polished_text = ai_response.strip()
                
                # 去除所有类型的引号包裹（包括中英文引号）
                import re
                # 先尝试提取引号内的内容
                quoted_match = re.search(r'["""\'\'](.*?)["""\'\']', polished_text, re.DOTALL)
                if quoted_match:
                    polished_text = quoted_match.group(1).strip()
                else:
                    # 如果没有引号，去除首尾的引号字符
                    polished_text = polished_text.strip('"\'""\'\'')
                
                # 确保文本不为空
                if not polished_text or len(polished_text.strip()) == 0:
                    polished_text = f"提醒：{task}"
                
                print(f"[AI润色] {polished_text}")
            except Exception as e:
                print(f"[AI润色错误] {e}")
                polished_text = f"提醒：{task}"
        
        # 使用 subprocess 调用自定义通知脚本（使用润色后的文本）
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            script_path = os.path.join(project_root, 'services', 'custom_notification.py')
            subprocess.Popen([sys.executable, script_path, polished_text])
            print(f"[通知] 自定义通知已发送: {polished_text}")
        except Exception as e:
            print(f"[通知错误] 自定义通知失败: {e}")
            self._console_notification(polished_text)
        
        # 语音播报
        if self.speak_callback and polished_text:
            try:
                self.speak_callback(polished_text)
            except Exception as e:
                print(f"[语音错误] 语音回调失败: {e}")
        
        print(f"[提醒] {polished_text}")
        
        # PushPlus通知
        if pushplus_notify:
            try:
                self.pushplus.send_notification("日程提醒", task)
            except Exception as e:
                print(f"[PushPlus Error] 发送通知失败: {e}")
    
    def _console_notification(self, task):
        """备用控制台通知方法"""
        try:
            # 在Windows上使用系统 beep 吸引注意
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            try:
                # 跨平台的beep
                print('\a')  # ASCII bell character
            except:
                pass
        
        # 打印醒目的提醒信息
        print("=" * 50)
        print(f"🔔 AI助手提醒")
        print(f"任务: {task}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
    def start(self):
        self.running = True
        
        def run():
            last_remind_time = {}  # 记录每个任务的最后提醒时间
            
            while self.running:
                schedules = self.load_schedules()
                now = datetime.now()
                current_datetime_str = now.strftime('%Y-%m-%d %H:%M:%S')
                
                for item in schedules:
                    schedule_datetime = item['datetime']
                    task = item['task']
                    pushplus_notify = item.get('pushplus_notify', 0)
                    repeat_type = item.get('repeat_type', 'once')
                    task_id = f"{schedule_datetime}-{task}"
                    
                    # 如果已经完成所有提醒，跳过
                    if task_id in self.reminded_schedules:
                        continue
                    
                    # 检查是否到达提醒时间
                    if schedule_datetime <= current_datetime_str:
                        # 获取当前提醒次数
                        current_count = self.reminder_counts.get(task_id, 0)
                        
                        # 如果还没达到重复次数
                        if current_count < config.REMINDER_REPEAT_COUNT:
                            should_remind = False
                            
                            if current_count == 0:
                                # 首次提醒
                                should_remind = True
                            else:
                                # 检查距离上次提醒是否已过间隔时间
                                if task_id in last_remind_time:
                                    elapsed = (now - last_remind_time[task_id]).total_seconds()
                                    if elapsed >= config.REMINDER_REPEAT_INTERVAL:
                                        should_remind = True
                                else:
                                    # 如果没有上次提醒时间，也提醒（防止数据丢失）
                                    should_remind = True
                            
                            if should_remind:
                                try:
                                    self.remind(task, pushplus_notify=bool(pushplus_notify))
                                    self.reminder_counts[task_id] = current_count + 1
                                    last_remind_time[task_id] = now
                                    
                                    # 达到重复次数后标记为已提醒
                                    if self.reminder_counts[task_id] >= config.REMINDER_REPEAT_COUNT:
                                        self.reminded_schedules.add(task_id)
                                        self.mark_as_reminded(schedule_datetime, task)
                                        
                                        # 如果是重复日程，创建下一次提醒
                                        if repeat_type != 'once':
                                            self.create_next_repeat_schedule(schedule_datetime, task, pushplus_notify, repeat_type)
                                except Exception as e:
                                    print(f"[Schedule Error] 提醒失败: {e}")
                
                time.sleep(1)
        
        threading.Thread(target=run, daemon=True).start()
    
    def stop(self):
        self.running = False