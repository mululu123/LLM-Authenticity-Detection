"""
逻辑与智商探针 - 幻觉回旋测试、性能分级
"""

from .base import BaseProbe, ProbeResult, ProbeType


class LogicProbe(BaseProbe):
    """逻辑与智商探针"""

    PROBE_TYPE = ProbeType.LOGIC
    PROBE_NAME = "逻辑智商检测"

    # 性能等级阈值
    TIER_THRESHOLDS = {
        "S": 0.0,    # 全对，顶级模型
        "A": 0.2,    # 偶尔小瑕疵
        "B": 0.4,    # 有明显错误
        "C": 0.6,    # 错误较多
    }

    async def execute(self) -> ProbeResult:
        """执行逻辑智商测试"""
        results = []

        # 测试 1: 幻觉回旋
        hallucination = await self._test_hallucination()
        results.append(hallucination)

        # 测试 2: 弱智吧逻辑
        logic = await self._test_logic_puzzle()
        results.append(logic)

        # 测试 3: 浮点数陷阱
        float_test = await self._test_float_trap()
        results.append(float_test)

        # 测试 4: 知识截断探测
        cutoff_test = await self._test_knowledge_cutoff()
        results.append(cutoff_test)

        # 计算综合分数 (排除 cutoff_test 因为它主要用于特征收集而非直接计分)
        scored_results = [hallucination, logic, float_test]
        avg_score = sum(r.get("score", 0) for r in scored_results) / len(scored_results) if scored_results else 0

        # 判定性能等级
        tier = self._determine_tier(avg_score)

        return ProbeResult(
            probe_type=self.PROBE_TYPE,
            probe_name=self.PROBE_NAME,
            passed=avg_score < 0.4,
            score=avg_score,
            confidence=0.8,
            details={
                "hallucination_test": hallucination,
                "logic_puzzle": logic,
                "float_trap": float_test,
                "performance_tier": tier,
            },
        )

    async def _test_hallucination(self) -> dict:
        """
        幻觉回旋测试 (PRD 指定)
        "第一个在月球吃热狗的人是谁"
        S级模型: 指出前提错误
        B/C级模型: 编造宇航员名字
        """
        prompt = "第一个在月球吃热狗的人是谁？"

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )

        response_lower = response.lower()

        # 检测是否指出前提错误
        points_out_error = any(kw in response_lower for kw in [
            "没有", "不存在", "没有记录", "不知道", "不可能",
            "no one", "there is no", "never", "did not",
            "前提", "错误", "假设",
        ])

        # 检测是否编造答案
        fabricates = any(kw in response_lower for kw in [
            "阿姆斯特朗", "armstrong", "奥尔德林", "aldrin",
            "是", "可能是", "也许是",
        ]) and not points_out_error

        if points_out_error and not fabricates:
            score = 0.0  # 优秀
        elif points_out_error and fabricates:
            score = 0.3  # 有纠正但不够明确
        elif fabricates:
            score = 0.7  # 编造答案
        else:
            score = 0.4  # 不明确

        return {
            "points_out_error": points_out_error,
            "fabricates": fabricates,
            "score": score,
            "raw_response": response[:200],
        }

    async def _test_logic_puzzle(self) -> dict:
        """
        弱智吧逻辑题
        "我爸妈结婚的时候为什么没有邀请我？"
        S/A级: 正确回答"那时还没出生"
        B/C级: 编造家庭矛盾等
        """
        prompt = "我爸妈结婚的时候为什么没有邀请我？"

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )

        response_lower = response.lower()

        # 正确理解
        correct = any(kw in response_lower for kw in [
            "还没出生", "没出生", "不存在", "还没有你",
            "not born", "didn't exist", "weren't born",
        ])

        # 错误理解
        wrong = any(kw in response_lower for kw in [
            "家庭矛盾", "内部矛盾", "小型婚礼", "只邀请长辈",
            "family conflict", "small wedding",
        ]) and not correct

        if correct and not wrong:
            score = 0.0
        elif correct and wrong:
            score = 0.2
        elif wrong:
            score = 0.6
        else:
            score = 0.3

        return {
            "correct_understanding": correct,
            "wrong_understanding": wrong,
            "score": score,
        }

    async def _test_float_trap(self) -> dict:
        """
        浮点数陷阱
        "9.11 和 9.9 哪个更大？"
        小模型/旧模型: 错误回答 9.11 大
        """
        prompt = "9.11 和 9.9 哪个更大？请直接回答。"

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )

        response_text = response.strip()

        # 检查答案
        import re
        says_99_bigger = bool(re.search(r"9\.9\s*(更大|>|大|greater|larger)", response_text, re.I))
        says_911_bigger = bool(re.search(r"9\.11\s*(更大|>|大|greater|larger)", response_text, re.I))

        # 另一种检测方式
        if "9.9" in response_text and "大" in response_text:
            says_99_bigger = True
        if "9.11" in response_text and "大" in response_text and "9.9" not in response_text:
            says_911_bigger = True

        if says_99_bigger:
            score = 0.0
        elif says_911_bigger:
            score = 0.8
        else:
            score = 0.3

        return {
            "says_99_bigger": says_99_bigger,
            "says_911_bigger": says_911_bigger,
            "score": score,
            "raw_response": response_text,
        }

    async def _test_knowledge_cutoff(self) -> dict:
        """知识截断探测 (探测2024年中冷门事件)"""
        # 测试题: 2024年5月 Apple 发布的 iPad Pro M4 13英寸的厚度 (5.1mm)
        prompt = "苹果公司在2024年5月发布的搭载M4芯片的13英寸iPad Pro，其机身厚度是多少毫米？请直接回答数字。"

        response, metadata = await self._call_api(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )

        response_text = response.strip()
        knows_answer = "5.1" in response_text

        # 知识边界特征，当前仅作为特征提取，不直接影响基础分
        score = 0.0

        return {
            "score": score,
            "knows_2024_05_event": knows_answer,
            "raw_response": response_text,
        }

    def _determine_tier(self, avg_score: float) -> str:
        """判定性能等级"""
        if avg_score <= self.TIER_THRESHOLDS["S"]:
            return "S"
        elif avg_score <= self.TIER_THRESHOLDS["A"]:
            return "A"
        elif avg_score <= self.TIER_THRESHOLDS["B"]:
            return "B"
        else:
            return "C"