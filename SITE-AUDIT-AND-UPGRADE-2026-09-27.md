# NAVIER YACHTS 网站审计与升级报告

**审计对象**：navieryacht.com（实际生效域名 www.navieryacht.com）
**审计时间**：2026-09-27
**代码基线**：`main` 分支 `32de078`（2026-06-17「全站品牌重构」）
**托管现状**：腾讯云 EdgeOne Pages（`Server: edgeone-pages`）
**审计方式**：本地代码静态审查 + 线上实测（DNS / HTTP 响应头 / 资源体积 / 端到端请求）

---

## 一、总体结论

站点视觉与内容（品牌重构后）已经到位，**SEO 元数据、结构化数据、alt 文本、H1 层级这些基础项做得相当规范**，这部分不输给大多数中小船厂官网。

但存在 **3 个致命问题**，其中 1 个正在持续造成业务损失（询盘丢失），另外 2 个正在持续损害搜索排名。性能层面则因为「原始大图 + 零缓存」的组合，实际访问体验远低于站点应有的水平。

按严重程度分四档，共 **26 项**。

---

## 二、P0 — 致命问题（正在持续造成损失）

### P0-1 ⛔ 询盘表单是空的，每一封询盘都在丢失

**证据**：

```
contact.html:136   <form id="contactForm" action="#" method="post">
js/footer.js:21    <form action="#" method="post">
```

全局搜索 `contactForm`、`submit` 事件监听、`fetch(`、`XMLHttpRequest`、以及 Formspree / Web3Forms / EmailJS 等第三方表单服务 —— **全部为零**（`js/` 与所有 `*.html` 均无匹配）。

**后果**：访客填写姓名、电话、邮箱、项目描述，点击「Submit Build Enquiry」后：
- 表单提交到当前页面（`action="#"`）
- 没有任何 JS 拦截、没有 `fetch`、没有邮件服务
- **数据直接消失，用户看到页面刷新，没有任何成功或失败反馈**

这不是"可能有问题"，是**每一个潜在客户的联系方式都在被静默丢弃**。页脚「Project & Build Updates」订阅框同理，`action="#"` 无处理，订阅全部丢失。

对于一个以「Start a Build Enquiry」为核心转化路径的制造品牌官网，这是**最高优先级**。

**修复方向**（按落地成本排序）：
| 方案 | 成本 | 说明 |
|---|---|---|
| EdgeOne Pages 函数 / 云函数接收 POST 并转发邮件 | 低 | 与现有托管同平台，无需新服务 |
| 接第三方表单服务（Web3Forms / Formspree） | 最低 | 改 `action` 即可，5 分钟 |
| 接企业邮箱 SMTP + 服务端 | 中 | 可控性最好 |

无论哪种，都必须补上：**提交中状态、成功提示、失败提示、防重复提交、前端校验、蜜罐反垃圾字段**。

---

### P0-2 ⛔ 全站 canonical / sitemap / og:url 指向一个 404 域名

**证据**（9 个页面的 canonical 全部指向根域，所有 og:url 同理）：

```html
<link rel="canonical" href="https://naiveryacht.com/index.html">   <!-- 返回 404 -->
<link rel="canonical" href="https://naiveryacht.com/about.html">   <!-- 返回 404 -->
... 9/9 页面全部如此
```

`sitemap.xml` 中 9 条 `<loc>` 也全部是 `https://naiveryacht.com/...`；`index.html` 的 JSON-LD `"url": "https://naiveryacht.com"` 同样是这个返回 404 的地址。

**实测确认**：`https://naiveryacht.com/index.html` → **HTTP 404**（详见上一份 DNS 诊断报告）。

**后果**：
- Google 抓取 `www.navieryacht.com` 页面时，canonical 指向另一个地址，而那个地址返回 404 → Google 会判定 canonical 无效，**或者直接把 www 版本视为重复内容不作索引**
- `sitemap.xml` 提交给 Search Console 后全部 404，站点可能被大面积降权或去索引
- 社媒分享、结构化数据全部指向失效地址

这是**与根域 DNS 问题叠加的双重打击**：DNS 修好后这个问题部分自动消失，但 `sitemap.xml` 与 canonical 中 `/index.html` 的写法仍应优化为 `/`。

**修复**：先修 DNS（上一份报告方案 B），再把 canonical / sitemap 统一到 `https://www.navieryacht.com/` 或决定唯一主域后全量对齐。

