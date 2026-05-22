# DySub - 开源本地字幕提取工具产品需求文档 (PRD)

DySub 是一款**完全运行在用户本地**的开源字幕提取工具。它通过插件化的输入源架构，支持用户将本地音视频文件或网络链接（如抖音、Bilibili 等）作为输入，在本地完成音频流式提取、分片与标准化，最终调用**用户自备的**兼容 OpenAI 规范的 ASR API，生成带有精准时间戳的 SRT/VTT 字幕文件。

**核心原则**：所有数据处理均在用户本地完成。开发者不托管任何在线服务，不接触用户的音视频内容，也不经手用户的 API Key。

---

## 1. 产品定位与合规声明

### 1.1 产品定位
DySub 的定位是**"通用本地字幕工作流"**，而非针对任何单一平台的破解工具。
- 首要输入源为**用户本地音视频文件**。
- 网络链接解析（如抖音）作为**可选扩展插件**提供，需用户手动安装。
- 项目以 Python 库 + CLI 为核心，Web UI 仅为可选的本地交互界面。

### 1.2 合规与免责声明
本项目以开源代码形式发布，开发者不运营任何中心化服务。
- 用户须自行获取并配置第三方 ASR 服务的 API Key（如 OpenAI、阿里云、讯飞等）。
- 用户须确保其对输入的音视频内容拥有合法权利，或已获得相应授权。
- 使用网络链接解析功能时，用户须自行遵守相应平台的服务条款（ToS）。
- 因用户使用本工具产生的任何法律纠纷或平台处罚，均由用户自行承担。

---

## 2. 系统架构与技术栈选型

项目采用**本地优先、插件化、轻量级**设计。彻底摒弃需要中心化运维的分布式组件。

### 2.1 技术栈选型

| 层级 | 选型 | 说明 |
|------|------|------|
| **核心运行时** | Python 3.10+ | 全异步基于 `asyncio`，足以支撑本地并发 |
| **输入源插件** | Python Adapter 模式 | 统一接口，按需安装特定平台解析插件 |
| **音频处理** | FFmpeg + `ffmpeg-python` | 流式读取，不落地完整视频 |
| **Web UI (可选)** | Gradio / Streamlit / FastAPI 轻量 SPA | 本地浏览器访问，无需 Next.js 过重架构 |
| **打包与分发** | `pyproject.toml` + PyPI | `pip install dysub[webui,douyin]` |

### 2.2 去除的原始架构
以下在原始设计中存在、但在本地优先模式下**不再必要**的组件已被移除：
- ~~Celery + Redis~~：本地 asyncio 即可满足任务调度，无需分布式队列。
- ~~API Gateway / 限流~~：无公网服务，不存在多用户并发与恶意刷量。
- ~~基于 Redis 的分布式状态机~~：本地任务状态通过内存 + 日志实时反馈。

### 2.3 目录结构规范

```text
dysub/
├── packages/
│   ├── dysub-core/                 # 核心库（音频处理、ASR 客户端、字幕合并）
│   │   ├── dysub_core/
│   │   │   ├── audio/
│   │   │   │   └── processor.py    # FFmpeg 流式提取、重采样、分片
│   │   │   ├── asr/
│   │   │   │   └── client.py       # OpenAI 兼容 ASR 客户端
│   │   │   ├── subtitle/
│   │   │   │   └── merger.py       # SRT 分片合并与时间戳修正
│   │   │   └── pipeline.py         # 本地异步流水线编排
│   │   └── pyproject.toml
│   ├── dysub-input-local/          # 内置插件：本地文件输入
│   │   └── dysub_input_local/
│   │       └── adapter.py
│   └── dysub-input-douyin/         # 可选插件：抖音链接解析
│       └── dysub_input_douyin/
│           └── adapter.py          # X-Bogus 签名与无水印直链提取（可选安装）
├── apps/
│   └── webui/                      # 本地 Web UI（可选安装）
│       ├── app.py                  # Gradio/Streamlit/FastAPI 入口
│       └── pyproject.toml
├── tests/                          # 各模块测试
├── Dockerfile                      # 可选：本地容器化运行
├── pyproject.toml                  # 仓库级配置（可选 monorepo 工具如 PDM）
└── README.md
```

