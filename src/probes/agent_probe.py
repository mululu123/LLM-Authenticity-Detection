"""
Agent 兼容性探针 - 极限 JSON 格式测试
"""

import re
import json
from .base import BaseProbe, ProbeResult, ProbeType


class AgentProbe(BaseProbe):
    """Agent 兼容性探针"""

    PROBE_TYPE = ProbeType.AGENT
    PROBE_NAME = "Agent兼容性检测"

    async def execute(self) -> ProbeResult:
        """执行 Agent 兼容性测试"""
        # 极限 JSON 格式测试 (PRD 指定 Prompt)
        result = await self._test_strict_json()

        # 判定 Agent 兼容等级
        rank = self._determine_rank(result["score"])

        return ProbeResult(
            probe_type=self.PROBE_TYPE,
            probe_name=self.PROBE_NAME,
            passed=result["score"] < 0.5,
            score=result["score"],
            confidence=0.9,
            details={
                "json_test": result,
                "agent_rank": rank,
            },
            raw_response=result.get("raw_response", ""),
        )

    async def _test_strict_json(self) -> dict:
        """
        极限 JSON 格式测试 (PRD 指定 Prompt)
        检测:
        1. 是否有 Markdown 标签污染
        2. 是否有废话前缀
        3. 数学运算是否正确 (质数)
        4. JSON 结构是否正确
        """
        # PRD 指定的 Prompt
        prompt = '''生成包含3个元素的JSON数组。要求：1. 只能输出原生JSON，绝不能包含 markdown 标签。2. 绝不能有任何前言后语。3. key必须是"a","b","c"，value是递增的质数，且第一个质数大于100。'''

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )

        response_text = response.strip()

        # 检测 Markdown 污染
        has_markdown = "```" in response_text

        # 检测废话前缀
        has_prefix = any(response_text.lower().startswith(kw) for kw in [
            "这是", "以下是", "here is", "following", "sure", "当然", "好的",
        ])

        # 尝试解析 JSON
        is_valid_json = False
        math_correct = False
        parsed_data = None

        # 尝试提取 JSON
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            try:
                parsed_data = json.loads(json_match.group())
                is_valid_json = True

                # 检查数学正确性
                # key 必须是 a, b, c
                # value 必须是递增质数，第一个 > 100
                if all(k in parsed_data for k in ["a", "b", "c"]):
                    vals = [parsed_data["a"], parsed_data["b"], parsed_data["c"]]
                    try:
                        vals = [int(v) for v in vals]
                        if vals[0] > 100 and vals[0] < vals[1] < vals[2]:
                            # 检查是否为质数
                            if all(self._is_prime(v) for v in vals):
                                math_correct = True
                    except:
                        pass
            except json.JSONDecodeError:
                pass

        # 计算分数
        score = 0.0
        issues = []

        if has_markdown:
            score += 0.3
            issues.append("Markdown污染")

        if has_prefix:
            score += 0.2
            issues.append("废话前缀")

        if not is_valid_json:
            score += 0.4
            issues.append("JSON格式错误")

        if is_valid_json and not math_correct:
            score += 0.2
            issues.append("数学运算错误")

        return {
            "has_markdown_pollution": has_markdown,
            "has_prefix": has_prefix,
            "is_valid_json": is_valid_json,
            "math_correct": math_correct,
            "score": min(1.0, score),
            "issues": issues,
            "raw_response": response_text,
        }

    def _is_prime(self, n: int) -> bool:
        """判断是否为质数"""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n ** 0.5) + 1, 2):
            if n % i == 0:
                return False
        return True

    def _determine_rank(self, score: float) -> str:
        """
        判定 Agent 兼容等级
        A: 完美兼容
        B: 基本兼容
        C: 可能有问题
        D: 有明显问题
        F: 会导致 Agent 崩溃
        """
        if score == 0:
            return "A"
        elif score < 0.2:
            return "B"
        elif score < 0.4:
            return "C"
        elif score < 0.6:
            return "D"
        else:
            return "F"