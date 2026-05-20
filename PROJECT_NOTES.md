# 项目理解与开发笔记

> 本文档记录本项目（向僵尸开炮自动化脚本）的整体架构、改造过程、已知问题和后续待办事项。
> 供后续在其他 Mac 设备上继续开发和调试时参考。

---

## 一、项目背景与目标

### 1.1 游戏
- **名称**：向僵尸开炮
- **平台**：微信小程序（Mac 版微信内运行）
- **运行方式**：用户通过 Mac 版微信打开小程序，游戏画面嵌套在微信窗口内

### 1.2 脚本目标
用户核心需求：
1. **自动抢环球救援**：自动刷新寰球救援房间列表，加入别人的房间，自动准备/开始，打完自动退出，循环抢房
2. **自动化游戏流程**：图像识别 + 模拟点击，实现无人值守

### 1.3 运行模式
脚本通过 `--play` 参数区分模式：
- `python3 start.py --play master` — 普通闯关模式（自己打关卡）
- `python3 start.py --play hq` — 寰球模式（组队打寰球救援）

寰球模式下又分两种子模式（由 `config_mac.jsonc` 中的 `hq_snipe_mode` 控制）：
- `hq_snipe_mode: true` — **抢房模式**（加入别人发布的房间）
- `hq_snipe_mode: false` — **自建房间模式**（自己发布招募等队友加入）

---

## 二、项目结构

```
xjskp-auto/
├── start.py              # 主程序入口（~2600行，所有核心逻辑）
├── mac_window.py         # Mac 窗口管理模块（替代 Windows 的 pygetwindow）
├── config_mac.jsonc      # Mac 版配置文件（json5 格式，支持注释）
├── config.jsonc          # 原 Windows 版配置文件（保留备用）
├── list_windows.py       # 工具脚本：列出当前所有窗口的进程名和尺寸
├── requirements.txt      # Python 依赖列表
├── README_MAC.md         # Mac 用户使用文档
├── PROJECT_NOTES.md      # 本文档（开发者笔记）
├── .gitignore            # Git 忽略规则
├── templates/            # 图像识别模板目录（*.png）
│   ├── start.png
│   ├── pause.png / pause2.png
│   ├── exit_btn.png / exit_btn2.png
│   ├── back_btn.png / back_btn2.png
│   ├── skill_template.png / skill_template2.png
│   ├── invite.png / invite2.png
│   ├── hq_invite_title.png
│   ├── send_invite.png / send_invite2.png
│   ├── hq_start.png / hq_start2.png
│   ├── hq_skill.png / hq_skill2.png
│   ├── activated_skills.png
│   ├── hq_lunpan.png
│   └── ...（其他模板）
├── venv/                 # Python 虚拟环境（.gitignore 排除，不提交）
└── logs/                 # 运行日志（.gitignore 排除，不提交）
```

---

## 三、核心架构

### 3.1 技术栈
| 库 | 用途 | Mac 兼容性 |
|----|------|-----------|
| `pyautogui` | 模拟鼠标移动和点击 | 支持 |
| `mss` | 屏幕截图 | 支持 |
| `opencv-python (cv2)` | 图像模板匹配 | 支持 |
| `pytesseract` | OCR 文字识别（技能名称） | 支持 |
| `numpy` | 图像数组处理 | 支持 |
| `PIL` | 图像格式转换 | 支持 |
| `json5` | 解析带注释的 JSON 配置 | 支持 |
| `mac_window.py` | 替代 `pygetwindow` 获取窗口信息 | 本次新增 |

### 3.2 核心流程（hq 模式）