---

### P0-3 ⛔ 深度页面没有唯一主域策略，www 与根域长期双轨

`robots.txt` 中 `Sitemap: https://naiveryacht.com/sitemap.xml`，而站点实际只在 www 上可访问。加上没有做 www ↔ 根域的 301 归一，搜索引擎看到的是「两个域名、一个能用、一个 404」。

**修复**：确定唯一主域（建议 `https://www.navieryacht.com`，EdgeOne Pages 默认），另一边做 301 永久跳转。

---

## 三、P1 — 严重问题（性能 / 合规 / 信任）

### P1-1 图片完全没有做优化，是全站最大的性能瓶颈

**实测数据**：

| 文件 | 体积 |
|---|---|
| `images/18FT/Ready to ship 3.jpg` | **4.8 MB** |
| `images/18FT/Ready to ship 2.jpg` | **4.4 MB** |
| `images/Yachts/60ft catamaran.jpg` | **3.3 MB**（首页首屏主图） |
| `images/18FT/18ft sb.jpg` | 2.8 MB |
| `images/18FT/18ft stern.jpg` | 2.8 MB |
| `images/18FT/Ready to ship 1.jpg` | 2.8 MB |
| `images/Snakehead/1200/snakehead 1200.png` | 2.0 MB（PNG） |
| `images/18FT/Image_20251002200931_9_160.png` | 2.0 MB（PNG） |
| `images/Snakehead/2300/snakehead 2300.png` | 1.9 MB（PNG） |

**`images/` 总计 53 MB**。

线上实测该图片确实是 **4.79 MB 原样传输**：
```
GET /images/18FT/Ready%20to%20ship%203.jpg
Content-Type: image/jpeg
Content-Length: 5022497      ← 4.79 MB，未压缩、未转格式
```

**问题**：
1. 没有转 WebP / AVIF（同样画质可再降 60–80%）
2. 没有响应式 `srcset`，手机也在下载 4.8 MB 的桌面大图
3. 没有预生成多尺寸缩略图
4. 首页首屏主图 3.3 MB，直接拖垮 LCP

**预期收益**：全量 WebP 化 + srcset 后，`images/` 可从 53 MB 降到 5–8 MB，LCP 有望进入 2.5 秒内。

---

### P1-2 静态资源零缓存，每次访问都重新下载

**线上实测**（CSS 与图片一致）：

```
GET /css/style.css
Cache-Control: public,max-age=0,must-revalidate      ← max-age=0！
```

`max-age=0, must-revalidate` 意味着浏览器**每次页面访问都要重新校验每个静态资源**。加上 HTTP/1.1（实测 `http_version=1.1`，无 HTTP/2 多路复用），一个 53 MB 的图片库会被反复拉取。

**正确的做法**：静态资源统一 `Cache-Control: public, max-age=31536000, immutable`，配合文件名哈希或版本查询串做失效控制。这一项改动成本极低，收益极大。

> 附带确认：**Brotli 压缩是正常的**（`Content-Encoding: br`，style.css 36858 B → 7228 B），这一项无需处理。

---

### P1-3 隐私政策与服务条款是通用占位模板，存在合规风险

`privacy-policy.html`（3.9 KB）与 `terms-of-service.html`（5.6 KB）内容是放之四海皆准的通用条款：只有「我们收集信息 / 我们如何使用 / 我们共享」四个套路段落，**没有任何一条与本主体相关的实质信息**：

- ❌ 无公司注册主体全称与 **FZCO 执照编号**
- ❌ 无注册地址（仅有 Dubai 泛称）
- ❌ 无数据控制者（Data Controller）与数据保护官联系方式
- ❌ 无 **Cookie 政策**（站点用了 Font Awesome CDN，涉及第三方请求）
- ❌ 无数据留存期限
- ❌ 无跨境数据传输说明（迪拜 + 中国船厂双实体，这点尤其重要）
- ❌ 无 GDPR / 阿联酋 PDPL 的具体条款引用与用户权利行使路径
- ❌ 服务条款里无合同主体、准据法、争议解决地

**风险**：阿联酋已实施《个人数据保护法》（PDPL），欧盟访客涉及 GDPR。以「GDPR Compliant」作为 SEO 关键词却交付一份不含任何合规要素的模板，既无合规价值，也可能构成误导性陈述。**建议由法务出具正式版本。**

