"""
基础检测器抽象类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"           # 模型身份可信
    SUSPICIOUS = "suspicious"  # 存在可疑特征
    FAKE = "fake"           # 确认为套壳/伪装


@dataclass
class DetectionResult:
    """检测结果"""
    detector_name: str
    layer: str              # 检测层级
    test_name: str          # 测试名称
    passed: bool            # 是否通过
    risk_level: RiskLevel
    score: float            # 0.0-1.0, 越高越可疑
    details: dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "detector_name": self.detector_name,
            "layer": self.layer,
            "test_name": self.test_name,
            "passed": self.passed,
            "risk_level": self.risk_level.value,
            "score": self.score,
            "details": self.details,
            "raw_response": self.raw_response,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class ModelProfile:
    """模型档案"""
    name: str
    provider: str
    tokenizer_type: str
    knowledge_cutoff: str
    fallback_pattern: str
    alignment_style: str


class BaseDetector(ABC):
    """检测器基类"""

    LAYER_NAME: str = "base"

    def __init__(self, client: Any, model_name: str = "gpt-4"):
        """
        初始化检测器

        Args:
            client: OpenAI/Anthropic 兼容的 API 客户端
            model_name: 声称的模型名称
        """
        self.client = client
        self.model_name = model_name
        self.results: list[DetectionResult] = []

    @abstractmethod
    def run_all_tests(self) -> list[DetectionResult]:
        """运行该层级的所有测试"""
        pass

    def _call_api(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> tuple[str, dict[str, Any]]:
        """
        调用 API

        Returns:
            (response_text, metadata)
        """
        metadata = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "stream_chunks": [],
        }

        start_time = time.time()

        try:
            # 兼容 OpenAI 格式的客户端
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
            )

            if stream:
                # 流式响应处理
                chunks = []
                content = ""
                for chunk in response:
                    chunks.append(chunk)
                    if chunk.choices and chunk.choices[0].delta.content:
                        content += chunk.choices[0].delta.content
                metadata["stream_chunks"] = chunks
                return content, metadata
            else:
                # 非流式响应
                content = response.choices[0].message.content or ""
                if hasattr(response, "usage"):
                    metadata["prompt_tokens"] = response.usage.prompt_tokens
                    metadata["completion_tokens"] = response.usage.completion_tokens

                latency = (time.time() - start_time) * 1000
                metadata["latency_ms"] = latency

                return content, metadata

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            metadata["latency_ms"] = latency
            return "", {"error": str(e), **metadata}

    def add_result(self, result: DetectionResult) -> None:
        """添加检测结果"""
        self.results.append(result)

    def get_summary(self) -> dict:
        """获取检测摘要"""
        if not self.results:
            return {"layer": self.LAYER_NAME, "tests": 0, "avg_score": 0.0}

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        avg_score = sum(r.score for r in self.results) / total

        return {
            "layer": self.LAYER_NAME,
            "tests": total,
            "passed": passed,
            "failed": total - passed,
            "avg_score": round(avg_score, 3),
            "results": [r.to_dict() for r in self.results],
        }
