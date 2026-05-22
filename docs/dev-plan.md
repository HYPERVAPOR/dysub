# DySub 开发执行计划

## 目标

基于 `/home/hv/projs/dysub/docs/prd.md`（本地优先、插件化字幕提取工具），制定一份**可追踪、可验收**的开发计划，并在获得用户批准后，将其输出为 `docs/dev-plan.md`。

计划采用**里程碑（Milestone）+ 可验收任务（Task）**两级结构，每个任务附带明确的完成标准和交付物。所有开发按优先级串行推进，部分模块内任务可并行。

---

## 1. 项目当前状态

- **PRD 已完成**：`/home/hv/projs/dysub/docs/prd.md`
- **代码库为空**：仅包含 `.git/`、`README.md`（空）、`docs/prd.md`
- **技术决策（PRD 已确认）**：
  - 运行时：Python 3.10+，纯 `asyncio`
  - CLI：Typer + Rich
  - WebUI：Gradio（轻量本地优先）
  - 音频：FFmpeg 流式处理
  - ASR：OpenAI 兼容 SDK，用户自备 Key
  - 插件：Python `entry_points` 机制

---

## 2. 里程碑总览

| 里程碑 | 目标 | 核心交付物 | 预估工作量 |
|---|---|---|---|
| **M0** | 工程基建与骨架搭建 | 目录结构、CI、Lint、数据模型 | 0.5 d |
| **M1** | dysub-core 核心库 | 音频处理、ASR 客户端、字幕合并、流水线 | 2 d |
| **M2** | CLI + 插件体系 | 插件接口、本地文件适配器、CLI 入口、抖音插件 | 1.5 d |
| **M3** | 本地 WebUI | Gradio 界面、批量任务、结果下载 | 1 d |
| **M4** | 测试与打包 | 单元测试、集成测试、Docker、README | 1 d |
| **M5** | 发布准备 | PyPI 配置、GitHub Release、CHANGELOG | 0.5 d |

**关键路径**：M0 → M1 → M2 → M3 → M4 → M5

---

## 3. 详细任务分解与验收标准

### M0: 工程基建与骨架搭建（第 1 天上午）

#### [x] T0.1 创建 Monorepo 目录结构
- **内容**：按 PRD 2.3 节创建目录树，初始化各包的 `pyproject.toml`
- **交付物**：
  ```
  dysub/
  ├── packages/dysub-core/pyproject.toml
  ├── packages/dysub-input-local/pyproject.toml
  ├── packages/dysub-input-douyin/pyproject.toml
  ├── apps/webui/pyproject.toml
  ├── tests/
  ├── .github/workflows/ci.yml
  ├── Dockerfile
  └── Makefile
  ```
- **验收标准**：`make install` 能一键安装所有本地包到虚拟环境，无 import error

#### [x] T0.2 配置开发工具链
- **内容**：`pre-commit` + `ruff`（lint + format）+ `pytest` + `mypy`（可选）
- **交付物**：`.pre-commit-config.yaml`、`pyproject.toml`（统一 ruff 规则）、`Makefile`（含 `make test`、`make lint`）
- **验收标准**：`make lint` 全绿，`make test` 能运行（即使暂时 0 个测试也正常退出）

#### [x] T0.3 定义核心数据模型
- **内容**：`packages/dysub-core/dysub_core/models.py`
- **模型清单**：
  - `MediaSource`（stream_url, metadata, source_type）
  - `AudioChunk`（file_path, start_offset_seconds, duration_seconds）
  - `TranscriptionResult`（raw_srt, language, segments）
  - `TaskConfig`（temp_dir, output_dir, api_key, concurrency_limit）
  - 自定义异常基类 `DySubError` 及子类（`InputNotSupported`, `ParserError`, `AudioProcessError`, `APIQuotaExceeded`, `InvalidAPIKey`, `ContentFilterError`）
- **验收标准**：所有模型能通过 `pytest` 序列化/反序列化测试，异常类能正确携带 message 和 context