---

### P1-4 全站没有任何访问统计

全局搜索 `gtag` / `googletagmanager` / `analytics` / `umami` / `clarity` / `fbq` —— **零匹配**。

**后果**：不知道有多少访客、不知道他们看哪些船型、不知道转化漏斗在哪一步断掉、不知道 Google Ads 该不该投。**在没有数据的条件下做任何 SEO 或投放决策都是盲猜。**

建议：GA4 或更轻量的 Umami / Plausible（后者无需 Cookie 横幅，合规负担小）。

---

### P1-5 所有社交链接都是死链

`js/footer.js` 中 Facebook / Twitter / Instagram / LinkedIn / YouTube **五个链接全部是 `href="#"`**，`target="_blank"`。

点击后回到页面顶部，什么都不发生。对于一个正在建立品牌信任的制造企业，页脚挂着一排点不动的社媒图标，比不放更伤。

---

## 四、P2 — 中等问题（SEO / 可访问性 / 代码质量）

### P2-1 导航与页脚靠 JS 注入，HTML 里是空的

所有页面的结构是：

```html
<header></header>          <!-- 空 -->
...
<footer></footer>          <!-- 空 -->
```

真正的内容由 `header.js` / `footer.js` 在 `DOMContentLoaded` 后写入 `innerHTML`。

**后果**：
- 搜索引擎与社交爬虫拿到的初始 HTML 中**没有导航链接、没有页脚链接**（Google 虽能执行 JS，但这是额外的渲染预算与风险）
- 造成 **CLS（累积布局偏移）** —— 导航和页脚在 JS 执行后才"弹"出来
- JS 加载失败或被拦截时，**整站没有任何导航**，用户无法离开当前页

**建议**：改为静态 HTML 内联（可用构建步骤生成，避免手工同步 9 个文件），或至少加 `<noscript>` 兜底导航。

---

### P2-2 首页存在两套冲突的轮播脚本，其中一套每 5 秒抛异常

- `index.html` 内联脚本：操作 `.hero-slide` 与 `.indicator`
- `js/main.js` 第 19–84 行：另一套轮播，操作 `.hero-slide` 与 **`.slider-dot`**

而 HTML 中**根本不存在 `.slider-dot`**（用的是 `.indicator`）。于是 `main.js` 中：

```js
sliderDots[index].classList.add('active');   // sliderDots 为空 → undefined → TypeError
```

`sliderDots[index]` 恒为 `undefined`。该代码在 `setInterval` 中每 5 秒执行一次，**持续抛出 TypeError**。两套逻辑还会互相争夺 `active` class，导致轮播行为不稳定。

**建议**：删除 `main.js` 中的整套轮播逻辑，统一由内联脚本（或统一由 main.js）负责一套实现。

---

### P2-3 表单没有 `<label>`，可访问性不合格

`contact.html`：`<label>` 数量 = **0**，全部依赖 placeholder。

**后果**：屏幕阅读器无法正确识别字段；placeholder 在输入时消失导致用户忘记该填什么；自动填充（autofill）识别率下降 —— 这对「手机号 / WhatsApp」这种关键字段影响直接。

---

### P2-4 轮播与图标的可访问性问题

- 自动播放**无暂停机制**（鼠标悬停不暂停、无暂停按钮）
- **未处理 `prefers-reduced-motion`**
- 左右切换按钮 `<button class="prev-slide">` **无 `aria-label`**，屏幕阅读器只能读出空白按钮
- 指示器是 `<span>` 而非 `<button>`，**无法通过键盘聚焦**（虽有全局键盘监听，但语义仍然错误）
- 移动端 `.menu-toggle` 同样无 `aria-label` / `aria-expanded`

### P2-5 Font Awesome 用的是 2022 年的 beta 版

```html
.../font-awesome/6.0.0-beta3/css/all.min.css
```

- `6.0.0-beta3` 是 **beta 版本**，早已过时（现行为 6.7.x / 7.x）
- 加载**整套图标字体**（数百 KB）却只用了十几个图标
- 从第三方 CDN 同步加载，**阻塞首屏渲染**，且多一个单点故障
- `crossorigin` 已设置但**未配 `preconnect`**（仅 `about.html` 有）

**建议**：升级到稳定版，或改用内联 SVG 图标（可省掉整个字体请求）。

---

### P2-6 图片路径使用了反斜杠

