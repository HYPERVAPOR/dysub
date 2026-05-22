# dysub-input-douyin

DySub 抖音链接输入插件 — 解析抖音分享链接，提取视频直链用于字幕生成。

## 工作原理

不同于 yt-dlp 等重型工具，`dysub-input-douyin` 采用轻量级解析策略：

1. 用手机 UA 访问 `iesdouyin.com` 分享页面
2. 从 HTML 中提取嵌入的 `window._ROUTER_DATA` JSON
3. 解析出 `video.play_addr.url_list` 作为视频直链
4. 附带必要的 HTTP headers 传给 FFmpeg 提取音频

无需浏览器自动化、无需 cookies、无外部二进制依赖。

## 安装

```bash
pip install dysub-input-douyin
```

作为 `dysub` 统一包的一部分安装：

```bash
pip install dysub
```

## 使用

安装后自动注册，无需额外配置：

```bash
dysub process "https://v.douyin.com/xxxxx" --lang zh --format srt
```

## 技术细节

| 项目 | 说明 |
|------|------|
| 依赖 | 仅 `httpx`（由 `dysub-core` 提供） |
| 请求方式 | 单次 HTTP GET，纯 Python |
| 视频质量 | 带水印版本（不影响音频提取） |
| 失败原因 | 分享页改版、视频已删除/私密、网络超时 |

## 更多文档

- 主仓库：https://github.com/HYPERVAPOR/dysub
