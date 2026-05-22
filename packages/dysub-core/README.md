# dysub-core

DySub 核心库 — 本地音频提取、ASR 转写与字幕合并的一站式解决方案。

## 简介

`dysub-core` 是 [DySub](https://github.com/HYPERVAPOR/dysub) 字幕提取工具的核心引擎，负责：

- **音频处理**：基于 FFmpeg 流式提取、重采样、智能分片
- **ASR 客户端**：兼容 OpenAI 规范，支持 Whisper / DashScope 等服务商
- **字幕合并**：SRT/VTT 时间戳修正与格式导出
- **流水线编排**：纯 asyncio 异步驱动，带进度回调
- **CLI 入口**：`dysub` 命令行工具

## 安装

```bash
pip install dysub-core
```

前置依赖：
- Python 3.10+
- FFmpeg（`ffmpeg -version` 验证）

## 快速开始

### CLI

```bash
# 检查环境
dysub doctor

# 本地视频转字幕
dysub process ./video.mp4 --lang zh --format srt

# 启动本地 WebUI
dysub webui
```

### Python API

```python
import asyncio
from pathlib import Path
from dysub_core.models import MediaSource, TaskConfig
from dysub_core.pipeline import Pipeline

async def main():
    config = TaskConfig(
        api_key="sk-xxxxxxxx",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        language="zh",
        output_format="srt",
        output_dir=Path("outputs"),
    )
    pipeline = Pipeline(config)
    source = MediaSource(
        stream_url="./video.mp4",
        source_type="local",
    )
    result = await pipeline.run(source)
    print(f"Subtitle saved to: {result}")

asyncio.run(main())
```

## 配置 API Key

DySub 需要自备 ASR API Key。推荐阿里百炼（DashScope）：

1. 打开 [阿里百炼控制台](https://bailian.console.aliyun.com/)
2. 进入「API Key 管理」→ 创建新的 API Key
3. 配置到 DySub：

```bash
# 环境变量
export DYSUB_ASR_API_KEY="sk-xxxxxxxx"
export DYSUB_ASR_BASE_URL="https://dashscope.aliyuncs.com/api/v1"

# 或写入 ~/.config/dysub/.env
cat > ~/.config/dysub/.env << 'EOF'
DYSUB_ASR_API_KEY=sk-xxxxxxxx
DYSUB_ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DYSUB_DEFAULT_LANGUAGE=zh
DYSUB_DEFAULT_FORMAT=srt
EOF
```

## 功能特性

| 模块 | 能力 |
|------|------|
| `audio.processor` | FFmpeg 流式提取 → WAV (16kHz, mono)，自动分片 (>25MB 按 10min 切) |
| `asr.client` | OpenAI 兼容客户端，支持 `response_format=srt/vtt` |
| `asr.dashscope_client` | 阿里百岭 DashScope 原生客户端，支持 base64 音频上传 |
| `subtitle.merger` | SRT 分片合并，自动修正时间戳偏移 |
| `pipeline` | asyncio 异步流水线，并发控制，进度回调 |
| `cli` | Typer + Rich 终端界面，支持 `doctor`/`process`/`webui` |

## 插件机制

通过 `entry_points(group="dysub.inputs")` 自动发现输入源插件：

```python
from dysub_core.inputs.registry import discover_inputs

adapters = discover_inputs()
# {'local': LocalFileAdapter(), 'douyin': DouyinAdapter()}
```

安装额外插件：

```bash
pip install dysub-input-douyin   # 抖音链接解析
```

## 更多文档

- 主仓库：https://github.com/HYPERVAPOR/dysub
- 完整 README：https://github.com/HYPERVAPOR/dysub/blob/main/README.md