---

### M1: dysub-core 核心库（第 1 天下午 ~ 第 3 天）

#### [x] T1.1 音频处理模块（audio/processor.py）
- **内容**：
  - `extract_audio(source: MediaSource) -> Path`：FFmpeg 流式提取，输出 WAV 16kHz mono
  - `chunk_audio(wav_path: Path, max_size_mb: int = 25, chunk_duration_sec: int = 600) -> list[AudioChunk]`：按体积/时长切片
  - `get_audio_duration(path: Path) -> float`
- **技术要点**：使用 `ffmpeg-python` 或直接用 `asyncio.create_subprocess_exec` 调用 FFmpeg，避免阻塞事件循环
- **验收标准**：
  - 提供 `tests/assets/sample.mp4`（放一个 5MB 以内的测试视频），`extract_audio` 输出符合格式要求（通过 `ffprobe` 验证采样率、声道数）
  - `chunk_audio` 对 30MB 的测试 WAV 正确切为 3 段，每段偏移量计算正确
  - 所有函数都有对应单元测试

#### [x] T1.2 ASR 客户端模块（asr/client.py）
- **内容**：
  - `ASRClient` 类，支持 OpenAI 兼容 API（base_url, api_key 可配置）
  - `transcribe(file_path: Path, language: str, response_format: str = "srt") -> str`
  - 集成 `tenacity` 做指数退避重试（429 / 网络抖动），最多 3 次（1s, 2s, 4s）
  - 正确处理 `InvalidAPIKey`（401）、`ContentFilterError`（特定状态码或内容过滤响应）、`APIQuotaExceeded`（429）
- **验收标准**：
  - 使用 `pytest-httpx` 或 `responses` Mock OpenAI API，测试正常响应、429 重试、401 抛异常、SRT 格式返回
  - 重试次数和退避间隔符合 PRD 要求

#### [x] T1.3 字幕合并与后处理模块（subtitle/merger.py）
- **内容**：
  - `parse_srt(srt_text: str) -> list[SubtitleSegment]`：解析 SRT 为标准结构
  - `merge_chunks(chunks: list[tuple[str, float]]) -> str`：多段 SRT 按偏移量合并，修正时间戳
  - `export_vtt(segments: list[SubtitleSegment]) -> str`
  - `postprocess(srt_text: str) -> str`：去除连续重复字词、修正标点空格（可选，基础实现即可）
- **验收标准**：
  - 提供两段测试 SRT（第一段 0:00-0:05，第二段 0:00-0:03），合并后第二段时间戳正确顺延为 0:05-0:08，无重叠
  - VTT 输出格式通过 W3C 简单校验（文件头、时间码格式）

#### [x] T1.4 流水线编排（pipeline.py）
- **内容**：
  - `Pipeline` 类，串联：输入适配 → 音频提取 → 分片 → ASR → 合并 → 输出
  - 支持进度回调 `Callable[[str, float], None]`（stage_name, progress_0_to_1）
  - 全局异常捕获：任何步骤失败时清理临时文件，返回结构化错误
  - 并发控制：Semaphore 限制同时向 ASR 发送的请求数（默认 2）
- **验收标准**：
  - 集成测试：从本地 MP4 到输出 SRT 文件，全流程跑一次通过
  - 模拟 ASR 失败，验证临时文件被正确清理（`DYSUB_KEEP_TEMP=0` 时）
  - 并发 3 个任务时，ASR 请求最多同时 2 个（通过日志或 mock 断言）

---

### M2: CLI + 插件体系（第 3 天 ~ 第 4.5 天）

#### [x] T2.1 插件接口与发现机制
- **内容**：
  - `BaseInputAdapter` 抽象类（`resolve(source: str) -> MediaSource`）
  - `discover_inputs() -> dict[str, BaseInputAdapter]`：通过 `importlib.metadata.entry_points(group="dysub.inputs")` 自动发现
  - `get_input_for_url(url: str) -> BaseInputAdapter`：根据 URL 模式匹配（如 `file://`、本地路径、`https://v.douyin.com`）
