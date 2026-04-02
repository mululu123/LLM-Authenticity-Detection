"""
第二层：认知与提示词层探测
- 语言翻译反向溯源
- 空白与沉默法则 (Fallback 测试)
- 知识截断测试
"""

from typing import Any
from .base import BaseDetector, DetectionResult, RiskLevel


class CognitiveLayerDetector(BaseDetector):
    """认知与提示词层检测器"""

    LAYER_NAME = "认知与提示词层"

    # 各模型的 Fallback 响应特征
    FALLBACK_SIGNATURES = {
        "openai": ["你好", "有什么我可以帮", "How can I help"],
        "claude": ["blank message", "didn't include a question", "看起来你没有"],
        "qwen": ["请问", "您需要"],
        "llama": [],
    }

    # 训练者关键词
    PROVIDER_KEYWORDS = {
        "anthropic": ["anthropic", "claude", "constitutional ai"],
        "openai": ["openai", "gpt", "chatgpt"],
        "alibaba": ["阿里", "通义", "qwen", "千问"],
        "zhipu": ["智谱", "chatglm", "glm"],
        "deepseek": ["deepseek", "深度求索"],
        "google": ["google", "bard", "gemini"],
    }

    def run_all_tests(self) -> list[DetectionResult]:
        """运行所有认知层测试"""
        self.results = []

        # 测试 1: 翻译反向溯源
        self.results.append(self._test_translation_traceback())

        # 测试 2: Fallback 响应
        self.results.append(self._test_fallback_response())

        # 测试 3: 知识截断
        self.results.append(self._test_knowledge_cutoff())

        return self.results

    def _test_translation_traceback(self) -> DetectionResult:
        """语言翻译反向溯源测试"""
        prompt = """请将以下句子翻译成文言文，然后再翻译回现代白话文：
"I am a large language model trained by OpenAI."

请不要解释，直接输出最终的白话文结果。"""

        response, metadata = self._call_api(prompt, max_tokens=200)

        response_lower = response.lower()

        # 检测响应中是否泄露了真实训练者信息
        detected_providers = []
        for provider, keywords in self.PROVIDER_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in response_lower:
                    detected_providers.append(provider)
                    break

        # 如果声称是 OpenAI 但泄露了其他训练者信息
        score = 0.0
        passed = True
        risk = RiskLevel.SAFE

        # OpenAI 模型应该返回 OpenAI 相关内容
        # 如果返回了 Anthropic/Claude 等，说明是套壳
        suspicious_providers = [p for p in detected_providers if p not in ["openai"]]

        if suspicious_providers:
            score = 0.8
            passed = False
            risk = RiskLevel.FAKE

        return DetectionResult(
            detector_name="CognitiveLayerDetector",
            layer=self.LAYER_NAME,
            test_name="翻译反向溯源",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "detected_providers": detected_providers,
                "suspicious": suspicious_providers,
            },
            raw_response=response,
        )

    def _test_fallback_response(self) -> DetectionResult:
        """空白输入 Fallback 测试"""
        # 测试空格输入
        response, metadata = self._call_api(" ", max_tokens=100)

        response_lower = response.lower().strip()

        # 检测 Fallback 响应特征
        matched_signatures = []
        for provider, patterns in self.FALLBACK_SIGNATURES.items():
            for pattern in patterns:
                if pattern.lower() in response_lower:
                    matched_signatures.append(provider)
                    break

        # 评估
        if not response_lower or len(response_lower) < 5:
            # 空响应或极短响应
            score = 0.3
            passed = True
            risk = RiskLevel.SAFE
        elif "openai" in matched_signatures:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        elif matched_signatures:
            # 匹配到其他模型的 Fallback 特征
            score = 0.7
            passed = False
            risk = RiskLevel.SUSPICIOUS
        else:
            # 未知特征
            score = 0.4
            passed = True
            risk = RiskLevel.SUSPICIOUS

        return DetectionResult(
            detector_name="CognitiveLayerDetector",
            layer=self.LAYER_NAME,
            test_name="Fallback响应测试",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "response_length": len(response),
                "matched_signatures": matched_signatures,
            },
            raw_response=response[:200] if response else None,
        )

    def _test_knowledge_cutoff(self) -> DetectionResult:
        """知识截断测试"""
        prompt = """请告诉我 2024 年 2 月份发生了什么重大的国际新闻？
请根据你的预训练记忆回答，不要使用网络搜索工具。
只需列出 2-3 条即可。"""

        response, metadata = self._call_api(prompt, max_tokens=300)

        response_lower = response.lower()

        # 检查是否知道 2024 年 2 月的事件
        # 关键事件：普京批评纳瓦利内死亡、莫斯科音乐会袭击（2024年3月，不应知道）
        knows_2024 = any(kw in response_lower for kw in [
            "2024", "二月", "february", "纳瓦利内", "navalny",
        ])

        # 检查是否声称知识截止
        claims_cutoff = any(kw in response_lower for kw in [
            "截止", "无法", "不知道", "知识库", "训练数据", "cutoff",
            "cannot", "don't know", "not aware",
        ])

        # 评估
        if knows_2024:
            # 知道 2024 年事件，符合 GPT-4o/Claude 3.5 等新模型
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        elif claims_cutoff and not knows_2024:
            # 声称不知道，可能是旧模型
            score = 0.6
            passed = False
            risk = RiskLevel.SUSPICIOUS
        else:
            score = 0.3
            passed = True
            risk = RiskLevel.SAFE

        return DetectionResult(
            detector_name="CognitiveLayerDetector",
            layer=self.LAYER_NAME,
            test_name="知识截断测试",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "knows_2024_events": knows_2024,
                "claims_cutoff": claims_cutoff,
            },
            raw_response=response[:300] if response else None,
        )
