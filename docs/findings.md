# Findings: API 中转站比价平台

## 市场调研结论

### 需求验证
- **学术论文**: "Real Money, Fake Models" (arxiv 2603.01919) 审计 17 个 shadow API，45.83% 指纹验证失败
- **Reddit**: 持续有用户投诉 API 代理欺诈，模型降级是主要痛点
- **V2EX/知乎**: 中文社区同样大量投诉，New API 作者曾被指控欺诈
- **结论**: 需求真实且强烈

### 竞品分析
| 平台 | 做了什么 | 缺什么 |
|------|----------|--------|
| LMSYS Chatbot Arena | 官方模型评测排名 | 不涉及中转站 |
| Artificial Analysis | 模型性能/价格对比 | 不涉及中转站 |
| 各类"中转站推荐"文章 | 手写评测，SEO 引流 | 不系统，无数据支撑 |
| **我们的差异化** | 自动检测 + 风险评级 + 比价 | — |

### 中转站数据获取
- 大部分基于 New API / One API 开源系统
- `/api/models` 接口返回模型列表和倍率（JSON 格式统一）
- V2EX/GitHub/LINUXdo 是新站曝光的主要渠道
- 头部 30 家覆盖 80% 用户需求

### 变现路径
1. 广告收入（流量上来后）
2. 中转站付费收录/推荐位
3. 联盟佣金（引导用户注册中转站）

---

## 技术发现

### 现有可复用资产
- 五维探针检测引擎（src/probes/）
- Supabase 集成（数据库 + 前端 SDK）
- Vercel 部署配置
- 探针配置动态加载（从 Supabase probes 表）

### 需要新建
- providers / provider_models / provider_ratings 表
- 首页排行榜 UI
- 详情页 UI
- 文章系统 UI
- 自动化评测脚本
