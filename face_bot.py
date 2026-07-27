"""
face_bot.py — 监控屏幕,自动点拍照按钮+喂本地照片
原理:模板匹配(matchTemplate)+ WinAPI 鼠标操作
v2.2 — 修复文件对话框路径输入(改用剪贴板粘贴) + Enter 加固
"""
import os
import sys
import time
import random
import logging
from pathlib import Path

# ============================================================
# 高 DPI 感知声明(必须放在所有 import 之前)
# Win11 180% 缩放屏不修这个会导致所有坐标偏 1.8x
# ============================================================
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def app_path(rel):
    if getattr(sys, "frozen", False):
        external = Path(sys.executable).parent / rel
        if external.exists():
            return external
        return Path(sys._MEIPASS) / rel
    else:
        return Path(__file__).parent / rel


# ============== 依赖 ==============
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except ImportError:
    print("需要: pip install pyautogui")
    sys.exit(1)

from PIL import ImageGrab

# ============== 路径 ==============
APP_DIR  = app_path(".")
TPL_DIR  = APP_DIR / "templates"
FACE_DIR = APP_DIR / "faces"
if getattr(sys, "frozen", False):
    LOG_DIR  = Path(sys.executable).parent / "logs"
else:
    LOG_DIR  = APP_DIR / "logs"

TPL_CAPTURE_BTN = TPL_DIR / "capture_button.png"
TPL_DIALOG_BOX  = TPL_DIR / "file_dialog.png"

LOG_DIR.mkdir(exist_ok=True)
TPL_DIR.mkdir(exist_ok=True)
FACE_DIR.mkdir(exist_ok=True)

# ============== 日志(强制 UTF-8) ==============
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "face_bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("face_bot")

# ============== 配置 ==============
CONFIG = {
    "scan_interval_ms": 1500,
    "scan_confidence": 0.7,
    "after_btn_click_wait_ms": 2500,
    "after_path_enter_wait_ms": 1200,
    "after_open_wait_ms": 5000,
    "post_inject_settle_ms": 3000,
    "scan_region": None,
}


# ============== 工具函数 ==============
def list_faces():
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return sorted([p for p in FACE_DIR.iterdir() if p.suffix.lower() in exts])


def pick_face():
    files = list_faces()
    if not files:
        raise FileNotFoundError(f"{FACE_DIR} 是空的")
    return random.choice(files)


def safe_screenshot(tag):
    try:
        path = LOG_DIR / f"{tag}_{int(time.time())}.png"
        ImageGrab.grab().save(path)
        return path
    except Exception as e:
        log.warning("截图失败 %s: %s", tag, e)
        return None


def scroll_capture_popup():
    try:
        x, y = pyautogui.size().width // 2, pyautogui.size().height // 2
        pyautogui.moveTo(x, y)
        pyautogui.scroll(-300)
        time.sleep(0.4)
        pyautogui.scroll(-300)
        time.sleep(0.4)
    except Exception as e:
        log.debug("滚动失败: %s", e)


