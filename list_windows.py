#!/usr/bin/env python3
"""
Mac 窗口列表查看工具
用于查找游戏窗口的实际标题
"""
import mac_window

def main():
    print("=" * 60)
    print("当前所有可见窗口列表")
    print("=" * 60)
    
    windows = mac_window.getAllWindows()
    if not windows:
        print("未找到任何窗口（可能需要授予辅助功能权限）")
        return
    
    # 按应用名分组
    apps = {}
    for w in windows:
        app = w._app if hasattr(w, '_app') else 'Unknown'
        if app not in apps:
            apps[app] = []
        apps[app].append(w)
    
    for app, wins in sorted(apps.items()):
        print(f"\n【应用】{app}")
        for w in wins:
            title = w.title if w.title else "(无标题)"
            app_name = getattr(w, '_app', '')
            print(f"  - 标题: '{title}'")
            print(f"    进程: '{app_name}'")
            print(f"    位置: ({w.left}, {w.top}) 尺寸: {w.width}x{w.height}")
    
    print("\n" + "=" * 60)
    print("请确认游戏窗口的标题，并修改 config_mac.jsonc 中的 game_title")
    print("=" * 60)

if __name__ == "__main__":
    main()