---

## 3. 核心业务流程与数据流

本地流水线采用纯 `asyncio` 异步驱动，终端或 WebUI 通过回调/轮询本地进程获取实时进度。

```
[用户输入: 本地文件 / 抖音链接 / 其他]
       │
       ▼
 1. [Input Adapter] 路由至对应插件
       │
       ├── 本地文件 → 直接返回文件路径
       └── 抖音链接 → [douyin adapter] 追踪重定向/解析 → 返回 MP4 直链
       │
       ▼
 2. [audio.processor] FFmpeg 流式抽音频 → WAV (16kHz, mono)
       │
       ▼
 3. [audio.chunker] 检查体积
       │
       ├── ≤ 25MB → 单文件直传
       └── > 25MB → 按 10min 切片，记录各段偏移量
       │
       ▼
 4. [asr.client] 读取用户本地 .env 中的 API_KEY，逐片请求 ASR
       │                       （response_format="srt"）
       ▼
 5. [subtitle.merger] 解析 SRT → 按偏移量顺延时间戳 → 合并为完整字幕
       │
       ▼
 6. [输出] 写入用户本地目录 /tmp/dysub/output/
       │
       ▼
 7. [清理] 删除临时音频文件（保留原始视频/字幕输出）
```

---

## 4. 模块化功能需求详情 (Functional Requirements)

### 4.1 packages/dysub-input-* (输入源插件体系)

*   **FR-1.1 统一接口：** 所有输入源必须实现 `BaseInputAdapter.resolve(source: str) -> MediaSource`，返回包含 `stream_url`（可直接被 FFmpeg 读取的 URL 或本地路径）和 `metadata` 的标准对象。
*   **FR-1.2 本地文件（内置）：** 支持常见音视频格式（MP4, MKV, MP3, WAV, M4A, MOV）。直接透传绝对路径给下游。
*   **FR-1.3 抖音插件（可选）：** 接收 `v.douyin.com` 短链，追踪 302 重定向，处理防爬签名（X-Bogus），提取无水印 MP4 直链。若视频已删除/私密，抛出 `VideoNotFoundError`。
*   **FR-1.4 插件发现机制：** 核心库通过 `entry_points`（`dysub.inputs`）自动发现已安装的输入源插件。若用户未安装 `dysub-input-douyin`，CLI/WebUI 应友好提示：`"抖音解析功能需安装 pip install dysub-input-douyin"`。

### 4.2 packages/dysub-core/audio (音频处理模块)

*   **FR-2.1 流式处理：** 禁止将网络视频完整下载到本地持久化。`ffmpeg-python` 必须以流式输入处理 MP4 直链，仅输出临时音频文件。
*   **FR-2.2 标准化重采样：** 强制输出为 WAV 格式、16000Hz 采样率、单声道 (mono)。
*   **FR-2.3 25MB 智能分片：**
    *   若临时 WAV 体积 `≤ 25MB`，透传单文件路径。
    *   若 `> 25MB`，按每 10 分钟切片，输出有序文件列表（如 `[chunk_0.wav, chunk_1.wav]`），并记录各段相对于原视频的时间偏移量。
*   **FR-2.4 临时文件管理：** 所有临时音频文件写入用户可配置的 `DYSUB_TEMP_DIR`（默认系统临时目录），并在任务成功或失败后按策略清理。

### 4.3 packages/dysub-core/asr (ASR 客户端模块)

