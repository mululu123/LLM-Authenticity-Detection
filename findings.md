# Findings: 套壳场景分析

## 核心套壳模式

### 模式1: DeepSeek 套壳 (最常见)
```
声称: GPT-4o / Claude-3.5 / GLM-5
实际: DeepSeek-V3 / DeepSeek-R1 / DeepSeek-Lite
```

**检测特征:**
- `reasoning_content` 字段 (R1 特有)
- DeepSeek Token 特征
- 中性拒绝风格 (非 Claude 说教式)

### 模式2: 低配冒充高配
```
声称: GPT-4 / Claude-3.5
实际: GPT-3.5 / Claude-3-Haiku / DeepSeek-Lite
```

**检测特征:**
- 逻辑题错误率
- 数学运算准确度
- 指令复杂度遵从

### 模式3: 开源冒充商业
```
声称: GPT-4o
实际: Qwen / Llama / GLM
```

**检测特征:**
- Tokenizer 计费差异
- 身份信息泄露
- 安全对齐风格

---

## 模型性能分级

| 等级 | 代表模型 | 特征 |
|------|----------|------|
| **S级** | GPT-4o, Claude-3.5-Sonnet | 逻辑完美, 格式严格, 复杂指令100%遵从 |
| **A级** | GLM-4, DeepSeek-V3, Qwen-Max | 逻辑优秀, 格式良好, 复杂指令90%+ |
| **B级** | DeepSeek-Lite, Qwen-Plus | 逻辑偶尔出错, 格式一般 |
| **C级** | Llama-7B, 小参数模型 | 逻辑经常出错, 格式污染 |

---

## 关键检测探针

### 1. 性能分级测试题
- **逻辑回旋**: "爸妈结婚没邀请我" - S/A级秒答, B/C级编造
- **浮点陷阱**: "9.11 vs 9.9" - 旧模型/小模型易错
- **幻觉回旋**: "第一个在月球吃热狗的人" - S级指出前提错误

### 2. 身份泄露探测
- 翻译倒影: "I am trained by OpenAI" → 中 → 英
- 空白 Fallback: 不同模型有独特兜底响应

### 3. 格式污染检测
- 极限 JSON: 要求纯净输出
- Markdown 检测: 是否夹带 ```json

### 4. DeepSeek 专项
- `reasoning_content` 字段检测
- 思维链格式特征
- 响应延迟模式

---

## 判定逻辑

```
输入: 声称模型 X
输出: {
  真实模型: Y (概率: Z%)
  性能等级: S/A/B/C
  诈骗指数: 0-100
  Agent兼容: A-F
}
```

### 诈骗指数计算
- Token 不匹配: +30%
- 身份泄露矛盾: +40%
- 性能等级不达标: +20%
- 格式污染: +10%