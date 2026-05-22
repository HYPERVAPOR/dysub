# dysub-input-local

DySub 本地文件输入插件 — 支持常见音视频格式直接作为字幕提取的输入源。

## 支持的格式

- 视频：MP4, MKV, MOV, AVI, WEBM
- 音频：MP3, WAV, M4A, AAC, FLAC, OGG

## 安装

```bash
pip install dysub-input-local
```

作为 `dysub` 统一包的一部分安装：

```bash
pip install dysub
```

## 使用

安装后自动注册，无需额外配置：

```bash
dysub process ./video.mp4 --lang zh
dysub process ./podcast.mp3 --lang zh --format txt
```

## 工作原理

通过文件扩展名和路径存在性检测，直接透传绝对路径给下游 FFmpeg 音频提取模块。不修改、不复制原文件。

## 更多文档

- 主仓库：https://github.com/HYPERVAPOR/dysub
