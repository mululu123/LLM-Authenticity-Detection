"""
第四层：逻辑与数学短板测试
- 经典弱智吧测试
- 浮点数大小陷阱
- 格式遵从度测试
"""

from typing import Any
import re
from .base import BaseDetector, DetectionResult, RiskLevel


class LogicLayerDetector(BaseDetector):
    """逻辑与数学检测器"""

    LAYER_NAME = "逻辑与数学层"

    def run_all_tests(self) -> list[DetectionResult]:
        """运行所有逻辑层测试"""
        self.results = []

        # 测试 1: 弱智吧逻辑题
        self.results.append(self._test_logic_puzzle())

        # 测试 2: 浮点数陷阱
        self.results.append(self._test_float_comparison())

        # 测试 3: 格式遵从度
        self.results.append(self._test_format_compliance())

        return self.results

    def _test_logic_puzzle(self) -> DetectionResult:
        """经典弱智吧测试"""
        prompt = "我爸妈结婚的时候为什么没有邀请我？"

        response, metadata = self._call_api(prompt, max_tokens=200)

        response_lower = response.lower()

        # 正确答案：那时你还没出生
        correct_understanding = any(kw in response_lower for kw in [
            "还没出生", "没出生", "不存在", "还没有你",
            "not born", "didn't exist", "weren't born",
            "之后才", "之后才有",
        ])

        # 错误理解：分析家庭矛盾
        wrong_understanding = any(kw in response_lower for kw in [
            "家庭矛盾", "内部矛盾", "小型婚礼", "只邀请长辈",
            "可能是因为", "也许", "也许是因为",
            "family conflict", "small wedding",
        ])

        # 评估
        if correct_understanding and not wrong_understanding:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        elif correct_understanding and wrong_understanding:
            score = 0.3
            passed = True
            risk = RiskLevel.SAFE
        elif wrong_understanding and not correct_understanding:
            score = 0.7
            passed = False
            risk = RiskLevel.SUSPICIOUS
        else:
            score = 0.4
            passed = True
            risk = RiskLevel.SAFE

        return DetectionResult(
            detector_name="LogicLayerDetector",
            layer=self.LAYER_NAME,
            test_name="弱智吧逻辑题",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "correct_understanding": correct_understanding,
                "wrong_understanding": wrong_understanding,
            },
            raw_response=response,
        )

    def _test_float_comparison(self) -> DetectionResult:
        """浮点数大小陷阱测试"""
        prompt = "9.11 和 9.9 哪个更大？请直接回答。"

        response, metadata = self._call_api(prompt, max_tokens=100)

        response_text = response.strip()

        # 检查答案
        # 正确答案：9.9 更大
        says_99_bigger = bool(re.search(r"9\.9\s*(更大|>|大|greater|larger|bigger)", response_text, re.I))
        says_99_greater = "9.9" in response_text and ("大" in response_text or "greater" in response_text.lower() or ">" in response_text)

        # 错误答案：9.11 更大（tokenizer 陷阱）
        says_911_bigger = bool(re.search(r"9\.11\s*(更大|>|大|greater|larger|bigger)", response_text, re.I))
        says_911_greater = "9.11" in response_text and ("大" in response_text or "greater" in response_text.lower() or ">" in response_text) and "9.9" not in response_text

        correct = says_99_bigger or says_99_greater
        wrong = says_911_bigger or (says_911_greater and not correct)

        # 评估
        if correct and not wrong:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        elif wrong and not correct:
            score = 0.9
            passed = False
            risk = RiskLevel.FAKE
        else:
            score = 0.3
            passed = True
            risk = RiskLevel.SAFE

        return DetectionResult(
            detector_name="LogicLayerDetector",
            layer=self.LAYER_NAME,
            test_name="浮点数陷阱",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "says_99_bigger": says_99_bigger or says_99_greater,
                "says_911_bigger": says_911_bigger or says_911_greater,
            },
            raw_response=response,
        )

    def _test_format_compliance(self) -> DetectionResult:
        """格式遵从度测试"""
        prompt = """只输出包含"Hello"的 JSON，键名为 msg。不要输出任何其他多余字符。
不要解释，不要 markdown 代码块，只输出纯 JSON。"""

        response, metadata = self._call_api(prompt, max_tokens=100)

        response_text = response.strip()

        # 检查是否有多余字符
        has_markdown_block = "```" in response_text
        has_explanation = any(kw in response_text.lower() for kw in [
            "here is", "这是", "如下", "following", "sure", "当然",
        ])

        # 尝试解析 JSON
        is_valid_json = False
        try:
            import json
            # 提取可能的 JSON
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
                is_valid_json = "msg" in parsed and "Hello" in str(parsed["msg"])
        except:
            pass

        # 严格检查：只有 JSON，没有其他
        is_strict = is_valid_json and not has_markdown_block and not has_explanation

        # 评估
        if is_strict:
            score = 0.0
            passed = True
            risk = RiskLevel.SAFE
        elif is_valid_json:
            score = 0.3
            passed = True
            risk = RiskLevel.SAFE
        else:
            score = 0.6
            passed = False
            risk = RiskLevel.SUSPICIOUS

        return DetectionResult(
            detector_name="LogicLayerDetector",
            layer=self.LAYER_NAME,
            test_name="格式遵从度",
            passed=passed,
            risk_level=risk,
            score=score,
            details={
                "is_valid_json": is_valid_json,
                "is_strict_compliance": is_strict,
                "has_markdown_block": has_markdown_block,
                "has_explanation": has_explanation,
            },
            raw_response=response,
        )