```
main()
  └─ load_config() — 加载 config_mac.jsonc
  └─ setup_logging() — 初始化日志
  └─ check_tesseract() — 检查 OCR 可用性
  └─ get_window_info(game_title) — 查找游戏窗口
  └─ check_window_foreground() — 激活窗口到前台
  └─ 【hq 模式主循环】
       ├─ hq_snipe_mode == true
       │   └─ complete_hq_snipe_round()
       │       ├─ detect_hq_screen() — 检测是否在寰球界面
       │       ├─ click_hq_join_button() — 点击"加入"按钮
       │       ├─ detect_team_up_interface() — 检测是否进入房间
       │       ├─ click_hq_ready_button() — 点击"准备"
       │       ├─ execute_hq_game_flow() — 执行游戏内升级流程
       │       │   ├─ wait_for_hq_skill_selection_screen()
       │       │   ├─ select_skill() — 选择技能
       │       │   └─ pause_and_exit_with_retry() — 暂停并退出
       │       └─ click_hq_refresh_button() — 刷新列表（如果没抢到）
       │
       └─ hq_snipe_mode == false
           └─ complete_hq_round() — 原自建房间逻辑
               ├─ detect_hq_screen()
               ├─ click_invite_button() — 点击邀请
               ├─ click_send_invite_button() — 发布招募
               ├─ hq_countdown_timer() — 等待组队
               ├─ click_hq_start_button() — 开始游戏
               └─ execute_hq_game_flow()
```

### 3.3 图像匹配核心函数

```python
def multi_template_match(screenshot, template_filenames, threshold=None, region=None):
    """
    在截图中匹配多个模板图片，返回最佳匹配结果
    - 支持区域匹配（region 参数限定匹配范围）
    - 支持多种匹配算法（TM_CCOEFF_NORMED 等）
    - 对模板和截图都会做预处理（灰度、对比度、二值化）
    """
```

### 3.4 坐标系说明（Mac 关键注意点）

Mac 屏幕坐标系：
- **原点**：屏幕左上角 (0, 0)
- **X 轴**：向右递增
- **Y 轴**：向下递增

`mac_window.py` 获取的窗口坐标直接基于此坐标系，`mss` 截图和 `pyautogui` 点击也使用同一坐标系，**三者一致，无需转换**。

窗口坐标说明：
- `window_info["left"]` — 窗口左边距屏幕左边缘的距离
- `window_info["top"]` — 窗口上边距屏幕顶部的距离
- `window_info["width"]` — 窗口宽度
- `window_info["height"]` — 窗口高度

点击位置计算：
```python
abs_x = window_info["left"] + x  # x 是窗口内相对坐标
abs_y = window_info["top"] + y   # y 是窗口内相对坐标
pyautogui.moveTo(abs_x, abs_y)
pyautogui.click()
```

---

## 四、Mac 改造详情

### 4.1 改造原因
原代码是为 Windows 编写的，使用了以下 Windows 专属 API：
- `ctypes.windll.shell32.IsUserAnAdmin()` — 管理员权限检查
- `ctypes.windll.shell32.ShellExecuteW()` — 提权运行
- `pygetwindow` — 窗口管理（Windows 专用库）

这些在 Mac 上完全不可用。

### 4.2 改造内容

#### 1) start.py 修改
- **移除** `import ctypes` 和 `is_admin()` 函数及提权代码
- **替换** `import pygetwindow as gw` —> 改为 `import mac_window as gw`
- **修改** `get_window_info()`：标题匹配失败时 fallback 到进程名匹配
- **新增** 抢房相关函数（约 200 行）：
  - `click_hq_join_button()` / `click_hq_join_button_default()`
  - `click_hq_refresh_button()`
  - `click_hq_ready_button()`
  - `complete_hq_snipe_round()`
- **修改** `main()`：根据 `hq_snipe_mode` 选择执行抢房或自建房间逻辑

#### 2) mac_window.py（新增）
使用 **Quartz** 框架获取窗口信息，作为 `pygetwindow` 的替代。

关键实现：
```python
# Quartz.CGWindowListCopyWindowInfo 获取所有窗口
# 由于 macOS 隐私限制，OnScreenOnly 经常遗漏实际可见窗口
# 因此使用 OptionAll（获取所有窗口，不限于当前屏幕）

class MacWindow:
    # 模拟 pygetwindow.Window 的接口：
    # title, left, top, width, height
    # isActive, isMinimized, activate(), restore()
```

**注意**：AppleScript 获取窗口标题/激活窗口需要**辅助功能权限**，如果用户没有授予：
- `isActive` 永远返回 False
- `activate()` 无效
- `isMinimized` 无效
- 窗口标题获取为空

