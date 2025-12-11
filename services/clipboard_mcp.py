import pyperclip

class ClipboardMCP:
    def get_clipboard(self):
        """获取剪贴板内容"""
        try:
            content = pyperclip.paste()
            return content if content else "剪贴板为空"
        except Exception as e:
            return f"获取剪贴板失败: {str(e)}"
    
    def set_clipboard(self, text):
        """设置剪贴板内容"""
        try:
            pyperclip.copy(text)
            return f"已复制到剪贴板: {text[:50]}..."
        except Exception as e:
            return f"设置剪贴板失败: {str(e)}"