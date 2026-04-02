"""
模型指纹数据库 - 各模型特征基准
"""

from typing import Optional


class ModelProfiles:
    """模型指纹特征库"""

    MODELS = {
        "gpt-4o": {
            "name": "GPT-4o",
            "provider": "openai",
            "tokenizer_type": "tiktoken",
            "has_reasoning": False,
            "performance_tier": "S",
            "refusal_style": "warning_then_help",
            "knowledge_cutoff": "2024-04",
        },
        "gpt-4": {
            "name": "GPT-4",
            "provider": "openai",
            "tokenizer_type": "tiktoken",
            "has_reasoning": False,
            "performance_tier": "S",
            "refusal_style": "warning_then_help",
            "knowledge_cutoff": "2023-04",
        },
        "claude-3-5-sonnet": {
            "name": "Claude 3.5 Sonnet",
            "provider": "anthropic",
            "tokenizer_type": "claude",
            "has_reasoning": False,
            "performance_tier": "S",
            "refusal_style": "didactic_refusal",
            "knowledge_cutoff": "2024-04",
        },
        "claude-3-opus": {
            "name": "Claude 3 Opus",
            "provider": "anthropic",
            "tokenizer_type": "claude",
            "has_reasoning": False,
            "performance_tier": "S",
            "refusal_style": "didactic_refusal",
            "knowledge_cutoff": "2024-04",
        },
        "glm-4": {
            "name": "GLM-4",
            "provider": "zhipu",
            "tokenizer_type": "glm",
            "has_reasoning": False,
            "performance_tier": "A",
            "refusal_style": "chinese_hint",
            "knowledge_cutoff": "2024-03",
        },
        "glm-5": {
            "name": "GLM-5",
            "provider": "zhipu",
            "tokenizer_type": "glm",
            "has_reasoning": False,
            "performance_tier": "S",
            "refusal_style": "chinese_hint",
            "knowledge_cutoff": "2024-12",
        },
        "deepseek-v3": {
            "name": "DeepSeek-V3",
            "provider": "deepseek",
            "tokenizer_type": "deepseek",
            "has_reasoning": False,
            "performance_tier": "A",
            "refusal_style": "neutral",
            "knowledge_cutoff": "2024-06",
        },
        "deepseek-r1": {
            "name": "DeepSeek-R1",
            "provider": "deepseek",
            "tokenizer_type": "deepseek",
            "has_reasoning": True,
            "performance_tier": "A",
            "refusal_style": "neutral",
            "knowledge_cutoff": "2024-06",
        },
        "qwen-max": {
            "name": "Qwen Max",
            "provider": "alibaba",
            "tokenizer_type": "qwen",
            "has_reasoning": False,
            "performance_tier": "A",
            "refusal_style": "hardcoded_refusal",
            "knowledge_cutoff": "2024-06",
        },
        "llama-3": {
            "name": "Llama 3",
            "provider": "meta",
            "tokenizer_type": "sentencepiece",
            "has_reasoning": False,
            "performance_tier": "B",
            "refusal_style": "weak",
            "knowledge_cutoff": "2023-04",
        },
    }

    @classmethod
    def get_profile(cls, model: str) -> Optional[dict]:
        """获取模型档案"""
        return cls.MODELS.get(model.lower())

    @classmethod
    def get_by_provider(cls, provider: str) -> list[dict]:
        """按提供商获取模型"""
        return [m for m in cls.MODELS.values() if m["provider"] == provider]

    @classmethod
    def get_models_with_reasoning(cls) -> list[dict]:
        """获取所有有思维链的模型"""
        return [m for m in cls.MODELS.values() if m["has_reasoning"]]


class TokenSignatures:
    """Token 特征基准"""

    # 各模型家族的 Token 范围 (相同测试文本)
    # 测试文本: "The quick brown fox 诸葛大名垂宇宙 jumps over 1234567890 🚀?!"
    SIGNATURES = {
        "openai": {"min": 15, "max": 25},
        "anthropic": {"min": 18, "max": 28},
        "zhipu": {"min": 14, "max": 22},
        "alibaba": {"min": 12, "max": 20},
        "deepseek": {"min": 15, "max": 25},
        "meta": {"min": 25, "max": 40},
    }

    @classmethod
    def identify_family(cls, token_count: int) -> list[str]:
        """根据 Token 数识别可能的模型家族"""
        candidates = []
        for family, bounds in cls.SIGNATURES.items():
            if bounds["min"] <= token_count <= bounds["max"]:
                candidates.append(family)
        return candidates

    @classmethod
    def match_score(cls, token_count: int, family: str) -> float:
        """计算匹配分数 (0-1, 越小越匹配)"""
        bounds = cls.SIGNATURES.get(family, {"min": 0, "max": 999})
        mid = (bounds["min"] + bounds["max"]) / 2
        diff = abs(token_count - mid)
        return min(1.0, diff / 20)