**Fallback 机制**：当标题为空时，`find_window()` 和 `get_window_info()` 会通过**进程名**（如 "微信"）匹配窗口。这是 Mac 上工作的关键。

#### 3) config_mac.jsonc（新增）
主要差异：
- `template_root`: `"templates"` — 使用相对路径
- `tesseract_path`: `/opt/homebrew/bin/tesseract` — Mac Homebrew 路径
- `log_file_path`: `logs/auto_%Y-%m-%d.log` — 相对路径
- 新增 `hq_snipe_mode`: `true` — 默认开启抢房模式
- 新增 `hq_snipe_settings` — 抢房专属配置

#### 4) 虚拟环境 venv/
已安装的包：
```
pyautogui, opencv-python, mss, Pillow, pytesseract, json5, numpy
pyobjc-core, pyobjc-framework-Cocoa, pyobjc-framework-quartz
```

---

## 五、已知问题与限制

### 5.1 辅助功能权限（最重要）
**问题**：macOS 的辅助功能权限控制很严格。如果终端/IDE 没有被添加到 **系统设置 → 隐私与安全 → 辅助功能**，则：
- AppleScript 操作其他应用会报错：`osascript 不允许辅助访问 (-1719)`
- `mac_window.py` 的 `isActive`、`activate()`、`isMinimized` 等功能失效
- 窗口标题无法通过 AppleScript 获取（但 Quartz 可以获取进程名）

**当前 workaround**：
- 脚本通过进程名匹配窗口（不依赖标题）
- 激活窗口通过 `pyautogui.click()` 点击窗口中心实现（效果不如真正的 activate）

**理想方案**：引导用户在系统设置中授予辅助功能权限。

### 5.2 微信小程序的模板匹配问题（最大风险）
**问题**：现有的 `templates/*.png` 全部是从 **Windows 版/模拟器版** 游戏截取的。微信小程序的画面可能存在以下差异：
- UI 缩放比例不同
- 按钮样式、颜色、字体不同
- 游戏画面嵌在微信窗口内，位置和原模板对应的绝对位置不同

**影响**：
- `multi_template_match()` 的匹配值可能极低（< 0.3）
- 脚本会 fallback 到"默认位置点击"，但默认位置是基于窗口比例的，可能点不到正确的按钮

**解决方案**：
1. 让用户从微信小程序实际画面中重新截取所有模板图片
2. 或者调整 `config_mac.jsonc` 中的 `default_x_ratio` / `default_y_ratio` 到正确的相对位置

### 5.3 微信窗口多窗口问题
**问题**：微信在 Mac 上可能有多个窗口（如主聊天窗口 741x924、小程序窗口等）。`mac_window.py` 对每个 PID 只保留最大的窗口。

**影响**：如果用户同时打开了微信聊天窗口和小程序，脚本可能匹配到错误的窗口。

**解决方案**：
- 建议用户关闭其他微信窗口，只保留游戏小程序窗口
- 或者改进 `mac_window.py`，通过窗口尺寸过滤（小程序窗口通常比聊天窗口大或小，需观察）

### 5.4 截图可能被遮挡
**问题**：`mss` 截图截取的是屏幕上的实际像素。如果游戏窗口被其他窗口遮挡，截图会包含遮挡物，导致图像匹配失败。

**解决方案**：
- `check_window_foreground()` 尝试激活窗口，但 Mac 上激活不一定能把窗口置顶到最前
- 建议用户关闭其他可能遮挡微信的窗口

### 5.5 窗口尺寸变化
**问题**：微信小程序内的游戏画面尺寸可能随微信窗口大小变化。

**影响**：模板匹配对尺寸变化敏感，如果窗口缩放导致按钮变大/变小，匹配值会下降。

**解决方案**：
- 建议用户固定微信窗口大小（不要手动缩放）
- 或者使用 `cv2.resize()` 对模板进行多尺度匹配（当前未实现）

---

## 六、后续待办事项（供其他模型参考）

### 高优先级

