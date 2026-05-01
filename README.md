# Douyin Downloader

基于 mitmproxy 的抖音视频自动下载器。浏览抖音时自动拦截 HTTPS 流量，检测用户点赞/收藏行为，下载视频和封面，使用 Bloom Filter 去重。

## 工作原理

1. 启动本地 HTTPS 代理（mitmproxy）
2. 自动打开 Chrome 浏览器并配置代理
3. 拦截抖音视频详情 API 和 SSR 页面数据
4. 检查 `userDigged`（点赞）和 `userCollected`（收藏）字段
5. 仅下载用户点赞或收藏的视频，跳过普通浏览的视频
6. Bloom Filter 去重，避免重复下载

## 安装

需要 Python 3.13+ 和 [uv](https://docs.astral.sh/uv/) 包管理器。

```bash
git clone <repo-url>
cd douyin_downloader
uv sync
```

## 使用

### 快速开始

```bash
make run
```

启动代理并自动打开 Chrome，登录抖音后正常浏览即可。点赞或收藏过的视频会自动下载到 `downloads/` 目录。

### 常用命令

| 命令 | 说明 |
|------|------|
| `make run` | 启动代理 + 自动打开 Chrome |
| `make run-no-browser` | 仅启动代理，手动配置浏览器 |
| `make stop` | 停止代理 |
| `make reset` | 重置去重过滤器 |
| `make clean` | 清理已下载的文件 |

### 自定义端口

```bash
PORT=8082 make run
```

### 命令行参数

```bash
uv run python -m src.main [OPTIONS]

选项:
  --port PORT           代理端口 (默认: 8081)
  --download-dir DIR    下载目录 (默认: downloads)
  --reset-filter        启动前重置 Bloom Filter
  --no-browser          不自动启动 Chrome
```

## 首次使用说明

1. 运行 `make run`，Chrome 会自动打开
2. 首次需要登录抖音账号
3. 浏览视频时，点击进入你点赞或收藏过的视频详情页
4. 视频和封面会自动下载到 `downloads/` 目录
5. 登录状态会保存在 `~/.douyin-downloader/chrome/`，后续无需重新登录

## 项目结构

```
src/
├── main.py          # CLI 入口，mitmproxy 启动，Chrome 自动启动
├── addon.py         # Mitmproxy 插件：流量拦截、点赞门控、URL 匹配
├── downloader.py    # 异步视频/封面下载器 (aiohttp)
├── dedup.py         # Bloom Filter 去重
└── catalog.py       # JSONL 元数据目录

downloads/           # 下载文件存放目录
Makefile             # 常用命令快捷方式
```

## 技术细节

### 流量拦截

支持两种数据来源：

- **API 模式**: 拦截 `/aweme/v1/web/aweme/detail/` JSON 响应
- **SSR 模式**: 解析 `https://www.douyin.com/user/self` 页面中的 `self.__pace_f` 数据块

### 点赞门控

在 `_process_aweme_item` 中检查视频的 `userDigged` 和 `userCollected` 字段（兼容 camelCase 和 snake_case）。两者都为 false 时跳过下载并记录日志。

### 去重机制

使用 Bloom Filter（容量 10000，误判率 1%）对视频 ID 去重，持久化到 `downloads/bloom_filter.bin`。

### 元数据记录

每个视频记录一条 JSON 到 `downloads/videos.jsonl`，包含：

- 视频ID、作者信息、描述、标签
- 视频URL、封面URL、时长
- 创建时间、文件路径

## 依赖

- **mitmproxy** >= 10.0 — HTTPS 代理
- **aiohttp** >= 3.9 — 异步 HTTP 下载
- **pybloom_live** >= 4.0 — Bloom Filter

## License

MIT
