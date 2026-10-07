[README.md](https://github.com/user-attachments/files/33138293/README.md)
# AI Rock Paper Scissors · AI 猜拳擂台

面向学校社团招新摊位的摄像头石头剪刀布小游戏。站在镜头前做出 ✊ / ✋ / ✌️，与会学习出拳习惯的 AI 对战。

**源码仓库：** https://github.com/davywavey/ai-rock-paper-scissors

**在线策略 Demo：** https://davywavey-ai-rps.zhwdavid1.chatgpt.site （当前按 Sites 默认访问范围发布，仅所有者可访问。）

## 游戏玩法

- 先得 2 分赢下一场比赛；平局不计分。
- 每轮 3 秒倒计时，倒计时结束后读取手势。
- 每轮只锁定一次有效手势，连续两帧一致后判定。
- AI 根据最近 8 次出拳预测最常用手势，65% 概率进行针对性出拳，35% 概率随机；前两轮随机。
- 比赛连胜、最高连胜、结果闪屏、粒子效果；Windows 支持系统提示音。
- 所有计分和历史仅保留在当前运行中，退出后不保存。

## 桌面版运行

需要 **Python 3.11** 和可用摄像头。

```bash
git clone https://github.com/davywavey/ai-rock-paper-scissors.git
cd ai-rock-paper-scissors
python -m venv .venv
```

激活环境：

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

安装依赖并启动：

```bash
python -m pip install -r requirements.txt
python main.py
```

Windows 也可以双击 `setup-windows.bat` 完成首次安装，再双击 `start-game.bat` 启动。系统的 `python` 命令应指向 Python 3.11。已安装依赖的 Conda 环境可直接 `python main.py`。

`gesture_recognizer.task` 必须与 `main.py` 放在同一目录。程序通过 Python 读取模型字节，兼容 Windows 中文项目路径。

| 按键 | 功能 |
| --- | --- |
| SPACE | 下一轮；比赛结束后开启新比赛，保留连胜和 AI 历史 |
| R | 清空比分、连胜纪录和 AI 历史，重新开始 |
| ESC | 退出全屏游戏并释放摄像头和识别器 |

## 识别方式与限制

使用本地 MediaPipe GestureRecognizer，将 Closed_Fist / Open_Palm / Victory 映射为 ROCK / PAPER / SCISSORS。原模型不确定时，使用 21 个手部关键点的关节夹角作为兜底。优先使用世界坐标，改善旋转或倾斜姿势的适应性。

识别输入请求为 640×480、30 FPS；显示画布为 1280×720。启动时预热模型，稳定判定只需要连续两帧。实际延迟与电脑、摄像头、光线及遮挡相关，无法保证所有设备和姿势都在 1 秒内识别。完整侧面或严重遮挡仍可能无法识别。

手势推理在本机完成，不上传摄像头画面；不调用 ChatGPT、DeepSeek 或其他在线大模型，无需 API 密钥。AI 对手是本地自适应统计策略。

## 在线 Demo

`demo-site/dist/` 是无需构建的浏览器策略试玩：点击手势或按 1 / 2 / 3 出拳，SPACE 下一轮，R 重置；提供三局两胜、AI 预测、连胜与可选音效。

在线版展示游戏规则和 AI 策略，摄像头手势识别在桌面 Python 版中使用。两个版本的比分分别计算，在线版刷新即重置。

本地预览：

```bash
python -m http.server 8080 --directory demo-site/dist
```

访问 `http://localhost:8080`。

## 文件结构

```text
main.py                    # OpenCV + MediaPipe 桌面完整版
gesture_recognizer.task    # MediaPipe 预训练识别模型
main.ipynb                 # 早期探索 notebook；使用 main.py 运行完整版
requirements.txt           # Python 依赖
setup-windows.bat          # Windows 首次安装
start-game.bat             # Windows 启动
demo-site/dist/             # 在线策略试玩源码
```

## 第三方组件

MediaPipe、OpenCV 及预训练模型属于其各自提供方。模型来自 Google MediaPipe GestureRecognizer；相关介绍与来源见 [官方模型文档](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer) 与 [模型下载地址](https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task)。

首次运行遇到摄像头错误时，请关闭占用摄像头的软件，确认系统允许 Python 使用摄像头，再重新启动。画面中尽量只保留一只手，保证光线充足。
