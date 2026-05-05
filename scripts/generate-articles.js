#!/usr/bin/env node
/**
 * generate-articles.js
 * Reads provider/model data from Supabase and auto-generates original articles.
 * Should be run after sync-providers.js to use the latest data.
 *
 * Usage:
 *   SUPABASE_SERVICE_ROLE_KEY=xxx node scripts/generate-articles.js
 */

const SUPABASE_URL = 'https://ijqizaquvtpphqkysaoi.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const MONTH = new Date().toISOString().slice(0, 7); // e.g. "2026-05"
const MONTH_CN = `${new Date().getFullYear()}年${new Date().getMonth() + 1}月`;

if (!SERVICE_ROLE_KEY) {
  console.error('Error: SUPABASE_SERVICE_ROLE_KEY env var required');
  process.exit(1);
}

// ─── Supabase helpers ─────────────────────────────────────────

async function dbSelect(table, query = '') {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/${table}?${query}`,
    { headers: { apikey: SERVICE_ROLE_KEY, Authorization: `Bearer ${SERVICE_ROLE_KEY}` } }
  );
  return res.json();
}

async function dbUpsert(table, data, onConflict) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    headers: {
      apikey: SERVICE_ROLE_KEY,
      Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
      'Content-Type': 'application/json',
      Prefer: `resolution=merge-duplicates,return=minimal`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error(`  Upsert failed: ${err}`);
  }
  return res.ok;
}

// ─── Data loading ─────────────────────────────────────────────

async function loadData() {
  const providers = await dbSelect('providers', 'select=*,provider_models(*)');
  return providers.filter(p => p.status === 'active');
}

// ─── Article generators ──────────────────────────────────────

function generatePriceRanking(providers) {
  const modelGroups = {};
  for (const p of providers) {
    for (const m of (p.provider_models || [])) {
      if (m.price_per_1k_input == null) continue;
      if (!modelGroups[m.model_name]) modelGroups[m.model_name] = [];
      modelGroups[m.model_name].push({
        provider: p.name,
        url: p.url,
        tier: p.is_verified ? '推荐' : '中性',
        input: m.price_per_1k_input,
        output: m.price_per_1k_output,
        available: m.is_available,
      });
    }
  }

  const articles = [];
  const modelLabels = {
    'claude-sonnet-4-6': 'Claude Sonnet 4.6',
    'claude-opus-4-6': 'Claude Opus 4.6',
    'claude-opus-4-7': 'Claude Opus 4.7',
    'gpt-5.4': 'GPT-5.4',
    'gpt-5.5': 'GPT-5.5',
    'gpt-5.6': 'GPT-5.6',
    'gemini-3.1-pro': 'Gemini 3.1 Pro',
  };

  for (const [model, entries] of Object.entries(modelGroups)) {
    if (entries.length < 3) continue; // Skip models with too few providers
    const label = modelLabels[model] || model;
    entries.sort((a, b) => a.input - b.input);

    const top10 = entries.slice(0, 10);
    const officialInput = getOfficialPrice(model, 'input');
    const officialOutput = getOfficialPrice(model, 'output');

    let md = `# ${MONTH_CN} ${label} API 中转站价格排行\n\n`;
    md += `本文数据由 AI Club In 自动采集，更新于 ${MONTH_CN}。价格单位为人民币/百万Token。\n\n`;
    if (officialInput) {
      md += `> 官方价格参考：输入 ¥${officialInput}/百万Token，输出 ¥${officialOutput}/百万Token\n\n`;
    }
    md += `## 价格排行（从低到高）\n\n`;
    md += `| 排名 | 中转站 | 分类 | 输入价格 | 输出价格 | 相当于官方 |\n`;
    md += `|:---:|:---:|:---:|---:|---:|:---:|\n`;

    for (let i = 0; i < top10.length; i++) {
      const e = top10[i];
      const ratio = officialInput ? (e.input / officialInput * 100).toFixed(1) + '%' : '--';
      md += `| ${i + 1} | ${e.provider} | ${e.tier} | ¥${e.input} | ¥${e.output} | ${ratio} |\n`;
    }

    md += `\n## 价格分析\n\n`;
    const cheapest = top10[0];
    const mostExpensive = top10[top10.length - 1];
    md += `- 最便宜：**${cheapest.provider}**，输入 ¥${cheapest.input}/百万Token\n`;
    md += `- 最贵：**${mostExpensive.provider}**，输入 ¥${mostExpensive.input}/百万Token\n`;
    md += `- 价格差距：${(mostExpensive.input / cheapest.input).toFixed(1)} 倍\n`;
    md += `- 统计范围：共 ${entries.length} 家中转站提供 ${label} 模型\n\n`;
    md += `> ⚠️ 价格最低不代表最优。部分低价渠道可能使用逆向代理，质量和稳定性不如官方渠道。\n\n`;
    md += `*数据来源：AI Club In (aiclubin.com) 自动采集，仅供参考。*`;

    articles.push({
      slug: `${MONTH}-${model}-price-ranking`,
      title: `${MONTH_CN} ${label} API 中转站价格排行`,
      summary: `对比 ${entries.length} 家中转站的 ${label} 定价，最便宜 ¥${cheapest.input}/百万Token 起。`,
      content: md,
      category: 'report',
      is_published: true,
      published_at: new Date().toISOString(),
    });
  }

  return articles;
}

