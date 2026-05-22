<div align="center">

<h1>🎬 DySub</h1>

<p><strong>本地优先的字幕提取工具</strong> — 音视频 → 字幕，全程本地处理</p>

<p>
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg" alt="Platform">
</p>

<p>
  <a href="#快速开始">快速开始</a> •
  <a href="#配置-api-key">配置 API Key</a> •
  <a href="#使用示例">使用示例</a> •
  <a href="#常见问题">常见问题</a>
</p>

</div>

---

## 📖 简介

DySub 是一款**完全运行在用户本地**的开源字幕提取工具。支持本地音视频文件和抖音分享链接作为输入，在本地完成音频提取、标准化与转写，最终调用**用户自备的** ASR API，生成 **SRT / VTT / TXT** 字幕文件。

> 🔒 **核心原则**：所有数据处理均在用户本地完成。开发者不托管任何在线服务，不接触用户的音视频内容，也不经手用户的 API Key。

---

## ✨ 功能特性

| 特性 | 说明 |
|------|------|
| 🏠 **本地优先** | 音频提取、转写全流程本地执行，隐私零泄露 |
| 🔌 **插件化输入源** | 本地文件为核心，抖音等网络链接作为可选扩展 |
| ⚡ **异步流水线** | 基于 `asyncio` 的高性能音频提取与转写 |
| ✂️ **智能分片** | 音频超过 25MB 自动按 10 分钟切片，合并时自动修正时间戳 |
| 📝 **多种输出格式** | SRT、WebVTT、纯文本 TXT |
| 🖥️ **轻量 WebUI** | 基于 Gradio 的本地交互界面，支持批量任务 |

---

## 🚀 快速开始

### 前置依赖

- **Python** 3.10+
- **FFmpeg**（系统自带或自行安装）

```bash
# 验证 FFmpeg
ffmpeg -version
```

### 安装

```bash
# 基础功能（本地文件 + CLI）
pip install dysub-core

# 完整功能（含抖音解析 + WebUI）
pip install dysub-core dysub-webui dysub-input-douyin
```

### 一分钟上手

```bash
# 1. 检查环境
dysub doctor

# 2. 本地视频转字幕
dysub process ./video.mp4 --lang zh

# 3. 抖音链接转字幕
dysub process "https://v.douyin.com/xxxxx" --lang zh

# 4. 启动本地 WebUI
dysub webui
# 浏览器访问 http://127.0.0.1:7860
```

字幕默认输出到当前目录的 `outputs/` 文件夹。

---

## 🔑 配置 API Key

DySub 需要您自备 ASR API Key。目前最推荐的国内方案是**阿里百炼（DashScope）**，它提供免费的 `qwen3-asr-flash` 模型额度，且对中文支持极好。

### 获取阿里百炼 API Key

<div align="center">

