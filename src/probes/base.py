"""
探针基类 - 所有检测探针的抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import asyncio


class ProbeType(Enum):
    """探针类型"""
    PHYSICAL = "physical"           # 物理指纹层
    SUBCONSCIOUS = "subconscious"   # 潜意识溯源
    ALIGNMENT = "alignment"         # 安全对齐层
    LOGIC = "logic"                 # 逻辑与智商
    AGENT = "agent"                 # Agent兼容性


@dataclass
class ProbeResult:
    """探针检测结果"""
    probe_type: ProbeType
    probe_name: str
    passed: bool
    score: float                    # 0.0-1.0, 越高越可疑
    confidence: float               # 0.0-1.0, 置信度
    details: dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None
    latency_ms: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "probe_type": self.probe_type.value,
            "probe_name": self.probe_name,
            "passed": self.passed,
            "score": self.score,
            "confidence": self.confidence,
            "details": self.details,
            "raw_response": self.raw_response[:500] if self.raw_response else None,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class ModelFingerprint:
    """模型指纹特征"""
    name: str
    provider: str
    tokenizer_type: str
    has_reasoning: bool = False      # 是否有思维链
    performance_tier: str = "A"      # S/A/B/C
    refusal_style: str = "neutral"   # didactic/warning/hardcoded/weak
    knowledge_cutoff: str = ""


class BaseProbe(ABC):
    """探针基类"""

    PROBE_TYPE: ProbeType = ProbeType.PHYSICAL
    PROBE_NAME: str = "base"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @abstractmethod
    async def execute(self) -> ProbeResult:
        """执行探针测试"""
        pass

    async def _call_api(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """
        调用 API (异步)

        Returns:
            (response_text, metadata)
        """
        import httpx

        metadata = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "stream_chunks": [],
            "has_reasoning_content": False,
            "reasoning_content": None,
        }

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    # 流式请求
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
                        response.raise_for_status()
                        content = ""
                        chunks = []
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                import json
                                try:
                                    chunk = json.loads(data)
                                    chunks.append(chunk)
                                    if chunk.get("choices"):
                                        delta = chunk["choices"][0].get("delta", {})
                                        if delta.get("content"):
                                            content += delta["content"]
                                        # 检测 reasoning_content
                                        if delta.get("reasoning_content"):
                                            metadata["has_reasoning_content"] = True
                                            metadata["reasoning_content"] = delta["reasoning_content"]
                                except json.JSONDecodeError:
                                    pass
                        metadata["stream_chunks"] = chunks
                        metadata["latency_ms"] = (time.time() - start_time) * 1000
                        return content, metadata
                else:
                    # 非流式请求
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()

                    content = ""
                    if data.get("choices"):
                        message = data["choices"][0].get("message", {})
                        content = message.get("content", "") or ""

                        # 检测 reasoning_content (DeepSeek R1 特征)
                        if message.get("reasoning_content"):
                            metadata["has_reasoning_content"] = True
                            metadata["reasoning_content"] = message["reasoning_content"]

                    if data.get("usage"):
                        metadata["prompt_tokens"] = data["usage"].get("prompt_tokens", 0)
                        metadata["completion_tokens"] = data["usage"].get("completion_tokens", 0)

                    metadata["latency_ms"] = (time.time() - start_time) * 1000
                    return content, metadata

        except httpx.HTTPStatusError as e:
            metadata["latency_ms"] = (time.time() - start_time) * 1000
            metadata["error"] = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            return "", metadata
        except httpx.TimeoutException:
            metadata["latency_ms"] = (time.time() - start_time) * 1000
            metadata["error"] = "Request timeout"
            return "", metadata
        except Exception as e:
            metadata["latency_ms"] = (time.time() - start_time) * 1000
            metadata["error"] = str(e)
            return "", metadata