```html
<img src="images/Yachts\60ft catamaran.jpg">        <!-- 应为 / -->
<img src="images/Snakehead\2300\snakehead 2300 small.png">
<img src="images/42FT\42FT.png">
```

`news.html` / `projects.html` 中大量存在（如 `images/38FT\Cat 38 ready.JPG` 出现 5 次）。

浏览器做了容错，**实测返回 200 可正常显示**，但这是 Windows 路径风格误入 HTML 的结果。一旦经过构建工具、CDN 规则或服务端严格解析，就有断图风险。建议全量替换为 `/`。

---

### P2-7 `logo narrow.png` 文件名含空格，在 JSON-LD 中是非法 URL

```json
"logo": "https://naiveryacht.com/images/logo narrow.png"
```

JSON-LD / og:image 中的 URL 含**未编码的裸空格**，属非法 URL。社交平台抓取器与结构化数据校验器会解析失败。

**建议**：重命名为 `logo-narrow.png`，或者至少编码为 `%20`。同时 `og:image` 应换成 **1200×630 的专用社交分享图**，而不是一个窄长 Logo。

---

### P2-8 仓库中残留垃圾文件

| 文件 | 问题 |
|---|---|
| `div` | **0 字节空文件**，疑似某次 shell 重定向 `> div` 的产物 |
| `footer-test.html` | 开发期测试页，`<title>Footer Test</title>`，**线上可访问且可被索引** |
| `.claude/settings.json` | 有未提交修改 |

---

### P2-9 缺少基础站点配套

- ❌ **无 `404.html`** —— 实测访问不存在路径返回 EdgeOne 默认 404 页，无品牌、无导航、无返回首页入口（也是流量浪费）
- ❌ **无 favicon / apple-touch-icon / manifest** —— 浏览器标签页显示默认空白图标
- ❌ **无安全响应头** —— 实测无 `Strict-Transport-Security`、`X-Content-Type-Options`、`Referrer-Policy`、`X-Frame-Options`、CSP

### P2-10 文案与内容一致性

- 导航写 **"ABOUT US"**，页脚写 **"MANUFACTURER"**，指向同一个页面 → 术语不统一
- `README.md` 仍写着 "Dealer application page"，与品牌重构后的定位不符
- 页脚营业时间写 **Monday - Friday**，而 `contact.html` 的 JSON-LD `dayOfWeek` 包含 **周一到周日** → 自相矛盾

### P2-11 语言切换器是假的

导航右上角有 `EN / 中文` 下拉，但：

```html
<li><a href="#" data-lang="en">English</a></li>
<li><a href="#" data-lang="zh">中文</a></li>
```

**没有任何 JS 处理 `data-lang`，没有 i18n 资源文件**。点击无任何反应。

对一个「迪拜设计中心 + 山东龙口船厂」的商业模式，中文版不是装饰，而是**直接服务中国供应链与合作方的沟通界面**。要么实现它，要么先撤掉这个假控件。

### P2-12 代码组织与页面体积

- **内联 `style="..."` 泛滥**：`news.html` **144 处**、`projects.html` **88 处** → 无法被浏览器缓存、无法统一维护
- **`news.html` 单页 3094 行 / 233 KB**，包含 70 张图 —— 应拆分为年份/主题分页，或改为列表页 + 详情页
- `projects.html` 1842 行 / 123 KB，同类问题
- **无构建流程**：无 `package.json`、无 `.github/workflows`，全部手写同步，9 个文件的 header/footer/SEO 靠人工保持一致，极易漂移
- **无 `defer` / `async`**：三个 JS 文件同步加载（虽在 body 末尾，仍建议 `defer`）

### P2-13 结构化数据可以更强

- `Organization` 的 `sameAs` 数组**只填了自己网站**，应加入社媒、行业平台（YachtWorld 等）档案
- 建议补充 `Product` / `Offer`（船型）、`BreadcrumbList`（面包屑已存在但未标记）、`ImageObject`
- `Product` 类结构化数据对船型详情页的富媒体摘要帮助明显

### P2-14 canonical 首页写法

```html
<link rel="canonical" href="https://naiveryacht.com/index.html">
```

首页规范地址应为 `https://www.navieryacht.com/`（无 `index.html`），避免 `index.html` 与 `/` 被视为两个 URL。

### P2-15 `meta keywords` 等过时标签

