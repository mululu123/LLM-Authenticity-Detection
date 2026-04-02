"""
异步探针引擎 - 并发执行所有探针
"""

import asyncio
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.probes.base import BaseProbe, ProbeResult, ProbeType


@dataclass
class ScanResult:
    """扫描结果"""
    claimed_model: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: list[ProbeResult] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def get_by_type(self, probe_type: ProbeType) -> list[ProbeResult]:
        """按类型获取结果"""
        return [r for r in self.results if r.probe_type == probe_type]

    def to_dict(self) -> dict:
        return {
            "claimed_model": self.claimed_model,
            "timestamp": self.timestamp,
            "total_duration_ms": self.total_duration_ms,
            "results": [r.to_dict() for r in self.results],
        }


class ProbeEngine:
    """探针引擎 - 并发执行所有探针"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.probes: list[BaseProbe] = []

    def register_probe(self, probe: BaseProbe) -> None:
        """注册探针"""
        self.probes.append(probe)

    def register_probes(self, probes: list[BaseProbe]) -> None:
        """批量注册探针"""
        self.probes.extend(probes)

    async def run_all(self, verbose: bool = True) -> ScanResult:
        """并发执行所有探针"""
        import time
        start_time = time.time()

        if verbose:
            print(f"\n{'='*60}")
            print(f"  Model-Inspector 照妖镜")
            print(f"  目标模型: {self.model}")
            print(f"  探针数量: {len(self.probes)}")
            print(f"{'='*60}\n")

        # 并发执行
        tasks = [probe.execute() for probe in self.probes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        scan_result = ScanResult(claimed_model=self.model)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 探针执行异常
                probe = self.probes[i]
                error_result = ProbeResult(
                    probe_type=probe.PROBE_TYPE,
                    probe_name=probe.PROBE_NAME,
                    passed=False,
                    score=1.0,
                    confidence=1.0,
                    error=str(result),
                )
                scan_result.results.append(error_result)
            else:
                scan_result.results.append(result)

        scan_result.total_duration_ms = (time.time() - start_time) * 1000

        if verbose:
            self._print_progress(scan_result)

        return scan_result

    def _print_progress(self, result: ScanResult) -> None:
        """打印进度"""
        type_names = {
            ProbeType.PHYSICAL: "物理指纹层",
            ProbeType.SUBCONSCIOUS: "潜意识溯源",
            ProbeType.ALIGNMENT: "安全对齐层",
            ProbeType.LOGIC: "逻辑与智商",
            ProbeType.AGENT: "Agent兼容性",
        }

        for probe_type in ProbeType:
            results = result.get_by_type(probe_type)
            if results:
                icon = {"physical": "🔬", "subconscious": "🧠", "alignment": "🛡️", "logic": "🔢", "agent": "🤖"}
                print(f"{icon.get(probe_type.value, '•')} {type_names[probe_type]}")
                for r in results:
                    status = "✓" if r.passed else "✗"
                    print(f"   {status} {r.probe_name}: {'安全' if r.score < 0.3 else '可疑' if r.score < 0.6 else '异常'}")
                print()