1. **测试现有模板是否匹配微信小程序**
   - 让用户运行 `python3 start.py --play hq --config config_mac.jsonc --debug`
   - 查看日志中的匹配值，判断现有模板是否需要重截
   - 如果匹配值 < 0.5，需要全部重截

2. **获取微信小程序内的精确按钮坐标**
   - 使用 `pyautogui.displayMousePosition()`（需要在代码中临时调用）
   - 或让用户手动把鼠标放到按钮上，记录坐标
   - 更新 `config_mac.jsonc` 中的默认位置比例

3. **解决微信多窗口匹配问题**
   - 观察微信各个窗口的尺寸特征
   - 在 `mac_window.py` 或 `get_window_info()` 中增加更精确的过滤逻辑

### 中优先级

4. **改进抢房逻辑的健壮性**
   - 当前 `complete_hq_snipe_round()` 依赖模板匹配 `hq_join.png`
   - 如果用户没有截图，需要更好的 fallback（如 OCR 识别"加入"文字，或基于颜色/位置的启发式检测）

5. **增加 OCR 识别房间状态**
   - 用 `pytesseract` 识别寰球界面上的文字（如房间人数、倒计时）
   - 帮助判断哪些房间可以加入

6. **处理游戏结束后的奖励/结算界面**
   - 当前 `execute_hq_game_flow()` 只处理到退出游戏
   - 如果打完后有额外的奖励领取界面、评分界面，需要新增处理逻辑

### 低优先级

7. **多尺度模板匹配**
   - 当前 `multi_template_match()` 只匹配原始尺寸
   - 可以增加金字塔匹配，应对不同分辨率的缩放

8. **优化 mac_window.py 的 AppleScript fallback**
   - 当 Quartz 获取不到标题时，尝试使用 `ApplicationServices` 框架的 AX API
   - 比 AppleScript 更快，但也需要辅助功能权限

9. **打包为 Mac App**
   - 使用 `py2app` 或 `PyInstaller` 打包为 `.app`
   - 用户双击即可运行，不需要命令行

---

## 七、快速调试指南

### 查看当前所有窗口
```bash
cd /Users/geng/project/github/game/xjskp-auto
source venv/bin/activate
python3 list_windows.py
```

### 带调试运行
```bash
python3 start.py --play hq --config config_mac.jsonc --debug
```

### 查看日志
```bash
tail -f logs/auto_$(date +%Y-%m-%d).log
```

### 测试单个模板匹配
可以临时写一个小脚本测试某个模板在微信窗口中能否匹配：
```python
import sys
sys.path.insert(0, '/Users/geng/project/github/game/xjskp-auto')
from start import *

load_config('config_mac.jsonc')
wi = get_window_info(config['game_title'])
img = capture_screenshot(wi)
result, pos, val, size = multi_template_match(img, ['invite.png'], threshold=0.3)
print(f"匹配结果: {result}, 位置: {pos}, 匹配值: {val:.4f}")
```

---

## 八、关键配置项速查

| 配置项 | 位置 | 说明 |
|--------|------|------|
| `game_title` | `config_mac.jsonc` | 匹配窗口的进程名，微信小程序填 "微信" |
| `hq_snipe_mode` | `config_mac.jsonc` | true=抢房模式，false=自建房间 |
| `template_root` | `config_mac.jsonc` | 模板目录，相对路径 "templates" |
| `tesseract_path` | `config_mac.jsonc` | Mac 上通常是 /opt/homebrew/bin/tesseract |
| `match_threshold` | `config_mac.jsonc` | 图像匹配阈值，默认 0.6，可尝试降低 |
| `hq_snipe_settings.join_default_x_ratio` | `config_mac.jsonc` | 加入按钮默认 X 位置比例 |
| `hq_snipe_settings.join_default_y_ratio` | `config_mac.jsonc` | 加入按钮默认 Y 位置比例 |
| `calibration.*` | `config_mac.jsonc` | 各类按钮的点击偏移校准 |

---

## 九、最后更新时间

2026-05-20

**修改人**：Kimi Code CLI
**主要内容**：Mac 兼容性改造 + 寰球抢房模式