def find_template(template_path, confidence=None, region=None, timeout=15):
    conf = confidence or CONFIG["scan_confidence"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            box = pyautogui.locateOnScreen(
                str(template_path),
                confidence=conf,
                grayscale=True,
                region=region,
            )
            if box:
                cx, cy = pyautogui.center(box)
                log.info(f"找到模板 {template_path.name} @({cx},{cy})")
                return cx, cy
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            log.warning("locateOnScreen 异常: %s", e)
        time.sleep(CONFIG["scan_interval_ms"] / 1000)
    return None


def click(xy):
    x, y = xy
    pyautogui.moveTo(
        x + random.randint(-3, 3),
        y + random.randint(-3, 3),
        duration=random.uniform(0.08, 0.25),
    )
    pyautogui.click()


def inject_face_to_dialog(face_path: Path):
    """
    文件对话框双击缩略图(用模板匹配,不需要 OCR):
      1) Ctrl+L → 输入文件夹路径 → Enter(进文件夹)
      2) 等缩略图渲染
      3) 模板匹配:取\"文件名\"小图作为模板 → 双击中心
      4) 兜底:输入完整文件名 → Enter
    """
    folder = face_path.parent
    name = face_path.name

    # 1) 进文件夹
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.typewrite(str(folder), interval=0.03)
    time.sleep(0.4)
    pyautogui.press("enter")

    # 2) 等渲染
    time.sleep(3.5)

    # 3) 模板匹配找文件名 → 双击
    tpl_thumb = TPL_DIR / "file_thumb_name.png"
    click_xy = None
    if tpl_thumb.exists():
        click_xy = find_template(tpl_thumb, timeout=4)
    if click_xy:
        try:
            shot_path = LOG_DIR / f"file_dialog_match_{int(time.time())}.png"
            ImageGrab.grab().save(shot_path)
            log.info(f"  匹配后的屏幕截图: {shot_path}")
        except Exception:
            pass

        log.info(f"双击缩略图 {name} @ {click_xy}")
        x, y = click_xy
        y_icon = y
        log.info(f"  双击目标位置(模板中心):({x}, {y_icon})")

        import ctypes
        user32 = ctypes.windll.user32
        user32.SetCursorPos(int(x), int(y_icon))
        time.sleep(0.15)
        log.info(f"  SetCursorPos({x}, {y_icon}) OK")

        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP   = 0x0004
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.04)
        user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
        time.sleep(0.10)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.04)
        user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)
        log.info(f"  WinAPI 双击完成")
    else:
        log.warning(f"模板未找到或匹配失败 ({tpl_thumb}),降级输入文件名 + Enter")
        pyautogui.typewrite(name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")


# ============== 主循环 ==============
def main_loop():
    log.info("=" * 60)
    log.info("face_bot 启动")
    log.info("模板: %s", TPL_CAPTURE_BTN if TPL_CAPTURE_BTN.exists() else "(缺失!)")
    log.info("faces/ 照片: %d 张", len(list_faces()))
    log.info("终止方式:鼠标移到屏幕左上角 或 Ctrl+C")
    log.info("=" * 60)

    cycle = 0
    last_inject_ts = 0

    while True:
        cycle += 1
        cycle_start_ts = time.time()
        safe_screenshot("loop_start")

        if time.time() - last_inject_ts < CONFIG["post_inject_settle_ms"] / 1000:
            time.sleep(CONFIG["scan_interval_ms"] / 1000)
            continue

        log.info("--- 第 %d 轮扫屏 ---", cycle)

        popup_xy = find_template(TPL_DIR / "popup_header.png", timeout=2)
        if popup_xy is None:
            time.sleep(CONFIG["scan_interval_ms"] / 1000)
            continue

        log.info("=== 弹窗出现,准备操作 ===")
        scroll_capture_popup()
        time.sleep(0.8)

        btn_xy = find_template(TPL_CAPTURE_BTN, timeout=8)
        if btn_xy is None:
            log.warning("找不到拍照按钮,跳过")
            time.sleep(2)
            continue

        safe_screenshot("found_capture_btn")
        click(btn_xy)
        time.sleep(CONFIG["after_btn_click_wait_ms"] / 1000)
        safe_screenshot("after_btn_click")

        face = pick_face()
        log.info("选图: %s", face.name)
        try:
            inject_face_to_dialog(face)
        except Exception as e:
            log.error("注入失败: %s", e)
            continue

        time.sleep(CONFIG["after_open_wait_ms"] / 1000)
        safe_screenshot("after_upload_done")
        last_inject_ts = time.time()
        log.info("本轮完成 ✅")

        # 清理上一轮截图
        try:
            round_started_at = cycle_start_ts
            deleted = 0
            for f in LOG_DIR.iterdir():
                if f.suffix.lower() != ".png":
                    continue
                if f.stat().st_mtime < round_started_at:
                    f.unlink()
                    deleted += 1
            if deleted:
                log.info("清理上一轮 %d 张截图", deleted)
        except Exception as e:
            log.debug("清理截图失败: %s", e)


def clean_old_logs(days=7):
    if not LOG_DIR.exists():
        return
    cutoff = time.time() - days * 86400
    cleaned = 0
    for f in LOG_DIR.iterdir():
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                cleaned += 1
        except Exception:
            pass
    if cleaned:
        log.info("已清理 %d 个旧日志", cleaned)


def main():
    clean_old_logs(days=7)

    if not TPL_CAPTURE_BTN.exists() or not (TPL_DIR / "popup_header.png").exists():
        log.error("缺失模板: %s 或 popup_header.png", TPL_CAPTURE_BTN)
        sys.exit(2)
    if not list_faces():
        log.error("%s 是空的", FACE_DIR)
        sys.exit(2)

    try:
        main_loop()
    except KeyboardInterrupt:
        log.info("用户中止")
    except pyautogui.FailSafeException:
        log.warning("FailSafe 触发,自动退出")


if __name__ == "__main__":
    main()