全站使用 `<meta name="keywords">` 与自定义 `<meta name="keywords-hashtags">`。Google 自 2009 年起已完全忽略 keywords。无害，但属无效体积与虚假优化感，清理即可。

---

## 五、优先级路线图

### 第 0 阶段 — 立刻（本周内，成本极低，止血）
| # | 动作 | 影响 |
|---|---|---|
| 1 | **接通询盘表单**（第三方服务或边缘函数），补成功/失败反馈 | 止血：挽回全部丢失线索 |
| 2 | 修根域 DNS + www/裸域 301 归一 | 恢复裸域访问 |
| 3 | canonical / sitemap / og:url 统一到主域 | 停止 SEO 自伤 |
| 4 | 静态资源缓存改为 `immutable, max-age=31536000` | 立竿见影的加载提速 |
| 5 | 删除 `div`、`footer-test.html`；补 `404.html` 与 favicon | 清理与基础体验 |
| 6 | 社交链接改为真实地址（或暂时撤下） | 品牌信任 |

### 第 1 阶段 — 两周内（性能与可观测）
| # | 动作 |
|---|---|
| 7 | 图片全量转 WebP + 生成多尺寸 + `srcset`（53 MB → 目标 < 8 MB） |
| 8 | 接入访问统计（GA4 或 Umami） |
| 9 | header/footer 改静态输出，消除 CLS 与 SEO 依赖 |
| 10 | 删除 `main.js` 中冲突的轮播逻辑（消除每 5 秒的 TypeError） |
| 11 | Font Awesome 升级或改内联 SVG + 补 `preconnect` |
| 12 | 反斜杠路径全量修正，`logo narrow.png` 重命名 |

### 第 2 阶段 — 一个月内（转化与合规）
| # | 动作 |
|---|---|
| 13 | 法务出具正式隐私政策 + 服务条款（含 PDPL/GDPR、Cookie、跨境传输、FZCO 主体信息） |
| 14 | 表单加 `<label>`、`aria-*`、蜜罐反垃圾；轮播加暂停与 `prefers-reduced-motion` |
| 15 | 实现真正的中英双语（或撤下假控件） |
| 16 | `news.html` / `projects.html` 分页重构，消除内联样式 |
| 17 | 补 `Product` / `BreadcrumbList` 结构化数据、1200×630 社交分享图 |
| 18 | 上安全响应头（HSTS / CSP / Referrer-Policy 等） |

### 第 3 阶段 — 持续优化
| # | 动作 |
|---|---|
| 19 | 引入简单构建流程（构建期生成 header/footer、压缩图片、HTML 最小化） |
| 20 | 确认 EdgeOne 是否可开启 HTTP/2 或 HTTP/3（当前实测为 HTTP/1.1） |
| 21 | 配置 Search Console / Bing 站长工具并提交 sitemap |
| 22 | 建立转化漏斗监测：访问 → 船型页 → 询盘表单 → 提交成功 |

---

## 六、做得好、无需改动的地方

审计中也确认了一批已经做到位的项，避免过度返工：

- ✅ 每个页面 **H1 唯一**（9/9 页面均为 1 个 H1）
- ✅ 所有 `<img>` **均有 `alt` 属性**（0 处缺失）
- ✅ 所有页面均有 **`lang="en"`**、description、Open Graph、Twitter Card
- ✅ **`robots.txt` 规范**，仅允许抓取并声明 sitemap
- ✅ **`sitemap.xml` 语法正确**（9 条 URL，含 `lastmod` / `changefreq` / `priority`）
- ✅ **Brotli 压缩正常工作**
- ✅ **HTTPS 证书有效**（www 域）
- ✅ 首屏图片已用 `loading="eager"`，其余 `lazy`
- ✅ 每页均有 **canonical**（虽然域名指错，但机制存在）
- ✅ 品牌重构后的文案定位清晰、一致（"Engineered in Dubai. Built in China. Delivered to the World."）
- ✅ 拥有 `geo.*` / `ICBM` 本地化标签与 `areaServed` 区域声明

---

## 七、一句话总结

**这个站点目前的问题不在「做得不够漂亮」，而在「关键时刻会漏」**：访客来了、看了、想询盘，填完表单点提交 —— 数据消失；搜索引擎来抓 —— canonical 指向一个 404 的地址。先修这两条，再谈性能与升级，投入产出比最高。
