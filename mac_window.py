"""
Mac 窗口管理模块
替代 Windows 上的 pygetwindow，使用 Quartz + AppleScript 获取和控制窗口
"""

import subprocess
import time
from typing import List, Dict, Optional

try:
    import Quartz
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False


class MacWindow:
    """模拟 pygetwindow 的 Window 对象"""
    def __init__(self, window_info: dict):
        self._info = window_info
        self.title = window_info.get('title', '')
        self.left = window_info.get('x', 0)
        self.top = window_info.get('y', 0)
        self.width = window_info.get('width', 0)
        self.height = window_info.get('height', 0)
        self._pid = window_info.get('pid', 0)
        self._app = window_info.get('app', '')
    
    @property
    def isActive(self) -> bool:
        """检查窗口是否在前台（近似判断）"""
        try:
            script = f'''
            tell application "System Events"
                set p to first process whose unix id is {self._pid}
                return frontmost of p
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=3
            )
            return 'true' in result.stdout.lower()
        except Exception:
            return False
    
    @property
    def isMinimized(self) -> bool:
        """检查窗口是否最小化"""
        try:
            script = f'''
            tell application "System Events"
                set p to first process whose unix id is {self._pid}
                tell p
                    set w to window 1
                    return value of attribute "AXMinimized" of w
                end tell
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=3
            )
            return 'true' in result.stdout.lower()
        except Exception:
            return False
    
    def restore(self):
        """恢复最小化的窗口"""
        try:
            script = f'''
            tell application "System Events"
                set p to first process whose unix id is {self._pid}
                tell p
                    set w to window 1
                    set value of attribute "AXMinimized" of w to false
                end tell
            end tell
            '''
            subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=3
            )
        except Exception:
            pass
    
    def activate(self):
        """激活窗口（设置为前台）"""
        try:
            # 先尝试用 AppleScript 激活
            script = f'''
            tell application "System Events"
                set frontmost of the first process whose unix id is {self._pid} to true
            end tell
            '''
            subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=3
            )
        except Exception:
            pass


def _get_window_title_via_applescript(pid: int, app_name: str) -> str:
    """使用 AppleScript 获取窗口标题（备用方案）"""
    try:
        script = f'''
        tell application "System Events"
            set p to first process whose unix id is {pid}
            tell p
                if (count of windows) > 0 then
                    return name of window 1
                else
                    return ""
                end if
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _get_windows_quartz() -> List[Dict]:
    """使用 Quartz 获取所有窗口，并用 AppleScript 补充标题"""
    windows = []
    if not HAS_QUARTZ:
        return windows
    
    # 使用 OptionAll 而不是 OnScreenOnly，因为 macOS 上 OnScreenOnly 经常遗漏
    # 实际可见的窗口（特别是被遮挡或在不同 Space 的窗口）
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID
    )
    
    seen_pids = set()
    
    for win in window_list:
        pid = win.get(Quartz.kCGWindowOwnerPID, 0)
        app_name = win.get(Quartz.kCGWindowOwnerName, '')
        title = win.get(Quartz.kCGWindowName, '')
        bounds = win.get(Quartz.kCGWindowBounds, {})
        layer = win.get(Quartz.kCGWindowLayer, 0)
        
        w = int(bounds.get('Width', 0))
        h = int(bounds.get('Height', 0))
        x = int(bounds.get('X', 0))
        y = int(bounds.get('Y', 0))
        
        # 只保留普通应用窗口（layer==0），且尺寸合理
        if layer == 0 and w > 200 and h > 200 and pid > 0:
            # 如果 Quartz 没有返回标题，尝试用 AppleScript 获取
            if not title:
                title = _get_window_title_via_applescript(pid, app_name)
            
            # 每个 PID 只保留一个主窗口（最大的那个）
            if pid in seen_pids:
                # 更新为更大的窗口
                for existing in windows:
                    if existing['pid'] == pid:
                        if w * h > existing['width'] * existing['height']:
                            existing.update({
                                'title': title,
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h,
                            })
                        break
            else:
                seen_pids.add(pid)
                windows.append({
                    'pid': pid,
                    'app': app_name,
                    'title': title,
                    'x': x,
                    'y': y,
                    'width': w,
                    'height': h,
                })
    return windows


def getAllWindows() -> List[MacWindow]:
    """获取所有窗口（兼容 pygetwindow API）"""
    raw_windows = _get_windows_quartz()
    return [MacWindow(w) for w in raw_windows]


def find_window(title_keyword: str) -> Optional[MacWindow]:
    """模糊查找窗口（支持标题或进程名匹配）"""
    windows = getAllWindows()
    
    # 先尝试标题匹配
    title_matches = [w for w in windows if title_keyword.lower() in w.title.lower()]
    if title_matches:
        return title_matches[0]
    
    # 再尝试进程名匹配
    app_matches = [w for w in windows if hasattr(w, '_app') and title_keyword.lower() in w._app.lower()]
    if app_matches:
        return app_matches[0]
    
    return None


def getWindowsWithTitle(title: str) -> List[MacWindow]:
    """根据标题获取窗口"""
    all_wins = getAllWindows()
    return [w for w in all_wins if title.lower() in w.title.lower()]


def getActiveWindow() -> Optional[MacWindow]:
    """获取当前前台窗口"""
    try:
        script = '''
        tell application "System Events"
            set p to first process whose frontmost is true
            set n to name of p
            set pid to unix id of p
            return n & "|" & pid
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            if len(parts) >= 2:
                app_name = parts[0]
                pid = int(parts[1])
                # 查找该进程的窗口
                for w in getAllWindows():
                    if w._pid == pid:
                        return w
        return None
    except Exception:
        return None