*   **FR-3.1 用户自持 Key：** 运行时从本地环境变量 `DYSUB_ASR_API_KEY` 或配置文件 `~/.config/dysub/config.yaml` 读取密钥。**严禁在代码中硬编码密钥或代理用户请求。**
*   **FR-3.2 协议兼容：** 封装 OpenAI 官方 SDK 或标准 HTTP Client，对外暴露 `transcribe(file_path, language, response_format) -> str` 接口。
*   **FR-3.3 强控输出格式：** 请求参数必须包含 `response_format="srt"`（或 `"vtt"`），直接向 ASR 服务商索要带时间戳的字幕文本。
*   **FR-3.4 分片合并：** 若输入为切片列表，依次请求 API，通过解析 SRT 结构将后续分段的时间戳顺延叠加（如第二段起点增加 600 秒），合并为完整 SRT 字符串。

### 4.4 packages/dysub-core/subtitle (字幕后处理模块)

*   **FR-4.1 时间戳修正：** 处理切片边界时，确保合并后的字幕时间戳连续无重叠、无跳变。
*   **FR-4.2 格式导出：** 支持输出标准 SRT 与 WebVTT 格式文件。
*   **FR-4.3 简单后处理（可选）：** 去除明显的重复字词（如 ASR 产生的 "啊啊啊啊" 重复）、修正中英文混排标点空格，提升可读性。

### 4.5 apps/webui (本地交互界面)

*   **FR-5.1 本地服务：** 启动后绑定 `127.0.0.1`（禁止 `0.0.0.0` 暴露至公网），默认端口 `7860`（Gradio）或 `8080`（FastAPI）。
*   **FR-5.2 输入选择：** 提供标签页切换：【本地文件上传】/【粘贴链接】。若链接类型需要未安装的插件，实时提示安装命令。
*   **FR-5.3 实时进度：** 展示当前步骤（解析中 / 音频提取中 / 转写中 / 合并中），支持批量任务卡片流，独立显示各任务进度。
*   **FR-5.4 结果看板：** 转写完成后，内嵌文本框展示字幕内容，提供【一键复制】与【下载 SRT / VTT】按钮。

### 4.6 CLI 入口

*   **FR-6.1 基础命令：** `dysub process <source> --output ./subs/ --lang zh --format srt`
*   **FR-6.2 配置检查：** `dysub doctor` 检查 FFmpeg 是否安装、API Key 是否配置、可选插件是否可用。
*   **FR-6.3 进度输出：** 终端实时打印进度条与日志（`rich` 库）。

---

## 5. 非功能需求与健壮性设计 (Non-Functional Requirements)

### 5.1 隐私与数据安全

*   **NFR-1.1 零上传原则：** 除向用户自行指定的 ASR API 服务商发送音频数据外，不得向任何其他服务器发送数据。
*   **NFR-1.2 密钥本地存储：** API Key 仅允许存储在本地环境变量或用户主目录下的配置文件中，权限建议设为 `600`。
*   **NFR-1.3 临时文件清理：** 任务完成后（无论成功或失败），默认自动清理临时音频文件。可通过 `DYSUB_KEEP_TEMP=1` 保留用于调试。

### 5.2 资源自限（本地友好）

*   **NFR-2.1 并发控制：** 本地 asyncio 的并发请求数必须限制（如默认最多同时向 ASR 发送 2 个请求），避免用户因误操作同时转写 10 个长视频导致内存/带宽耗尽。
*   **NFR-2.2 FFmpeg 资源隔离：** 调用 FFmpeg 时设置 CPU 亲和性与内存上限（通过 `ulimit` 或进程参数），防止单任务拖垮用户本地机器。

### 5.3 错误处理矩阵

所有异常在本地流水线顶层统一捕获，转化为用户友好的终端/界面提示，并写入本地日志 `~/.local/share/dysub/logs/`。

