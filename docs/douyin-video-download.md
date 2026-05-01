# 抖音视频下载技术文档

## 支持的 URL 格式

| 格式 | 示例 | 说明 |
|------|------|------|
| 喜欢页弹窗 | `https://www.douyin.com/user/self?from_tab_name=main&modal_id={id}&showTab=like` | 从"喜欢"列表打开视频弹窗 |
| 直接弹窗 | `https://www.douyin.com/user/self?modal_id={id}` | 直接打开指定视频弹窗 |

两种 URL 的视频详情数据（`videoDetail`）均嵌入在页面的 SSR 数据中。

## 数据提取方式

### 数据来源：SSR `self.__pace_f` 或 `<script>` 标签

抖音 PC 端使用 React Server Components（`self.__pace_f`）进行 SSR 渲染。视频详情数据以 URL 编码的 JSON 嵌入在页面中。

**提取步骤：**

1. 遍历 `self.__pace_f` 数组或 `document.querySelectorAll('script')`
2. 对每个 chunk 的文本执行 `decodeURIComponent()` 解码
3. 搜索包含目标 `modal_id`（即 `awemeId`）的 chunk
4. 找到 `videoDetail` 对象，提取所需字段

### Chrome DevTools 自动化方式

通过 Chrome DevTools MCP 工具自动化操作：

1. **导航到视频页面** — `navigate_page` 或 `new_page`
2. **提取视频 URL** — 通过 `evaluate_script` 在页面上下文执行 JS：
   ```javascript
   // 方法1：从 SSR 数据提取（推荐，数据最全）
   const chunks = self.__pace_f || [];
   // 或遍历 document.querySelectorAll('script')
   for (const chunk of chunks) {
     const decoded = decodeURIComponent(chunk[1]);
     if (decoded.includes('{modal_id}') && decoded.includes('playAddr')) {
       // 提取 videoDetail 中的数据
     }
   }

   // 方法2：从 video 元素直接获取（仅能得到 blob 或当前播放地址）
   const videos = document.querySelectorAll('video');
   videos.forEach(v => console.log(v.currentSrc));
   ```
3. **下载视频和封面** — 用 `curl` 带 Referer 和 User-Agent 头下载

## videoDetail 数据结构

```
videoDetail
├── awemeId          // 视频 ID，即 URL 中的 modal_id
├── groupId          // 分组 ID，通常与 awemeId 相同
├── desc             // 视频描述（含话题标签）
├── caption          // 视频描述副本
├── createTime       // 发布时间戳（秒）
├── mediaType        // 媒体类型（4=视频）
├── authorInfo       // 作者信息 ⬇️
│   ├── uid          // 作者 UID
│   ├── secUid       // 加密 UID
│   ├── nickname     // 昵称
│   ├── avatarUri    // 头像 URL
│   ├── followerCount     // 粉丝数
│   ├── totalFavorited    // 总获赞数
│   ├── followStatus      // 关注状态（1=已关注）
│   ├── avatarThumb       // 头像缩略图 { urlList: [] }
│   └── roleTitle         // 角色（"作者"）
├── video            // 视频信息 ⬇️
│   ├── width / height   // 分辨率
│   ├── ratio            // 画质标签（如 "720p", "1080p"）
│   ├── duration         // 时长（毫秒）
│   ├── dataSize         // 文件大小（字节）
│   ├── uri              // 视频 URI
│   ├── playAddr         // MP4 播放地址 [{ src: "url" }]
│   ├── playAddrH265     // H265 播放地址 [{ src: "url" }]
│   ├── bitRateList      // 多码率列表 ⬇️
│   │   └── { playAddr, dataSize, width, height, qualityType, gearName, fps, bitRate, format }
│   ├── cover            // 封面图 URL（裁剪版）
│   ├── coverUrlList     // 封面图 URL 列表
│   ├── originCover      // 原始封面图 URL
│   └── dynamicCover     // 动态封面图 URL
├── textExtra        // 话题标签列表
│   └── { hashtagId, hashtagName, start, end }
├── userDigged       // 是否已点赞
├── userCollected    // 是否已收藏
└── awemeControl     // 权限控制
    ├── canComment
    ├── canForward
    ├── canShare
    └── canShowComment
```

## 关键 URL 字段说明

### 视频播放地址（playAddr）

```
https://v26-web.douyinvod.com/{token}/{expire}/video/tos/cn/{path}/?a=6383&br=1192&bt=1192&mime_type=video_mp4&...
```

- `token` — 临时鉴权 token，会过期
- `expire` — 过期时间戳（十六进制）
- `br` / `bt` — 码率参数
- 多个 CDN 节点：`v26-web.douyinvod.com`、`v11-weba.douyinvod.com`

### 封面图地址（cover）

```
https://p3-pc-sign.douyinpic.com/{path}~tplv-dy-resize-origshort-autoq-75:330.jpeg?...
```

- `tplv-dy-resize-origshort-autoq-75:330` — 图片处理模板（宽高比裁剪）
- `originCover` — 原始比例封面（`tplv-dy-360p.jpeg`）
- `dynamicCover` — 动态封面（WebP/GIF）

### 备用 API（playApi）

```
https://www.douyin.com/aweme/v1/play/?file_id={}&video_id={}&sign={}&aid=6383
```

可直接访问的视频播放 API，参数来自 videoDetail。

## 下载方法

### curl 下载（需带请求头）

```bash
# 下载视频
curl -L -o "{modal_id}.mp4" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Referer: https://www.douyin.com/" \
  "{playAddr_url}"

# 下载封面
curl -L -o "{modal_id}_cover.jpeg" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Referer: https://www.douyin.com/" \
  "{cover_url}"
```

### 注意事项

- 视频播放地址含有时效性 token，过期后无法下载
- 必须携带 `Referer: https://www.douyin.com/` 头，否则会被拒绝
- `User-Agent` 需模拟浏览器
- 部分视频使用 blob URL 播放（`blob:https://...`），此时需从 SSR 数据获取真实 MP4 地址

## 文件命名规范

```
{modal_id}.mp4            // 视频文件
{modal_id}_cover.jpeg     // 封面图
```

## 已下载示例

| modal_id | 作者 | 描述 | 视频 | 封面 |
|----------|------|------|------|------|
| 7634723394579429221 | 羊羊不吃草 | 五一快乐～#活力女高 #peng一下击中你 #你的理想型 | 1.5MB | 16KB |
| 7628517340775184362 | Rhea | 如果你有我就够了那么我也是 | 1.0MB | 23KB |

## 作者信息获取方式

作者信息在 `videoDetail.authorInfo` 中，包含：

| 字段 | 说明 | 示例 |
|------|------|------|
| `nickname` | 昵称 | "羊羊不吃草" |
| `uid` | 数字 UID | "2344592313680611" |
| `secUid` | 加密 UID | "MS4wLjABAAAA..." |
| `avatarUri` | 头像 | `https://p3-pc.douyinpic.com/aweme/100x100/...` |
| `followerCount` | 粉丝数 | 83507 |
| `totalFavorited` | 总获赞 | 849042 |
| `followStatus` | 是否关注 | 1=已关注 |
| `avatarThumb.urlList` | 头像缩略图列表 | |

## 视频描述获取方式

- `videoDetail.desc` — 视频完整描述文本（含 # 话题标签）
- `videoDetail.caption` — 描述副本
- `videoDetail.textExtra[]` — 话题标签结构化数据，每个标签包含：
  - `hashtagName` — 话题名称
  - `hashtagId` — 话题 ID
  - `start` / `end` — 在 desc 文本中的起止位置
