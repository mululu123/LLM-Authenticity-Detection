"""
判定引擎 - 分析探针结果，输出最终结论
"""

import re
from typing import Optional
from dataclasses import dataclass

from src.probes.base import ProbeType
from src.engine.probe_engine import ScanResult
from src.database.model_profiles import ModelProfiles, TokenSignatures


@dataclass
class Verdict:
    """判定结果"""
    claimed_model: str
    real_model: str
    real_probability: float          # 真实模型概率 %
    scam_score: float                # 诈骗指数 0-100
    performance_tier: str            # S/A/B/C
    agent_rank: str                  # A/B/C/D/F
    confidence: float                # 综合置信度

    # 雷达图数据
    physical_authenticity: float     # 物理真实性 0-1
    cognitive_clarity: float         # 认知清晰度 0-1
    alignment_match: float           # 价值观符合度 0-1
    instruction_following: float     # 指令遵从度 0-1
    api_stability: float             # API 稳定性 0-1

    # 详细分析
    findings: list[str]

    def to_dict(self) -> dict:
        return {
            "claimed_model": self.claimed_model,
            "real_model": self.real_model,
            "real_probability": f"{self.real_probability:.1f}%",
            "scam_score": f"{self.scam_score:.0f}",
            "performance_tier": self.performance_tier,
            "agent_rank": self.agent_rank,
            "confidence": f"{self.confidence:.1%}",
            "radar": {
                "physical_authenticity": self.physical_authenticity,
                "cognitive_clarity": self.cognitive_clarity,
                "alignment_match": self.alignment_match,
                "instruction_following": self.instruction_following,
                "api_stability": self.api_stability,
            },
            "findings": self.findings,
        }

    def get_verdict_emoji(self) -> str:
        """获取判定结果的图标"""
        if self.scam_score < 30:
            return "✅"
        elif self.scam_score < 60:
            return "⚠️"
        else:
            return "❌"