| 步骤 | 操作 |
|------|------|
| 1 | 打开 [阿里百炼控制台](https://bailian.console.aliyun.com/) |
| 2 | 登录阿里云账号（没有就注册一个） |
| 3 | 点击左上角 **「API Key 管理」** |
| 4 | 点击 **「创建新的 API Key」** |
| 5 | 复制生成的 Key（格式类似 `sk-xxxxxxxxxxxxxxxx`） |

</div>

> 💡 新用户通常有免费额度，足够个人使用。具体额度以百炼官网为准。

### 填入 DySub（三种方式）

**方式一：命令行参数**（临时，适合一次性使用）

```bash
dysub process ./video.mp4 --api-key sk-xxxxxxxx
```

**方式二：环境变量**（适合脚本或服务器）

```bash
export DYSUB_ASR_API_KEY="sk-xxxxxxxx"
export DYSUB_ASR_BASE_URL="https://dashscope.aliyuncs.com/api/v1"
```

**方式三：`.env` 配置文件** ⭐ 推荐，最方便

```bash
mkdir -p ~/.config/dysub

cat > ~/.config/dysub/.env << 'EOF'
DYSUB_ASR_API_KEY=sk-xxxxxxxx
DYSUB_ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DYSUB_DEFAULT_LANGUAGE=zh
DYSUB_DEFAULT_FORMAT=srt
EOF
```

> 📌 如果同时存在项目根目录的 `.env` 和 `~/.config/dysub/.env`，**优先读取后者**（用户级配置优先）。

---

## 📚 使用示例

### CLI 参数

```bash
dysub process <source> [OPTIONS]
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `source` | 输入源：本地文件路径或抖音链接 | **必填** |
| `--output, -o` | 输出目录 | `outputs` |
| `--lang, -l` | 语言代码 | `zh` |
| `--format, -f` | 输出格式：`srt` / `vtt` / `txt` | `srt` |
| `--api-key` | ASR API Key | 从 `.env` 读取 |
| `--base-url` | ASR 接口地址 | 从 `.env` 读取 |
| `--temp-dir` | 临时文件目录 | `/tmp/dysub` |
| `--keep-temp` | 保留临时文件 | `False` |

### 本地视频

```bash
dysub process ./video.mp4 --lang zh --format srt
# 输出：outputs/video.srt
```

### 抖音链接

```bash
dysub process "https://v.douyin.com/LtQTEmgLs58/" \
  --lang zh \
  --format srt \
  --base-url https://dashscope.aliyuncs.com/api/v1
```

### WebUI

```bash
dysub webui
```

浏览器访问 `http://127.0.0.1:7860`：

1. 上传音视频文件或粘贴抖音链接
2. 选择语言和输出格式
3. 点击「提取字幕」
4. 预览结果并下载文件

---

## 🏗️ 项目结构

```text
dysub/
├── 📁 packages/
│   ├── 📦 dysub-core/              # 核心库：音频处理、ASR、字幕合并、CLI
│   ├── 📦 dysub-input-local/       # 本地文件输入插件
│   ├── 📦 dysub-input-douyin/      # 抖音链接解析插件
│   └── 📦 dysub-webui/             # Gradio 本地 Web 界面
├── 📁 tests/                       # 测试与示例资源
├── 📁 outputs/                     # 默认字幕输出目录
├── 🐳 Dockerfile
└── 📄 README.md
```

---

## ❓ 常见问题

<details>
<summary><b>字幕没有时间戳，只有一个大块？</b></summary>

这是因为当前使用的 <code>qwen3-asr-flash</code> 模型只返回纯文本，不返回句子级时间戳。DySub 会将其包装成一个覆盖全片长的伪时间块。

如需真正的时间戳，需要使用支持时间戳输出的 ASR 模型（如 OpenAI Whisper API 的 <code>response_format=srt</code>）。

</details>

<details>
<summary><b>抖音链接解析失败？</b></summary>

抖音分享页偶尔改版会导致 <code>_ROUTER_DATA</code> 结构变化。若遇到解析失败，请提 Issue 并附上链接。

</details>

<details>
<summary><b>音频很大，会切片吗？</b></summary>

会。如果提取出的 WAV 超过 25MB，Pipeline 会自动按 10 分钟切片，逐片转写后合并，并修正时间戳偏移。

</details>

<details>
<summary><b>可以处理 Bilibili / YouTube 链接吗？</b></summary>

目前内置了本地文件和抖音插件。其他平台可以通过插件机制扩展，欢迎提交 PR。

</details>

---

## 🛠️ 开发

```bash
git clone https://github.com/yourname/dysub.git
cd dysub
python -m venv .venv
source .venv/bin/activate
pip install -e packages/dysub-core \
            -e packages/dysub-input-local \
            -e packages/dysub-input-douyin \
            -e packages/dysub-webui
pytest
```

---

## ⚠️ 免责声明

DySub 是一个本地运行的开源字幕提取工具，开发者不运营任何在线服务，也不对用户使用本工具的行为负责。

1. 用户须自行获取并遵守第三方 ASR 服务商的使用条款，自行承担 API 调用费用。
2. 用户须确保对处理的音视频内容拥有合法权利。使用网络链接解析功能时，须遵守相应平台的服务条款（ToS）。
3. 本项目提供的代码仅供个人学习、研究与合法的内容无障碍处理使用。
4. 任何因违反法律法规或平台规则而产生的后果，由使用者自行承担。

---

<div align="center">

**[⬆ 回到顶部](#-dysub)**

Made with ❤️ by DySub Contributors

</div>
