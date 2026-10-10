import sys
import time
import pythoncom

from wxauto4 import WeChat  # 免费版
# from wxautox4 import WeChat  # Plus版

# 默认测试目标，可通过命令行覆盖：python wx_test.py "Ding Zihan" "test msg"
target = sys.argv[1] if len(sys.argv) > 1 else "文件传输助手"
message = sys.argv[2] if len(sys.argv) > 2 else "你好，这是 wxauto 测试消息"

# 初始化 COM（UI Automation 需要）
pythoncom.CoInitialize()

try:
    # 初始化微信实例
    wx = WeChat()

    # 切换到聊天页签
    wx.SwitchToChat()
    time.sleep(0.2)

    # 从会话列表中直接查找并点击联系人（不走搜索框，避免"搜一搜"）
    sessions = wx.SessionBox.get_session()
    found = False
    for s in sessions:
        if target.lower() == s.name.lower():
            s.click()
            time.sleep(0.5)
            found = True
            print(f"在会话列表中找到 '{target}'，已点击打开")
            break

    if not found:
        print(f"会话列表中未找到 '{target}'，回退到 ChatWith 搜索")
        wx.ChatWith(target, exact=False)
        time.sleep(0.5)

    # 查看当前窗口信息
    chatinfo = wx.ChatInfo()
    print(f"当前窗口信息：{chatinfo}")

    # 发送消息
    if chatinfo.get('chat_name') == target:
        wx.SendMsg(message)
        print(f"已发送消息给 {target}: {message}")
    else:
        print(f"警告：当前聊天窗口 '{chatinfo.get('chat_name')}' 不是 '{target}'，未发送消息")

    # 获取当前聊天窗口消息
    msgs = wx.GetAllMessage()
    for msg in msgs:
        print(msg.raw)
finally:
    pythoncom.CoUninitialize()
