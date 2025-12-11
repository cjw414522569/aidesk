import tkinter as tk
import sys
import threading

class CustomNotification(tk.Tk):
    def __init__(self, title, message, auto_close=False):
        super().__init__()
        self.title_text = title
        self.message_text = message
        self.auto_close = auto_close
        self.overrideredirect(True)  # 移除窗口边框

        # 设置窗口样式
        self.config(bg="#2E2E2E", bd=1, relief="solid")
        
        # 获取屏幕尺寸以计算位置
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 窗口尺寸
        window_width = 350
        window_height = 120
        
        # 计算窗口位置（右上角）
        x = screen_width - window_width - 20
        y = 40
        
        self.geometry(f'{window_width}x{window_height}+{x}+{y}')

        # 添加组件
        self.create_widgets()

        # 设置窗口总在最前
        self.attributes("-topmost", True)

        # 如果需要自动关闭，5秒后关闭
        if self.auto_close:
            self.after(5000, self.close_window)

        # 绑定点击事件以关闭窗口
        self.bind("<Button-1>", self.on_click)

    def create_widgets(self):
        # 标题标签
        title_label = tk.Label(self, text=self.title_text, bg="#2E2E2E", fg="#FFFFFF", font=("Arial", 14, "bold"))
        title_label.pack(pady=(10, 5), padx=10, anchor="w")
        title_label.bind("<Button-1>", self.on_click)

        # 消息标签
        message_label = tk.Label(self, text=self.message_text, bg="#2E2E2E", fg="#CCCCCC", font=("Arial", 12), wraplength=330, justify="left")
        message_label.pack(pady=5, padx=10, anchor="w")
        message_label.bind("<Button-1>", self.on_click)

        # 关闭按钮
        close_button = tk.Button(self, text="×", bg="#2E2E2E", fg="#FFFFFF", command=self.close_window, relief="flat", font=("Arial", 14))
        close_button.place(x=320, y=5)

    def on_click(self, event):
        self.close_window()

    def close_window(self):
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
        # 检查是否有第二个参数指定自动关闭
        auto_close = len(sys.argv) > 2 and sys.argv[2] == "auto_close"
    else:
        message = "这是一个测试提醒。"
        auto_close = False
        
    app = CustomNotification("🔔 AI助手提醒", message, auto_close=auto_close)
    app.mainloop()