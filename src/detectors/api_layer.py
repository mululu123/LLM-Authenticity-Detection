"""
第一层：API 与协议层侦测
- Tokenizer 计费侦测法
- 流式传输切片特征
"""

from typing import Any
from .base import BaseDetector, DetectionResult, RiskLevel


class APILayerDetector(BaseDetector):
    """API 与协议层检测器"""

    LAYER_NAME = "API与协议层"

    # 各模型家族的 Token 特征（同一段测试文本的预期 Token 数）
    TOKEN_SIGNATURES = {
        "openai_tiktoken": {"min": 20, "max": 35},   # OpenAI tiktoken 特征
        "qwen": {"min": 10, "max": 20},              # 千问中文压缩率高
        "llama": {"min": 40, "max": 60},             # Llama 中文支持弱
        "claude": {"min": 18, "max": 30},            # Claude
    }

    def __init__(self, client: Any, model_name: str, claimed_family: str = "openai"):
        super().__init__(client, model_name)
        self.claimed_family = claimed_family

    def run_all_tests(self) -> list[DetectionResult]:
        """运行所有 API 层测试"""
        self.results = []

        # 测试 1: Tokenizer 计费检测
        self.results.append(self._test_tokenizer())

        # 测试 2: 流式传输特征
        self.results.append(self._test_stream_characteristics())

        return self.results

    def _test_tokenizer(self) -> DetectionResult:
        """Tokenizer 计费侦测法"""
        test_text = "你好世界Hello_World_2024!@# 魑魅魍魉 1234567890"

        response, metadata = self._call_api(
            f"请重复以下内容，不要添加任何其他文字：{test_text}",
            max_tokens=100
        )

        prompt_tokens = metadata.get("prompt_tokens", 0)

        # 检查 Token 数是否符合声称的模型家族
        expected = self.TOKEN_SIGNATURES.get(self.claimed_family, {})
        expected_min = expected.get("min", 0)
        expected_max = expected.get("max", 999)

        in_range = expected_min <= prompt_tokens <= expected_max

        # 计算可疑分数
        if in_range:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        else:
            # 计算偏离程度
            deviation = 0
            if prompt_tokens < expected_min:
                deviation = expected_min - prompt_tokens
            else:
                deviation = prompt_tokens - expected_max
            score = min(1.0, deviation / 20)  # 每 20 tokens 偏离增加 0.1 分
            passed = False
            risk = RiskLevel.SUSPICIOUS if score < 0.5 else RiskLevel.FAKE

        return DetectionResult(
            detector_name="APILayerDetector",
            layer=self.LAYER_NAME,
            test_name="Tokenizer计费检测",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "prompt_tokens": prompt_tokens,
                "expected_range": f"{expected_min}-{expected_max}",
                "claimed_family": self.claimed_family,
                "response_length": len(response),
            },
            raw_response=response[:200] if response else None,
        )

    def _test_stream_characteristics(self) -> DetectionResult:
        """流式传输切片特征检测"""
        response, metadata = self._call_api(
            "请用50个字介绍一下人工智能。",
            max_tokens=100,
            stream=True
        )

        chunks = metadata.get("stream_chunks", [])

        if not chunks or "error" in metadata:
            return DetectionResult(
                detector_name="APILayerDetector",
                layer=self.LAYER_NAME,
                test_name="流式传输特征",
                passed=False,
                risk_level=RiskLevel.SUSPICIOUS,
                score=0.5,
                details={"error": metadata.get("error", "无流式响应")},
            )

        # 分析切片特征
        chunk_sizes = []
        for chunk in chunks:
            if hasattr(chunk, "choices") and chunk.choices:
                content = chunk.choices[0].delta.content or ""
                if content:
                    chunk_sizes.append(len(content))

        if not chunk_sizes:
            return DetectionResult(
                detector_name="APILayerDetector",
                layer=self.LAYER_NAME,
                test_name="流式传输特征",
                passed=True,
                risk_level=RiskLevel.SAFE,
                score=0.0,
                details={"note": "无法分析切片（内容为空）"},
            )

        # 计算切片大小分布
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        size_variance = sum((s - avg_size) ** 2 for s in chunk_sizes) / len(chunk_sizes)

        # 检测"卡顿-暴发"模式：方差大表示不稳定
        # OpenAI 官方：切片均匀，方差小
        # 劣质中转：方差大，有卡顿
        is_smooth = size_variance < 10  # 经验阈值

        if is_smooth:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        else:
            score = min(1.0, size_variance / 50)
            passed = score < 0.5
            risk = RiskLevel.SUSPICIOUS if passed else RiskLevel.FAKE

        return DetectionResult(
            detector_name="APILayerDetector",
            layer=self.LAYER_NAME,
            test_name="流式传输特征",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "chunk_count": len(chunk_sizes),
                "avg_chunk_size": round(avg_size, 2),
                "size_variance": round(size_variance, 2),
                "is_smooth": is_smooth,
            },
            raw_response=response[:200] if response else None,
        )
