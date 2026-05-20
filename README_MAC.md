# 向僵尸开炮 - Mac 自动化脚本使用说明

## 一、安全评估

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 网络通信 | ✅ 无 | 脚本不联网，不传输任何数据 |
| 敏感信息收集 | ✅ 无 | 不读取文件、密码、聊天记录等 |
| 恶意操作 | ✅ 无 | 仅对指定游戏窗口进行图像识别和点击 |
| 权限需求 | ⚠️ 需要辅助功能 | Mac 控制鼠标/窗口需要系统授权 |
| 风险提示 | ⚠️ 运行时不可操作鼠标 | pyautogui 会接管鼠标，运行中请勿手动操作 |

**总体结论：脚本本身安全风险很低**，属于正常的自动化辅助工具。但请注意：
- 游戏官方可能禁止使用自动化脚本，存在被封号风险
- 运行期间鼠标会被脚本控制，不要在运行时操作电脑

---

## 二、环境准备

### 1. 安装依赖

项目已自带虚拟环境 `venv`，执行以下命令安装：

```bash
cd /Users/geng/project/github/game/xjskp-auto
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 安装 Tesseract OCR（已预装）

本项目已检测到系统安装了 Tesseract（路径：`/opt/homebrew/bin/tesseract`），无需额外操作。

### 3. 授予辅助功能权限（关键步骤）

Mac 控制其他应用窗口和鼠标需要【辅助功能】权限：

1. 打开 **系统设置 → 隐私与安全 → 辅助功能**
2. 点击左下角 🔒 解锁
3. 添加并勾选你运行脚本的程序（如 **终端/iTerm2/VS Code**）
4. 如果权限已添加但仍然报错，尝试**删除后重新添加**

> 💡 如果没有授予权限，脚本无法获取窗口标题，只能看到进程名。

---

## 三、查找游戏窗口

在 Mac 上，由于系统隐私保护，很多应用的窗口标题无法直接获取。脚本支持通过**进程名**匹配窗口。

运行以下命令查看当前所有可见窗口：

```bash
source venv/bin/activate
python3 list_windows.py
```

输出示例：
```
【应用】VMware Fusion
  - 标题: '(无标题)'
    进程: 'VMware Fusion'
    位置: (12, 46) 尺寸: 741x459
```

请确认你的游戏窗口对应的**进程名**，然后修改 `config_mac.jsonc` 中的 `game_title`：

```jsonc
"game_title": "VMware Fusion"
```

常见进程名对照：
- VMware 虚拟机 → `VMware Fusion`
- Parallels 虚拟机 → `Parallels Desktop`
- MuMu 模拟器 → `MuMuPlayer` 或 `NemuPlayer`
- 雷电模拟器 → `ldplayer` 或 `雷电模拟器`
- PlayCover → 游戏本身的名字（可能无法获取标题）

---

## 四、运行脚本

### 模式一：抢房模式（加入别人的寰球救援房间）

```bash
source venv/bin/activate
python3 start.py --play hq --config config_mac.jsonc
```

抢房模式说明：
- 自动刷新寰球救援房间列表
- 检测并点击【加入】按钮
- 进入房间后自动点击【准备/开始】
- 打完后自动退出，继续下一轮抢房

**注意**：抢房模式依赖新的模板图片（加入按钮、刷新按钮等）。目前代码已提供基于**默认坐标**的点击能力，建议你在游戏中截图这些按钮并放入 `templates/` 文件夹：
- `hq_join.png` / `hq_join2.png` — 房间列表中的"加入"按钮
- `hq_refresh.png` — 刷新列表按钮
- `hq_ready.png` — 进入房间后的"准备"按钮

如果不放这些图片，脚本会尝试用默认位置点击（可能不准，需要你在 `config_mac.jsonc` 中调整坐标比例）。

### 模式二：自建房间模式（自己发布招募）

修改 `config_mac.jsonc`：

```jsonc
"hq_snipe_mode": false
```

然后运行同样的命令。这是原脚本自带的逻辑：自己创建房间 → 发布招募 → 等待队友 → 开始游戏。

### 模式三：普通闯关模式

```bash
python3 start.py --play master --config config_mac.jsonc
```

---

## 五、调试与日志

### 开启调试模式

```bash
python3 start.py --play hq --config config_mac.jsonc --debug
```

调试模式会输出更多匹配信息，方便排查问题。

### 查看日志

日志保存在 `logs/` 目录下，文件名格式为 `auto_YYYY-MM-DD.log`。

---

## 六、常见问题

### Q1: 提示"未找到标题或进程名包含 xxx 的窗口"

1. 先运行 `python3 list_windows.py` 查看所有窗口
2. 确认 `config_mac.jsonc` 中的 `game_title` 与进程名一致
3. 确认游戏窗口没有被最小化
4. 如果游戏在虚拟机内，填写虚拟机的进程名（如 `VMware Fusion`）

### Q2: 提示"osascript 不允许辅助访问"

前往 **系统设置 → 隐私与安全 → 辅助功能**，添加并勾选终端程序。

### Q3: 脚本找到了窗口但截图是全黑的/不对

这通常是因为窗口被其他窗口遮挡。脚本会在点击前尝试激活窗口，但如果其他窗口（如权限弹窗）挡住了游戏，截图仍然会有问题。请确保游戏窗口可见。

### Q4: 点击位置不准确

修改 `config_mac.jsonc` 中的 `calibration` 部分，调整偏移量：

```jsonc
"calibration": {
    "start_x": 0,
    "start_y": 0,
    ...
}
```

或者在 `hq_snipe_settings` 中调整默认点击位置的比例。

---

## 七、改造内容总结

本次改造主要做了以下工作：

1. **移除 Windows 依赖**：删除了 `ctypes` 管理员权限检查和 `pygetwindow` 导入
2. **新增 Mac 窗口管理模块** (`mac_window.py`)：使用 Quartz + AppleScript 获取窗口信息
3. **Mac 版配置文件** (`config_mac.jsonc`)：使用相对路径和 Mac 版 Tesseract 路径
4. **新增抢房逻辑**：`complete_hq_snipe_round` 函数实现自动加入别人房间
5. **新增窗口列表工具** (`list_windows.py`)：帮助用户查找正确的窗口进程名
6. **依赖管理** (`requirements.txt`)：方便一键安装
