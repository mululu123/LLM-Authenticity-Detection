# Task Plan: API 中转站比价 + 风险评级平台 (aiclubin.com)

## Goal
将现有的 LLM 检测工具改造成 API 中转站比价评级平台，核心功能：比价、风险评级、用户评价、内容引流。
技术栈：纯静态 HTML/JS + Supabase 后端 + Vercel 部署。

---

## Phase 1: 数据层 — Supabase 表结构设计与创建
**Status:** `pending`
**Priority:** High

### 目标
设计并创建支撑平台运行的数据库表。

### 1.1 设计表结构
- [ ] `providers` 表 — 中转站基本信息（名称、URL、logo、描述、状态）
- [ ] `provider_models` 表 — 各站支持的模型列表和倍率定价
- [ ] `provider_ratings` 表 — 用户评价（评分、评论、使用体验）
- [ ] `detection_results` 表 — 自动检测结果（复用现有探针，存历史记录）
- [ ] `articles` 表 — AI 生成的评测文章/市场报告

### 1.2 种子数据
- [ ] 手动录入 20 家主流中转站基础信息
- [ ] 录入各站常见模型定价倍率

### 产出
- `supabase_schema_v2.sql` — 新表结构
- Supabase 数据库中表创建完成
- 种子数据导入完成

---

## Phase 2: 前端首页 — 比价排行榜
**Status:** `pending`
**Priority:** High

### 目标
替换现有检测工具页面，搭建平台首页。用户打开 aiclubin.com 第一眼看到的是中转站排行和比价。

### 2.1 页面结构
- [ ] 顶部导航栏（Logo + 搜索 + 分类 Tab）
- [ ] Hero 区域（标题 + 副标题 + CTA 按钮）
- [ ] 排行榜主体（表格/卡片列表，支持排序筛选）
- [ ] 侧边栏（分类筛选、热门标签、最新文章入口）
- [ ] 底部 Footer（关于我们、联系方式、免责声明）

### 2.2 排行榜数据展示
每条中转站记录展示：
- 站名 + URL + Logo
- 风险评级徽章（A/B/C/D，颜色区分）
- 支持模型数量
- 平均倍率（与官方价格对比）
- 用户评分（星级）
- 最近检测时间
- "查看详情"按钮

### 2.3 交互功能
- [ ] 按风险等级筛选
- [ ] 按价格排序（倍率从低到高）
- [ ] 按模型筛选（哪些站支持 GPT-4o/Claude-3.5 等）
- [ ] 搜索站名

### 产出
- `visualizer/index.html` 全新改版
- 从 Supabase 实时加载 provider 数据

---

## Phase 3: 详情页 — 单站深度分析
**Status:** `pending`
**Priority:** Medium

### 目标
点击某中转站后进入详情页，展示完整的检测报告和用户评价。

### 3.1 详情页内容
- [ ] 基本信息（URL、运营时间、支持模型列表）
- [ ] 定价对比表（各模型倍率 vs 官方价格）
- [ ] 五维探针检测报告（复用现有检测逻辑）
- [ ] 历史检测趋势图（风险等级变化）
- [ ] 用户评价列表（评分 + 评论）
- [ ] 提交评价表单

### 3.2 检测功能保留
- [ ] "立即检测"按钮 — 输入 API URL + Key 执行五维探针
- [ ] 检测结果存入 detection_results 表
- [ ] 结果更新该站的风险评级

### 产出
- `visualizer/detail.html` 详情页

---

## Phase 4: 内容系统 — AI 自动生成文章
**Status:** `pending`
**Priority:** Medium

### 目标
AI 自动生成评测内容，用于 SEO 引流。

### 4.1 文章类型
- [ ] "新站速评" — 新收录站点时自动生成
- [ ] "每周市场报告" — 汇总本周价格变动、新站上线
- [ ] "深度评测" — 对热门站的完整五维分析报告

### 4.2 自动化流程
- [ ] 定时任务触发检测
- [ ] 检测结果喂给 LLM 生成文章
- [ ] 存入 articles 表，前端自动展示

### 产出
- `scripts/auto_review.py` — 自动评测生成脚本
- 文章列表页和详情页

---

## Phase 5: 用户系统 & 冷启动
**Status:** `complete`
**Priority:** Low

### 5.1 用户功能
- [x] 匿名评价（无需登录，限制频率）
- [x] 提交新站点（用户建议收录）

### 5.2 冷启动内容
- [x] 录入 20 家主流中转站 + 2 家实测站点（Code Fox AI、GPTProto）
- [x] 为每家生成初始评测（62 条 seed reviews）
- [x] 模型定价数据（54 条 provider_models）
- [x] 写 3-5 篇 SEO 文章（自动化周报已生成多篇）
- [x] GPTProto 实测：6 条 detection_results（3 authentic + 3 unavailable）
- [x] Code Fox AI 录入（9 模型，API key 无余额未深入测试）

---

## 技术架构

```
aiclubin.com (Vercel)
├── visualizer/
│   ├── index.html      # 首页：排行榜 + 比价
│   ├── detail.html     # 详情页：单站分析
│   ├── article.html    # 文章页
│   └── detect.html     # 检测工具（原功能保留）
└── scripts/
    └── auto_review.py  # 自动评测脚本

Supabase (后端)
├── providers           # 中转站信息
├── provider_models     # 模型定价
├── provider_ratings    # 用户评价
├── detection_results   # 检测历史
├── probes              # 探针配置（已有）
└── articles            # 评测文章
```

---

## 当前进度

| Phase | 状态 |
|-------|------|
| Phase 1: 数据层 | `complete` ✅ |
| Phase 2: 首页 | `complete` ✅ |
| Phase 3: 详情页 | `complete` ✅ |
| Phase 4: 内容系统 | `complete` ✅ |
| Phase 5: 用户系统 | `complete` ✅ |

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |
