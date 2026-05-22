# dysub

本地优先的字幕提取工具 — 音视频 → 字幕，全程本地处理。

## 简介

DySub 是一款**完全运行在用户本地**的开源字幕提取工具。支持本地音视频文件和抖音分享链接作为输入，在本地完成音频提取、标准化与转写，最终调用**用户自备的** ASR API，生成 SRT / VTT / TXT 字幕文件。

> 🔒 **核心原则**：所有数据处理均在用户本地完成。开发者不托管任何在线服务，不接触用户的音视频内容，也不经手用户的 API Key。

## 安装

```bash
pip install dysub
```

前置依赖：
- Python 3.10+
- FFmpeg

## 快速开始

### 1. 配置 API Key

推荐阿里百炼（DashScope）：

1. 打开 [阿里百炼控制台](https://bailian.console.aliyun.com/)
2. 进入「API Key 管理」→ 创建新的 API Key
3. 写入配置：

```bash
mkdir -p ~/.config/dysub
cat > ~/.config/dysub/.env << 'EOF'
DYSUB_ASR_API_KEY=sk-xxxxxxxx
DYSUB_ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DYSUB_DEFAULT_LANGUAGE=zh
DYSUB_DEFAULT_FORMAT=srt
EOF
```

### 2. 提取字幕

```bash
# 本地视频
dysub process ./video.mp4 --lang zh

# 抖音链接
dysub process "https://v.douyin.com/xxxxx" --lang zh

# 启动 WebUI
dysub webui
# 浏览器访问 http://127.0.0.1:7860
```

字幕默认输出到 `outputs/` 目录。

## 包含的组件

安装 `dysub` 会自动安装以下包：

| 包名 | 说明 |
|------|------|
| `dysub-core` | 核心引擎：音频处理、ASR 客户端、字幕合并、CLI |
| `dysub-input-local` | 本地文件输入插件（MP4/MP3/MKV 等） |
| `dysub-input-douyin` | 抖音链接解析插件 |

## 更多文档

- 完整 README：https://github.com/HYPERVAPOR/dysub/blob/main/README.md
- 问题反馈：https://github.com/HYPERVAPOR/dysub/issues