| 异常类型 | 根本原因 | 处理策略 | 用户提示 |
|---|---|---|---|
| `InputNotSupported` | 输入源未安装对应插件 | 提示安装命令 | "暂不支持该平台，请安装 pip install dysub-input-xxx" |
| `ParserError` | 平台接口变动或链接失效 | 不重试，标记失败 | "链接解析失败，目标平台接口可能已更新" |
| `APIQuotaExceeded / HTTP 429` | ASR 服务商触发频率限制 | 指数退避重试 3 次（1s, 2s, 4s） | "ASR 服务繁忙，正在重试（第 X/3 次）..." |
| `AudioProcessError` | 音视频流断开或 FFmpeg 崩溃 | 清理临时文件，标记失败 | "音频提取失败，源文件可能已损坏或失效" |
| `ContentFilterError` | ASR 服务商返回内容拦截 | 不重试，标记失败 | "ASR 服务商拒绝处理该音频（可能触发内容合规限制）" |
| `InvalidAPIKey` | 用户配置的 Key 无效 | 立即停止 | "API Key 无效，请通过 dysub doctor 检查配置" |

### 5.4 可扩展性

*   **NFR-3.1 输入源插件化：** 新增平台支持时，只需新建一个 `dysub-input-<platform>` 包，实现 `BaseInputAdapter` 接口，无需修改核心代码。
*   **NFR-3.2 ASR 服务商扩展：** 核心 ASR 客户端应预留非 OpenAI 标准接口的扩展点（如阿里云、讯飞等可通过适配器模式接入）。

---

## 6. 本地部署与安装方案

### 6.1 推荐安装（pip）

```bash
# 基础功能（本地文件转字幕）
pip install dysub-core

# 完整功能（含抖音解析 + Web UI）
pip install dysub-core[douyin,webui]

# 配置 API Key
export DYSUB_ASR_API_KEY="sk-xxxxxxxx"

# 运行
dysub process ./video.mp4 --output ./subs/
# 或启动本地 WebUI
dysub webui
```

### 6.2 可选容器化（Docker）

为追求完全隔离环境或避免本地安装 FFmpeg 的用户提供可选 Dockerfile，**不作为核心部署方式**：

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/dysub-core /app/packages/dysub-core
COPY apps/webui /app/apps/webui
RUN pip install /app/packages/dysub-core[douyin,webui]

ENV DYSUB_ASR_API_KEY=""
EXPOSE 7860

CMD ["dysub", "webui", "--host", "127.0.0.1", "--port", "7860"]
```

**注意**：Docker 运行时必须通过环境变量注入用户自己的 API Key，镜像本身不得包含任何密钥。

```bash
docker run -e DYSUB_ASR_API_KEY="sk-xxx" -v $(pwd)/output:/app/output -p 7860:7860 dysub
```

---

## 7. 开源治理与社区边界

### 7.1 插件与核心解耦
- `dysub-core` 仓库作为官方主仓库，**不包含任何平台破解算法**。
- `dysub-input-douyin` 等涉及平台逆向的插件可作为独立仓库维护，通过 PyPI 与 `entry_points` 机制接入。
- 主仓库 README 中仅演示本地文件功能，网络解析插件的文档由各自仓库维护。

### 7.2 Issue 与 PR 规范
- 不接受任何要求开发者提供在线 Demo、托管服务或共享 API Key 的 Issue。
- 不接受将 WebUI 默认绑定 `0.0.0.0` 的 PR，防止用户误将本地服务暴露至公网。

---

## 8. 免责声明（项目级）

> **DySub 是一个本地运行的开源字幕提取工具，开发者不运营任何在线服务，也不对用户使用本工具的行为负责。**
>
> 1. 用户须自行获取并遵守第三方 ASR 服务商的使用条款，自行承担 API 调用费用。
> 2. 用户须确保对处理的音视频内容拥有合法权利。使用网络链接解析功能时，须遵守相应平台的服务条款（ToS）。
> 3. 本项目提供的代码仅供个人学习、研究与合法的内容无障碍处理使用。
> 4. 任何因违反法律法规或平台规则而产生的后果，由使用者自行承担。如认为本项目代码侵犯您的合法权益，请联系仓库维护者协商处理。

---

通过这一版本地优先、插件化、零托管的架构设计，DySub 既能在 GitHub 上以高质量开源工程的形式持续演进，又能将合规风险控制在开源社区广泛接受的范畴内，与 `yt-dlp`、`you-get` 等成熟本地工具处于同一风险水位。
