#!/usr/bin/env python3
"""
寰球救援抢房脚本 - 极速版
策略：固定位置疯狂点击，列表刷新后自然能抢到
"""

import os
import sys
import time
import random
import json5
import cv2
import numpy as np
import pyautogui
import logging
from datetime import datetime
from mss import mss
from PIL import Image

import mac_window as gw

# ============ 全局配置 ============
CONFIG_PATH = "config_mac.jsonc"
config = {}
DEBUG_MODE = True

# ============ 日志设置 ============
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger()

# ============ 基础功能 ============

def load_config(path):
    global config
    with open(path, 'r', encoding='utf-8') as f:
        config = json5.load(f)
    log.info(f"配置加载成功: {path}")
    return config

def get_game_window():
    title = config.get("game_title", "微信")
    windows = gw.getAllWindows()
    matches = []
    for w in windows:
        if title.lower() in w.title.lower() or (hasattr(w, '_app') and title.lower() in w._app.lower()):
            matches.append(w)
    if not matches:
        return None
    best = max(matches, key=lambda w: w.width * w.height)
    if best.isMinimized:
        best.restore()
        time.sleep(0.5)
    return {
        "window": best,
        "left": best.left,
        "top": best.top,
        "width": best.width,
        "height": best.height
    }

def activate_window(win):
    try:
        win["window"].activate()
        time.sleep(0.5)
        return True
    except Exception as e:
        log.warning(f"激活窗口失败: {e}")
        return False

def screenshot(win):
    try:
        with mss() as sct:
            monitor = {
                "top": win["top"],
                "left": win["left"],
                "width": win["width"],
                "height": win["height"]
            }
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        log.error(f"截图失败: {e}")
        return None

def match_template(screen, template_name, threshold=0.6):
    template_path = os.path.join(config.get("template_root", "templates"), template_name)
    if not os.path.exists(template_path):
        return False, None, 0
    template = cv2.imread(template_path)
    if template is None:
        return False, None, 0
    if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
        return False, None, 0
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        h, w = template.shape[:2]
        pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
        return True, pos, max_val
    return False, None, max_val

def match_multi(screen, template_names, threshold=0.6):
    best_val = -1
    best_pos = None
    for name in template_names:
        matched, pos, val = match_template(screen, name, threshold)
        if matched and val > best_val:
            best_val = val
            best_pos = pos
    return best_pos is not None, best_pos, best_val

def click(win, x, y, desc=""):
    try:
        abs_x = win["left"] + x
        abs_y = win["top"] + y
        pyautogui.moveTo(abs_x, abs_y, duration=random.uniform(0.05, 0.1))
        pyautogui.click()
        if desc:
            log.info(f"点击 {desc}: ({x},{y})")
        return True
    except Exception as e:
        log.error(f"点击失败: {e}")
        return False

def click_ratio(win, rx, ry, desc=""):
    x = int(win["width"] * rx)
    y = int(win["height"] * ry)
    return click(win, x, y, desc)

# ============ 界面检测 ============

def is_recruit_channel(win):
    """检测是否在招募频道"""
    screen = screenshot(win)
    if screen is None:
        return False
    matched, _, val = match_multi(screen, ["hq_recruit_title.png"], 0.5)
    if matched:
        return True
    matched, _, val = match_multi(screen, ["hq_rescue_card.png"], 0.5)
    if matched:
        return True
    return False

def is_in_room(win):
    """检测是否已进入房间"""
    screen = screenshot(win)
    if screen is None:
        return False
    matched, _, _ = match_multi(screen, config.get("hq_start_templates", ["hq_start.png", "hq_start2.png"]), 0.5)
    if matched:
        return True
    matched, _, _ = match_multi(screen, config.get("hq_team_up_title_templates", ["hq_invite_title.png"]), 0.5)
    if matched:
        return True
    return False

# ============ 抢房核心 ============

def snipe_loop(win):
    """
    抢房策略：在招募频道固定位置疯狂点击
    列表刷新后自然能抢到新房间
    """
    attempt = 0
    success_count = 0
    
    # 固定点击位置：第一个寰球救援卡片的中心区域
    # 基于截图分析：卡片在窗口中间偏右，偏上位置
    click_rx = 0.65  # 水平：中间偏右
    click_ry = 0.36  # 垂直：偏上（第一个卡片位置）
    
    log.info(f"抢房固定点击位置: ({click_rx}, {click_ry})")
    log.info("开始疯狂抢房模式...")
    
    while True:
        attempt += 1
        
        # 每隔10次打印一次状态
        if attempt % 10 == 0:
            log.info(f"已尝试 {attempt} 次，成功 {success_count} 次")
        
        # 1. 确保在招募频道
        if not is_recruit_channel(win):
            log.warning("不在招募频道，等待...")
            time.sleep(2)
            continue
        
        # 2. 快速点击固定位置（不截图、不匹配，直接点）
        click_ratio(win, click_rx, click_ry, f"抢房#{attempt}")
        
        # 3. 短暂等待，看是否进入房间
        time.sleep(0.8)
        
        # 4. 检测是否成功进入房间
        if is_in_room(win):
            success_count += 1
            log.info(f"🎉 成功进入房间！（第 {success_count} 次成功）")
            time.sleep(0.5)
            
            # 点击准备/开始
            click_ratio(win, 0.5, 0.75, "准备/开始")
            time.sleep(5)
            
            log.info("游戏进行中...等待结束")
            # 简化版：等待一段时间后认为游戏结束
            # 实际需要根据游戏时长调整，寰球救援通常 3-5 分钟
            time.sleep(30)
            
            log.info("本轮完成，继续抢房！")
            time.sleep(1)
        else:
            # 点击空白处关闭可能的弹窗（如"卡片已失效"）
            # 快速点击，不等待
            pass
        
        # 5. 极短间隔后继续下一轮（0.2秒）
        time.sleep(0.2)

# ============ 入口 ============

def main():
    log.info("=" * 50)
    log.info("寰球救援抢房脚本 - 极速版")
    log.info("策略: 固定位置疯狂点击")
    log.info("=" * 50)
    
    load_config(CONFIG_PATH)
    
    log.info("正在查找游戏窗口...")
    win = None
    while win is None:
        win = get_game_window()
        if win is None:
            log.warning("未找到窗口，3秒后重试...")
            time.sleep(3)
    
    log.info(f"找到窗口: {win['width']}x{win['height']}")
    
    if not activate_window(win):
        log.error("无法激活窗口")
        return
    
    log.info("窗口已激活！")
    log.info("⚠️ 请确保游戏已在招募频道界面")
    log.info("3秒后开始抢房...")
    time.sleep(3)
    
    try:
        snipe_loop(win)
    except KeyboardInterrupt:
        log.info("\n用户停止脚本")
    except Exception as e:
        log.error(f"脚本异常: {e}")
        import traceback
        log.error(traceback.format_exc())

if __name__ == "__main__":
    main()