- **交付物**：`packages/dysub-core/dysub_core/inputs/base.py`、`registry.py`
- **验收标准**：编写一个 mock 插件包，安装后能被 `discover_inputs()` 正确发现

#### [x] T2.2 本地文件输入插件（dysub-input-local）
- **内容**：
  - `LocalFileAdapter` 实现 `BaseInputAdapter`
  - 支持扩展名：`.mp4`, `.mkv`, `.mov`, `.mp3`, `.wav`, `.m4a`, `.flac`
  - 本地路径直接包装为 `MediaSource`
- **验收标准**：`dysub process ./test.mp4` 能正确路由到本地适配器

#### [x] T2.3 CLI 入口
- **内容**：
  - `apps/webui` 或 `packages/dysub-core` 内建 CLI（推荐后者，避免过度拆分）
  - 命令：
    - `dysub process <source> --output ./subs/ --lang zh --format srt`
    - `dysub doctor`：检查 FFmpeg、API Key、已安装插件
    - `dysub webui`：启动 Gradio（实际依赖 M3）
  - 终端进度：使用 `rich.progress` 或 `typer` 原生进度，显示当前 stage
- **验收标准**：
  - `dysub doctor` 在没有 FFmpeg 时正确报错提示安装
  - `dysub process ./sample.mp4 --lang zh` 成功生成 `./subs/sample.srt`
  - CLI `--help` 完整、参数命名符合直觉

#### [~] T2.4 抖音输入插件（dysub-input-douyin）【可选，延后至 M5 或社区贡献】
- **内容**：
  - `DouyinAdapter`：短链 302 追踪、X-Bogus 签名、提取无水印 MP4 直链
  - 视频删除/私密时抛出 `VideoNotFoundError`
- **验收标准**：
  - 提供 3 个真实抖音链接测试（公开视频、已删除视频、私密视频），分别验证成功/异常
  - **注意**：此任务依赖外部平台接口，验收时如接口变动，允许标记为 `blocked` 并记录 issue，不阻塞其他里程碑

---

### M3: 本地 WebUI（第 4.5 天 ~ 第 5.5 天）

#### [x] T3.1 Gradio 界面搭建
- **内容**：`apps/webui/app.py` 或 `dysub_core/webui.py`
  - 输入区：文件上传（`gr.File`）+ 链接输入框（`gr.Textbox`）
  - 配置区：语言选择、输出格式（SRT/VTT）、API Key 输入（可选，优先读环境变量）
  - 进度区：`gr.Markdown` 或 `gr.JSON` 实时显示 stage
  - 结果区：字幕预览文本框 + 下载按钮
  - 绑定 `127.0.0.1`，禁止 `0.0.0.0`
- **验收标准**：
  - 浏览器访问 `http://127.0.0.1:7860`，上传本地视频，全流程跑通并下载 SRT
  - 未安装抖音插件时粘贴抖音链接，界面友好提示 `pip install dysub-input-douyin`

#### [x] T3.2 批量任务支持
- **内容**：支持用户同时提交多个任务，以列表/卡片形式展示各自进度
- **验收标准**：同时上传 2 个视频，界面独立显示两个任务的进度，互不干扰

---

### M4: 测试与打包（第 5.5 天 ~ 第 6.5 天）

#### [x] T4.1 单元测试覆盖（覆盖率 94%，超过 80% 阈值）
- **内容**：为 M1/M2 所有核心函数编写测试
- **验收标准**：`pytest --cov=dysub_core tests/` 覆盖率 **≥ 80%**（pipeline 和异常路径必须覆盖）

#### [x] T4.2 集成测试（全流程 Mock + 真实 FFmpeg 测试通过）
- **内容**：
  - `tests/integration/test_full_pipeline.py`：端到端测试
  - 使用一个小型真实视频（< 30 秒），验证从输入到 SRT 的完整链路
  - Mock ASR 响应与真实 ASR 响应各跑一遍（真实测试需用户本地配置 Key，标记为 `pytest.mark.integration`）
