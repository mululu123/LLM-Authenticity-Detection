# Model Fingerprinting System

大模型脱壳鉴定法 - 识别 API 中转平台是否伪装模型

## 安装

```bash
pip install openai pyyaml
```

## 快速开始

```bash
# 测试 OpenAI 官方 API
python scripts/fingerprint_test.py --api-key YOUR_KEY --model gpt-4

# 测试第三方 API 端点
python scripts/fingerprint_test.py \
    --endpoint https://api.example.com/v1 \
    --api-key YOUR_KEY \
    --model gpt-4 \
    --family openai
```

## 检测层级

| 层级 | 检测内容 | 方法 |
|------|---------|------|
| 第一层 | API 与协议层 | Tokenizer 计费、流式传输特征 |
| 第二层 | 认知与提示词层 | 翻译溯源、Fallback、知识截断 |
| 第三层 | 对齐与审查层 | 道德拒绝指纹、区域审查 |
| 第四层 | 逻辑与数学层 | 弱智吧测试、浮点数陷阱、格式遵从 |

## 输出示例

```
==============================================================
  模型指纹检测 - 大模型照妖镜
  声称模型: gpt-4
==============================================================

📡 第一层: API 与协议层侦测...
   ✓ Tokenizer 计费检测
   ✓ 流式传输特征检测
...

# 模型指纹检测报告

| 项目 | 结果 |
|------|------|
| 结论 | ✅ 真实可信 |
| 通过率 | 85% |
| 可疑分数 | 0.15 |
```

## 配置文件

参考 `config.yaml` 进行详细配置。

## 退出码

- `0`: 真实可信
- `1`: 存在可疑
- `2`: 确认为伪装

## 许可证

MIT
