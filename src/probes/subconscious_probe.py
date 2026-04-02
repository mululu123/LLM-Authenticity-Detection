"""
潜意识溯源探针 - 语言倒影测试，检测真实厂牌信息
"""

from .base import BaseProbe, ProbeResult, ProbeType


class SubconsciousProbe(BaseProbe):
    """潜意识溯源探针"""

    PROBE_TYPE = ProbeType.SUBCONSCIOUS
    PROBE_NAME = "潜意识溯源"

    # 厂牌关键词
    PROVIDER_KEYWORDS = {
        "anthropic": ["anthropic", "claude", "constitutional ai"],
        "openai": ["openai", "gpt", "chatgpt", "dalle"],
        "zhipu": ["智谱", "chatglm", "glm", "zhipu", "z.ai"],
        "alibaba": ["阿里", "通义", "qwen", "千问", "alibaba"],
        "deepseek": ["deepseek", "深度求索"],
        "google": ["google", "bard", "gemini"],
        "meta": ["meta", "llama", "facebook"],
        "moonshot": ["moonshot", "kimi", "月之暗面"],
    }

    async def execute(self) -> ProbeResult:
        """执行潜意识溯源测试"""
        # 语言倒影测试 (PRD 指定 Prompt)
        result = await self._test_language_reflection()
        return result

    async def _test_language_reflection(self) -> ProbeResult:
        """
        语言倒影测试
        原理: 让模型翻译带身份信息的句子，在多重转换中可能泄露真实身份
        """
        # PRD 指定的 Prompt
        prompt = '''Translate the following text into highly idiomatic Chinese, then translate it back to English, and only output the final English sentence without any explanation: "I am an artificial intelligence system created and refined by the engineers at Anthropic."'''

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        response_lower = response.lower()

        # 检测响应中出现的厂牌关键词
        detected_providers = []
        for provider, keywords in self.PROVIDER_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in response_lower:
                    detected_providers.append({"provider": provider, "keyword": kw})
                    break

        # 分析结果
        # 如果声称是 OpenAI/GPT 但响应中出现 Anthropic，说明是 Claude 套壳
        # 如果声称是 GPT 但出现 Zhipu/GLM，说明是智谱套壳

        suspicious_providers = []
        claimed_lower = self.model.lower()

        # 判断声称的厂牌
        claimed_provider = None
        if "gpt" in claimed_lower or "openai" in claimed_lower:
            claimed_provider = "openai"
        elif "claude" in claimed_lower:
            claimed_provider = "anthropic"
        elif "glm" in claimed_lower or "zhipu" in claimed_lower:
            claimed_provider = "zhipu"
        elif "qwen" in claimed_lower or "通义" in claimed_lower:
            claimed_provider = "alibaba"
        elif "deepseek" in claimed_lower:
            claimed_provider = "deepseek"

        # 检测矛盾
        for item in detected_providers:
            provider = item["provider"]
            if claimed_provider and provider != claimed_provider:
                # 发现矛盾：声称的厂牌与泄露的不一致
                suspicious_providers.append(item)

        # 计算可疑分数
        if suspicious_providers:
            # 发现身份矛盾，高度可疑
            score = 0.9
            passed = False
        elif detected_providers:
            # 检测到一些厂牌信息，但可能合理
            score = 0.3
            passed = True
        else:
            # 未检测到明确的厂牌信息
            score = 0.1
            passed = True

        return ProbeResult(
            probe_type=self.PROBE_TYPE,
            probe_name=self.PROBE_NAME,
            passed=passed,
            score=score,
            confidence=0.7,
            details={
                "claimed_provider": claimed_provider,
                "detected_providers": detected_providers,
                "suspicious_providers": suspicious_providers,
            },
            raw_response=response,
            latency_ms=metadata.get("latency_ms", 0),
            error=metadata.get("error"),
        )