"""
微信自动发送模块 — 通过 wxauto4 操作微信桌面客户端发送消息

使用前提:
- Windows 系统
- 微信桌面客户端已登录并在线
- wxauto4 已安装 (pip install wxauto4)
"""

import logging
import time

logger = logging.getLogger(__name__)

try:
    from wxauto4 import WeChat
    WXAUTO_AVAILABLE = True
except ImportError:
    WXAUTO_AVAILABLE = False
    logger.warning("wxauto4 未安装，微信发送功能不可用")

try:
    import pythoncom
    PYTHONCOM_AVAILABLE = True
except ImportError:
    PYTHONCOM_AVAILABLE = False
    logger.warning("pythoncom 未安装，微信发送功能可能不稳定")


def _com_initialize():
    """在当前线程初始化 Windows COM（wxauto4/UI Automation 需要）"""
    if PYTHONCOM_AVAILABLE:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass  # 已经初始化过会抛异常，忽略即可


def _com_uninitialize():
    """释放当前线程的 COM 初始化"""
    if PYTHONCOM_AVAILABLE:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _find_in_session_list(wx, contact_name):
    """
    在会话列表中查找联系人，支持多种匹配方式：
    1. 完全匹配（不区分大小写）
    2. 包含匹配（备注名/昵称中包含目标名）
    3. 目标名包含会话名（适用于长名匹配短备注）
    """
    try:
        sessions = wx.SessionBox.get_session()
    except Exception:
        sessions = []

    target_name = contact_name.strip().lower()
    candidates = []

    for s in sessions:
        if not hasattr(s, "name"):
            continue
        session_name = s.name.strip()
        session_lower = session_name.lower()

        # 完全匹配
        if session_lower == target_name:
            return s

        # 备注名包含目标名
        if target_name in session_lower:
            candidates.append((len(session_lower) - len(target_name), s))

        # 目标名包含备注名（目标可能是 "张三(工作)", 备注是 "张三"）
        if session_lower and session_lower in target_name:
            candidates.append((len(target_name) - len(session_lower), s))

    if candidates:
        # 选匹配度最高的（差异最小）
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    return None


def _open_chat_safely(wx, contact_name):
    """
    安全打开联系人聊天窗口，尽量避免按回车进入"搜一搜"。
    优先从会话列表点击；若不在会话列表中，再使用 ChatWith 精确匹配。
    """
    # 1. 优先从会话列表匹配并点击
    target = _find_in_session_list(wx, contact_name)
    if target:
        logger.info(f"在会话列表中找到 '{contact_name}'，直接点击打开")
        target.click()
        time.sleep(0.6)
        return True

    # 2. 会话列表中没有，使用 ChatWith 搜索（先精确匹配）
    logger.warning(f"会话列表中未找到 '{contact_name}'，尝试 ChatWith 搜索")
    try:
        # exact=True 尽量打开唯一匹配联系人，避免按回车进入搜一搜
        wx.ChatWith(who=contact_name, exact=True)
        time.sleep(0.6)
        return True
    except Exception:
        logger.warning(f"ChatWith(exact=True) 失败，回退到模糊搜索")

    # 3. 精确匹配失败，回退到模糊搜索
    try:
        wx.ChatWith(who=contact_name, exact=False)
        time.sleep(0.6)
        return True
    except Exception as e:
        logger.error(f"ChatWith 搜索失败: {e}")
        return False


def _verify_chat_window(wx, expected_name):
    """
    尝试验证当前聊天窗口的联系人是否为预期联系人。
    如果验证失败，返回 False，避免消息发错对象。
    """
    try:
        # wxauto4 常见方法：获取当前聊天窗口名称
        current_name = wx.GetCurrentChatName()
        if current_name and expected_name.lower() in current_name.lower():
            return True
    except Exception:
        # 如果 API 不存在或调用失败，跳过验证
        pass
    return True


def send_message(contact_name, message_text):
    """
    通过微信发送消息给指定联系人

    Args:
        contact_name: 微信联系人名称（备注名或昵称）
        message_text: 要发送的消息文本

    Returns:
        dict: {"status": "success"/"error", "contact": str, "message": str}
    """
    if not WXAUTO_AVAILABLE:
        return {
            "status": "error",
            "contact": contact_name,
            "error": "wxauto4 未安装",
        }

    _com_initialize()
    try:
        wx = WeChat()

        # 步骤1：切换到聊天页签
        wx.SwitchToChat()
        time.sleep(0.2)

        # 步骤2：安全打开联系人聊天窗口
        opened = _open_chat_safely(wx, contact_name)
        if not opened:
            return {
                "status": "error",
                "contact": contact_name,
                "error": f"未找到联系人 '{contact_name}'，请确认名称正确",
            }

        # 步骤3：验证当前聊天窗口（如 API 可用）
        if not _verify_chat_window(wx, contact_name):
            logger.error(f"当前聊天窗口不是 '{contact_name}'，取消发送")
            return {
                "status": "error",
                "contact": contact_name,
                "error": f"打开联系人 '{contact_name}' 后验证失败，消息未发送",
            }

        # 步骤4：发送消息（who 留空，发送给当前已打开的聊天窗口）
        wx.SendMsg(msg=message_text)

        logger.info(f"消息已发送给 {contact_name}")
        return {
            "status": "success",
            "contact": contact_name,
            "message": message_text,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"发送失败: {error_msg}")

        # 判断错误类型
        if "登录" in error_msg or "login" in error_msg.lower():
            return {
                "status": "error",
                "contact": contact_name,
                "error": "微信未登录，请先打开并登录微信桌面客户端",
            }
        elif "找不到" in error_msg or "not found" in error_msg.lower():
            return {
                "status": "error",
                "contact": contact_name,
                "error": f"未找到联系人 '{contact_name}'，请确认名称正确",
            }
        else:
            return {
                "status": "error",
                "contact": contact_name,
                "error": error_msg,
            }
    finally:
        _com_uninitialize()


def check_wechat_status():
    """检查微信客户端状态"""
    if not WXAUTO_AVAILABLE:
        return {"available": False, "reason": "wxauto4 未安装"}

    _com_initialize()
    try:
        wx = WeChat()
        return {"available": True, "message": "微信客户端已连接"}
    except Exception as e:
        return {"available": False, "reason": str(e)}
    finally:
        _com_uninitialize()


if __name__ == "__main__":
    if WXAUTO_AVAILABLE:
        print("wxauto4 已安装，可以发送微信消息")
        status = check_wechat_status()
        print(f"微信状态: {status}")
    else:
        print("wxauto4 未安装")