function generateRecommendedList(providers) {
  const recommended = providers.filter(p => p.is_verified);
  if (recommended.length === 0) return [];

  let md = `# ${MONTH_CN} 最值得推荐的 API 中转站\n\n`;
  md += `经过综合评估定价、稳定性、口碑等因素，以下中转站被 AI Club In 列为推荐级别。\n\n`;
  md += `## 推荐标准\n\n`;
  md += `1. **运营时间长** — 至少稳定运营 3 个月以上\n`;
  md += `2. **价格透明** — 定价清晰，有明确的账单记录\n`;
  md += `3. **质量可靠** — 经测试未发现模型掺水\n`;
  md += `4. **客服响应** — 有问题能及时得到解决\n\n`;
  md += `## 推荐列表\n\n`;

  for (const p of recommended) {
    const models = (p.provider_models || []).filter(m => m.price_per_1k_input != null);
    const cleanUrl = p.url.replace(/^https?:\/\//, '').replace(/\/$/, '');
    md += `### ${p.name}\n\n`;
    md += `- 网址：${cleanUrl}\n`;
    if (models.length > 0) {
      const cheapest = models.reduce((min, m) => m.price_per_1k_input < min.price_per_1k_input ? m : min);
      md += `- 起步价：¥${cheapest.price_per_1k_input}/百万Token（${cheapest.model_name}）\n`;
    }
    if (p.description) md += `- 简介：${p.description.substring(0, 100)}\n`;
    const notes = (p.notes || '').replace(/^\[.*?\]\s*/, '');
    if (notes) md += `- 特点：${notes}\n`;
    md += `\n`;
  }

  md += `## 使用建议\n\n`;
  md += `1. **不要大额充值** — 中转站行业不稳定，用多少充多少\n`;
  md += `2. **先试用再购买** — 大部分推荐站点都有新用户试用额度\n`;
  md += `3. **关注价格变动** — 中转站价格变化频繁，定期关注最新排行\n`;
  md += `4. **多站备份** — 不要只依赖一家，建议同时备 2-3 家\n\n`;
  md += `*数据来源：AI Club In (aiclubin.com) 综合评估，仅供参考。*`;

  return [{
    slug: `${MONTH}-recommended-providers`,
    title: `${MONTH_CN} 最值得推荐的 API 中转站`,
    summary: `精选 ${recommended.length} 家优质中转站，综合评估价格、稳定性和服务质量。`,
    content: md,
    category: 'review',
    is_published: true,
    published_at: new Date().toISOString(),
  }];
}

function generateModelComparison(providers) {
  const models = ['claude-sonnet-4-6', 'claude-opus-4-6', 'gpt-5.4', 'gpt-5.5'];
  const modelLabels = {
    'claude-sonnet-4-6': 'Sonnet 4.6',
    'claude-opus-4-6': 'Opus 4.6',
    'claude-opus-4-7': 'Opus 4.7',
    'gpt-5.4': 'GPT-5.4',
    'gpt-5.5': 'GPT-5.5',
    'gpt-5.6': 'GPT-5.6',
    'gemini-3.1-pro': 'Gemini 3.1 Pro',
  };

  // Find average price per model
  const avgPrices = {};
  for (const p of providers) {
    for (const m of (p.provider_models || [])) {
      if (m.price_per_1k_input == null) continue;
      if (!avgPrices[m.model_name]) avgPrices[m.model_name] = { total: 0, count: 0, totalOut: 0 };
      avgPrices[m.model_name].total += m.price_per_1k_input;
      avgPrices[m.model_name].totalOut += m.price_per_1k_output;
      avgPrices[m.model_name].count++;
    }
  }

  let md = `# API 大模型中转站价格全对比（${MONTH_CN}）\n\n`;
  md += `不同大模型的中转站价格差异很大。本文汇总各主流模型的中转站平均价格，帮你选择最具性价比的方案。\n\n`;
  md += `## 各模型平均价格\n\n`;
  md += `| 模型 | 提供商数量 | 平均输入价 | 平均输出价 | 官方参考价 | 中转站折扣 |\n`;
  md += `|:---|:---:|---:|---:|---:|:---:|\n`;

  for (const [model, stats] of Object.entries(avgPrices).sort((a, b) => (a[1].total / a[1].count) - (b[1].total / b[1].count))) {
    const avgIn = (stats.total / stats.count).toFixed(1);
    const avgOut = (stats.totalOut / stats.count).toFixed(1);
    const offIn = getOfficialPrice(model, 'input');
    const offOut = getOfficialPrice(model, 'output');
    const discount = offIn ? ((stats.total / stats.count) / offIn * 100).toFixed(1) + '%' : '--';
    const offLabel = offIn ? `¥${offIn}/¥${offOut}` : '--';
    md += `| ${modelLabels[model] || model} | ${stats.count} | ¥${avgIn} | ¥${avgOut} | ${offLabel} | ${discount} |\n`;
  }

  md += `\n## 省钱建议\n\n`;
  const sonnetAvg = avgPrices['claude-sonnet-4-6'];
  const opusAvg = avgPrices['claude-opus-4-6'];
  if (sonnetAvg && opusAvg) {
    const ratio = ((opusAvg.total / opusAvg.count) / (sonnetAvg.total / sonnetAvg.count)).toFixed(1);
    md += `- **Opus 平均比 Sonnet 贵 ${ratio} 倍**。如果不需要最强性能，Sonnet 性价比更高\n`;
  }
  md += `- **GPT 系列普遍比 Claude 便宜**，适合预算有限的用户\n`;
  md += `- **推荐站点虽然单价稍高，但质量更可靠**，实际使用成本可能更低（不掺水）\n`;
  md += `- 关注各站的缓存折扣，编程场景缓存命中率通常 50%+\n\n`;
  md += `*数据来源：AI Club In (aiclubin.com) 自动采集，仅供参考。*`;

  return [{
    slug: `${MONTH}-model-comparison`,
    title: `${MONTH_CN} API 大模型中转站价格全对比`,
    summary: `对比 ${Object.keys(avgPrices).length} 种主流模型的中转站平均价格，分析最具性价比的选择。`,
    content: md,
    category: 'report',
    is_published: true,
    published_at: new Date().toISOString(),
  }];
}

function generateBeginnerGuide() {
  const md = `# API 中转站选购指南：新手必读

如果你刚接触 AI API 中转站，这篇文章帮你快速了解基本概念和避坑要点。

## 什么是 API 中转站？

API 中转站（也叫 API 代理、API 反代）是一个中间服务商，让你无需直接注册 OpenAI、Anthropic 等海外平台，就能通过统一的 API 接口调用各种大模型。

**优势：**
- 不需要海外信用卡
- 人民币结算，价格通常比官方低
- 一个 API Key 调用多个模型

**风险：**
- 部分中转站会用低价模型冒充高价模型（掺水）
- 稳定性不如官方，可能随时跑路
- 数据经过第三方服务器

## 选购 Checklist

### 1. 价格不是越低越好

价格异常便宜（比如官方 1 折以下）的渠道，大概率是：
- 使用逆向代理（从 Cursor/Kiro 等渠道套壳）
- 用低价模型（如 GLM）冒充高价模型（如 Claude）
- 账号随时可能被封，服务不稳定

合理的价格区间是官方的 **0.3-0.6 折**（逆向渠道）或 **0.5-0.8 折**（官方渠道）。

### 2. 看运营时间

优先选择运营 6 个月以上的站点。新站虽然可能有优惠活动，但跑路风险也更高。

### 3. 试用再购买

大部分中转站都有试用额度（1-10 元不等）。**先试用，确认质量和速度后再充值。**

### 4. 不要大额充值

这是最重要的建议。中转站行业没有监管，站长跑路的案例屡见不鲜。建议：
- 每次充值不超过 100 元
- 用多少充多少
- 不要被"充 500 送 100"之类的优惠诱惑

### 5. 关注 Token 计数

有些中转站会在 Token 计数上做手脚：
- 虚报 Token 用量，实际消耗比显示的多
- 不显示缓存命中，缓存部分也按原价收费
- 计费粒度和官方不一致

选择有**清晰账单**和**缓存命中记录**的站点。

## 常见坑

### 模型掺水

最常见的坑。表现为：
- 声称是 Claude Opus，实际返回的是 Claude Haiku 甚至 GLM
- 响应质量明显低于预期
- 编程时错误率异常高

**检测方法：** 使用本站的 [六维检测工具](/detect.html) 可以自动识别模型掺水。

### 缓存陷阱

编程场景（如 Claude Code）会大量使用 Prompt Caching。部分中转站：
- 缓存按原价收费（官方是半价或更低）
- 不显示缓存命中记录
- 实际费用比预期高很多

**建议：** 选择缓存折扣透明（0.1-0.2 倍）的站点。

### 跑路风险

中转站突然关站、无法提现的情况时有发生。

**防范：**
- 分散在 2-3 家站点
- 保持小额余额
- 关注社区动态（如 linux.do 论坛）

## 推荐阅读

- [每月推荐中转站清单](article.html?slug=${MONTH}-recommended-providers)
- [各模型价格排行](article.html?slug=${MONTH}-claude-sonnet-4-6-price-ranking)

---

*本文由 AI Club In 编写，内容仅供参考。市场变化较快，请以实际情况为准。*`;

  return [{
    slug: 'beginner-guide',
    title: 'API 中转站选购指南：新手必读',
    summary: '新手入门必读！了解什么是 API 中转站、如何选购、常见坑和避坑技巧。',
    content: md,
    category: 'guide',
    is_published: true,
    published_at: new Date().toISOString(),
  }];
}

// ─── Helpers ──────────────────────────────────────────────────

function getOfficialPrice(model, direction) {
  // Official prices in CNY per 1M tokens (approximate)
  const prices = {
    'claude-sonnet-4-6': { input: 21, output: 105 },
    'claude-opus-4-6': { input: 105, output: 525 },
    'claude-opus-4-7': { input: 105, output: 525 },
    'gpt-5.4': { input: 7, output: 42 },
    'gpt-5.5': { input: 7, output: 42 },
    'gpt-5.6': { input: 7, output: 42 },
    'gemini-3.1-pro': { input: 35, output: 105 },
  };
  return prices[model]?.[direction] || null;
}

// ─── Main ─────────────────────────────────────────────────────

async function main() {
  console.log('Loading provider data...');
  const providers = await loadData();
  console.log(`Loaded ${providers.length} active providers\n`);

  // Delete old auto-generated articles for current month
  const slugs = [
    `${MONTH}-recommended-providers`,
    `${MONTH}-model-comparison`,
    `${MONTH}-claude-sonnet-4-6-price-ranking`,
    `${MONTH}-claude-opus-4-6-price-ranking`,
    `${MONTH}-claude-opus-4-7-price-ranking`,
    `${MONTH}-gpt-5.4-price-ranking`,
    `${MONTH}-gpt-5.5-price-ranking`,
    `${MONTH}-gpt-5.6-price-ranking`,
    `${MONTH}-gemini-3.1-pro-price-ranking`,
  ];

  for (const slug of slugs) {
    await fetch(
      `${SUPABASE_URL}/rest/v1/articles?slug=eq.${slug}`,
      {
        method: 'DELETE',
        headers: {
          apikey: SERVICE_ROLE_KEY,
          Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
          Prefer: 'return=minimal',
        },
      }
    );
  }

  const allArticles = [];

  // 1. Price rankings per model
  console.log('Generating price rankings...');
  const rankings = generatePriceRanking(providers);
  allArticles.push(...rankings);
  console.log(`  Generated ${rankings.length} ranking articles`);

  // 2. Recommended providers list
  console.log('Generating recommended list...');
  const recommended = generateRecommendedList(providers);
  allArticles.push(...recommended);
  console.log(`  Generated ${recommended.length} recommendation articles`);

  // 3. Model comparison
  console.log('Generating model comparison...');
  const comparison = generateModelComparison(providers);
  allArticles.push(...comparison);
  console.log(`  Generated ${comparison.length} comparison articles`);

  // 4. Beginner guide (only insert if not exists)
  console.log('Generating beginner guide...');
  const existing = await dbSelect('articles', 'slug=eq.beginner-guide&select=id');
  if (!existing || existing.length === 0) {
    const guide = generateBeginnerGuide();
    allArticles.push(...guide);
    console.log(`  Generated beginner guide`);
  } else {
    console.log(`  Beginner guide already exists, skipping`);
  }

  // Insert all articles
  console.log(`\nInserting ${allArticles.length} articles...`);
  for (const article of allArticles) {
    // Use upsert with slug as conflict key
    const ok = await dbUpsert('articles', {
      ...article,
      view_count: 0,
    }, 'slug');
    console.log(`  ${ok ? '✓' : '✗'} ${article.slug}`);
  }

  console.log(`\nDone! Generated ${allArticles.length} articles.`);
}

main().catch(console.error);
