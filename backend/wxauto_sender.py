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

        # 步骤2：从会话列表中直接查找并点击联系人（不走搜索框，避免触发"搜一搜"）
        sessions = wx.SessionBox.get_session()
        target = None
        for s in sessions:
            if contact_name.lower() == s.name.lower():
                target = s
                break

        if target:
            # 在会话列表中找到了，直接点击打开聊天
            target.click()
            time.sleep(0.5)
        else:
            # 会话列表中没有，回退到 ChatWith 搜索
            # 注意：ChatWith 内部可能按回车导致"搜一搜"，仅作降级
            logger.warning(f"会话列表中未找到 '{contact_name}'，回退到搜索模式")
            wx.ChatWith(who=contact_name, exact=False)
            time.sleep(0.5)

        # 步骤3：发送消息（who 留空，发送给当前已打开的聊天窗口）
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