- **验收标准**：`pytest tests/integration/` 全部通过（Mock 部分必过，真实部分可选但推荐）

#### [x] T4.3 Docker 支持（docker build 成功，twine check 通过）
- **内容**：根目录 `Dockerfile`，基于 `python:3.11-slim`，内置 FFmpeg
- **验收标准**：`docker build -t dysub .` 成功，`docker run -e DYSUB_ASR_API_KEY=xxx dysub dysub doctor` 输出正常

#### [x] T4.4 README 与使用文档
- **内容**：
  - 安装方式（pip / Docker）
  - 快速开始示例（CLI + WebUI）
  - 环境变量说明
  - 插件安装说明
  - 免责声明（引用 PRD 第 8 节）
- **验收标准**：一个新用户按照 README 能在 5 分钟内跑通第一个字幕提取任务

---

### M5: 发布准备（第 6.5 天 ~ 第 7 天）

#### [x] T5.1 PyPI 发布配置（build + twine check 通过）
- **内容**：各 `pyproject.toml` 配置好 `name`, `version`, `classifiers`, `license`，根目录配 `scripts/build.sh`
- **验收标准**：`python -m build packages/dysub-core` 生成有效 wheel，可通过 `twine check`

#### [x] T5.2 GitHub CI/CD（ci.yml 已配置，push/tag 触发）
- **内容**：`.github/workflows/ci.yml`（lint + test）、`release.yml`（tag 触发自动发 PyPI）
- **验收标准**：push 到 main 分支时 CI 全绿，打 tag `v0.1.0` 时自动发布 dysub-core 到 PyPI

#### [x] T5.3 开发计划归档（docs/dev-plan.md 已写入）
- **内容**：将本计划正式写入 `docs/dev-plan.md`
- **验收标准**：文件存在，与 plan 文件内容一致

---

## 4. 任务依赖关系图

```
T0.1 目录结构 ──┬──> T0.2 工具链 ──> T0.3 数据模型 ──┬──> T1.1 音频处理
                                                   ├──> T1.2 ASR 客户端
                                                   ├──> T1.3 字幕合并
                                                   └──> T2.1 插件接口

T1.1 / T1.2 / T1.3 ──> T1.4 流水线编排
T1.4 / T2.1 / T2.2 ──> T2.3 CLI 入口
T2.3 ──> T3.1 WebUI
T1.4 / T2.3 ──> T4.2 集成测试
T4.1 / T4.2 / T4.3 / T4.4 ──> M5 发布
```

---

## 5. 风险与应对

| 风险 | 影响 | 应对策略 |
|---|---|---|
| 抖音接口变动导致 T2.4 失败 | M2 延期 | T2.4 明确标记为**可选**，接口变动时先 skip，不阻塞整体发布 |
| FFmpeg 流式处理复杂度高 | T1.1 超期 | 先以 `subprocess` 异步调用实现 MVP，后续再优化为纯内存流 |
| ASR API 费用 | 测试成本高 | 所有自动化测试使用 Mock；真实测试标记为 `integration`，手动触发 |
| Gradio 绑定 127.0.0.1 在某些环境受限 | M3 验收困难 | 提供 `--host` 参数但默认 127.0.0.1，文档说明安全原因 |

---

## 6. 用户审批后执行步骤

用户通过本计划后，将按以下顺序执行：

1. **立即创建** `docs/dev-plan.md`，将本计划内容正式写入项目文档
2. **从 M0 开始编码**：搭建目录结构、配置工具链、定义数据模型
3. **每完成一个里程碑**后向用户汇报进度与验收结果
4. **如遇阻塞**（如抖音接口变动），按风险应对策略调整并同步用户

---

*本计划基于 PRD v1.0（本地优先版）制定，总预估工作量 6.5 ~ 7 天（单人全负荷）。*