class JudgeEngine:
    """判定引擎"""

    def __init__(self, claimed_model: str):
        self.claimed_model = claimed_model
        self.findings = []

    def analyze(self, scan_result: ScanResult) -> Verdict:
        """分析扫描结果"""
        # 获取各层结果
        physical = self._get_result(scan_result, ProbeType.PHYSICAL)
        subconscious = self._get_result(scan_result, ProbeType.SUBCONSCIOUS)
        alignment = self._get_result(scan_result, ProbeType.ALIGNMENT)
        logic = self._get_result(scan_result, ProbeType.LOGIC)
        agent = self._get_result(scan_result, ProbeType.AGENT)

        # 分析真实模型
        real_model, real_prob = self._detect_real_model(physical, subconscious, alignment)

        # 计算诈骗指数
        scam_score = self._calculate_scam_score(physical, subconscious, alignment, logic, agent)

        # 性能等级
        perf_tier = self._get_performance_tier(logic)

        # Agent 兼容等级
        agent_rank = self._get_agent_rank(agent)

        # 雷达图数据
        radar = self._calculate_radar(physical, subconscious, alignment, logic, agent)

        # 生成发现
        self._generate_findings(physical, subconscious, alignment, logic, agent)

        return Verdict(
            claimed_model=self.claimed_model,
            real_model=real_model,
            real_probability=real_prob,
            scam_score=scam_score,
            performance_tier=perf_tier,
            agent_rank=agent_rank,
            confidence=0.8,
            physical_authenticity=radar["physical"],
            cognitive_clarity=radar["cognitive"],
            alignment_match=radar["alignment"],
            instruction_following=radar["instruction"],
            api_stability=radar["stability"],
            findings=self.findings,
        )

    def _get_result(self, scan: ScanResult, probe_type: ProbeType):
        """获取探针结果"""
        results = scan.get_by_type(probe_type)
        return results[0] if results else None

    def _detect_real_model(
        self,
        physical,
        subconscious,
        alignment,
    ) -> tuple[str, float]:
        """检测真实模型"""
        candidates = {}

        # 从潜意识溯源获取线索
        if subconscious:
            detected = subconscious.details.get("detected_providers", [])
            for item in detected:
                provider = item.get("provider", "unknown")
                candidates[provider] = candidates.get(provider, 0) + 30

        # 从安全对齐获取线索
        if alignment:
            family = alignment.details.get("redteam", {}).get("detected_family")
            if family and family != "unknown":
                candidates[family] = candidates.get(family, 0) + 20

        # 从物理指纹获取线索
        if physical:
            tokenizer_family = physical.details.get("tokenizer", {}).get("detected_family")
            if tokenizer_family:
                candidates[tokenizer_family] = candidates.get(tokenizer_family, 0) + 15

            # 检测 DeepSeek R1
            if physical.details.get("has_reasoning_content"):
                candidates["deepseek"] = candidates.get("deepseek", 0) + 40
                candidates["deepseek-r1"] = candidates.get("deepseek-r1", 0) + 50

        # 判定
        if not candidates:
            return "Unknown", 50.0

        winner = max(candidates.items(), key=lambda x: x[1])
        model_map = {
            "openai": "GPT-4o/GPT-4",
            "anthropic": "Claude 3.5",
            "zhipu": "GLM-4/GLM-5",
            "alibaba": "Qwen",
            "deepseek": "DeepSeek-V3",
            "deepseek-r1": "DeepSeek-R1",
            "chinese_domestic": "国产模型 (Qwen/GLM)",
        }

        real_model = model_map.get(winner[0], winner[0].title())
        prob = min(95, 50 + winner[1])

        return real_model, prob

    def _calculate_scam_score(self, physical, subconscious, alignment, logic, agent) -> float:
        """计算诈骗指数 0-100"""
        score = 0

        # 身份泄露矛盾
        if subconscious:
            suspicious = subconscious.details.get("suspicious_providers", [])
            if suspicious:
                score += 40

        # 性能等级不达标
        if logic:
            tier = logic.details.get("performance_tier", "S")
            if tier in ["B", "C"]:
                score += 20

        # 格式污染
        if agent:
            agent_score = agent.details.get("json_test", {}).get("score", 0)
            score += agent_score * 20

        # 拒绝风格不符
        if alignment:
            align_score = alignment.score
            score += align_score * 20

        # DeepSeek R1 思维链暴露
        if physical and physical.details.get("has_reasoning_content"):
            # 如果声称的是非推理模型，这是高可疑
            if not any(r in self.claimed_model.lower() for r in ["r1", "reasoning", "thinking"]):
                score += 30

        return min(100, score)

    def _get_performance_tier(self, logic) -> str:
        """获取性能等级"""
        if logic:
            return logic.details.get("performance_tier", "B")
        return "C"

    def _get_agent_rank(self, agent) -> str:
        """获取 Agent 兼容等级"""
        if agent:
            return agent.details.get("agent_rank", "C")
        return "F"

    def _calculate_radar(self, physical, subconscious, alignment, logic, agent) -> dict:
        """计算雷达图数据"""
        return {
            "physical": 1 - (physical.score if physical else 0.3),
            "cognitive": 1 - (subconscious.score if subconscious else 0.3),
            "alignment": 1 - (alignment.score if alignment else 0.3),
            "instruction": 1 - (agent.score if agent else 0.3),
            "stability": 0.9,  # 暂时固定，后续可以根据错误率计算
        }

    def _generate_findings(self, physical, subconscious, alignment, logic, agent) -> None:
        """生成发现列表"""
        self.findings = []

        if physical:
            if physical.details.get("has_reasoning_content"):
                self.findings.append("⚠️ 检测到 reasoning_content 字段，疑似 DeepSeek-R1 推理模型")

            tokenizer = physical.details.get("tokenizer", {})
            detected = tokenizer.get("detected_family")
            if detected and detected != "unknown":
                self.findings.append(f"🔬 Token 特征匹配: {detected}")

        if subconscious:
            suspicious = subconscious.details.get("suspicious_providers", [])
            if suspicious:
                for item in suspicious:
                    self.findings.append(f"🚨 身份矛盾: 检测到 {item['provider']} 特征")

        if logic:
            tier = logic.details.get("performance_tier")
            if tier in ["B", "C"]:
                self.findings.append(f"⬇️ 性能等级: {tier}级，疑似低配模型冒充")

        if agent:
            rank = agent.details.get("agent_rank")
            if rank in ["D", "F"]:
                self.findings.append(f"❌ Agent 兼容性: {rank}级，不适合严格格式调用")