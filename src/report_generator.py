"""
报告生成器
"""

import json
from datetime import datetime
from typing import Any
from pathlib import Path


class ReportGenerator:
    """生成检测报告"""

    def __init__(self, claimed_model: str):
        self.claimed_model = claimed_model
        self.summaries: list[dict] = []
        self.timestamp = datetime.now().isoformat()

    def add_summary(self, summary: dict) -> None:
        """添加层级检测摘要"""
        self.summaries.append(summary)

    def generate(self, format: str = "json") -> str:
        """生成报告"""
        report = {
            "meta": {
                "claimed_model": self.claimed_model,
                "timestamp": self.timestamp,
                "version": "0.1.0",
            },
            "overall": self._calculate_overall(),
            "layers": self.summaries,
        }

        if format == "json":
            return json.dumps(report, ensure_ascii=False, indent=2)
        elif format == "markdown":
            return self._to_markdown(report)
        else:
            return str(report)

    def _calculate_overall(self) -> dict:
        """计算总体评估"""
        if not self.summaries:
            return {"verdict": "unknown", "total_score": 0.0}

        total_tests = sum(s.get("tests", 0) for s in self.summaries)
        total_passed = sum(s.get("passed", 0) for s in self.summaries)

        if total_tests == 0:
            return {"verdict": "unknown", "total_score": 0.0}

        pass_rate = total_passed / total_tests
        avg_scores = [s.get("avg_score", 0) for s in self.summaries if s.get("tests", 0) > 0]
        total_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0.0

        # 判定结论
        if pass_rate >= 0.8 and total_score < 0.3:
            verdict = "authentic"  # 真实
        elif pass_rate >= 0.5 or total_score < 0.6:
            verdict = "suspicious"  # 可疑
        else:
            verdict = "fake"  # 伪装

        return {
            "verdict": verdict,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "pass_rate": round(pass_rate, 2),
            "total_score": round(total_score, 3),
        }

    def _to_markdown(self, report: dict) -> str:
        """转换为 Markdown 格式"""
        lines = [
            "# 模型指纹检测报告",
            "",
            f"**声称模型**: {report['meta']['claimed_model']}",
            f"**检测时间**: {report['meta']['timestamp']}",
            "",
            "## 总体评估",
            "",
        ]

        overall = report["overall"]
        verdict_emoji = {
            "authentic": "✅",
            "suspicious": "⚠️",
            "fake": "❌",
            "unknown": "❓",
        }
        verdict_text = {
            "authentic": "真实可信",
            "suspicious": "存在可疑",
            "fake": "确认为伪装",
            "unknown": "无法判定",
        }

        lines.append(f"| 项目 | 结果 |")
        lines.append(f"|------|------|")
        lines.append(f"| 结论 | {verdict_emoji.get(overall['verdict'], '')} {verdict_text.get(overall['verdict'], overall['verdict'])} |")
        lines.append(f"| 通过率 | {overall.get('pass_rate', 0) * 100:.0f}% |")
        lines.append(f"| 可疑分数 | {overall.get('total_score', 0):.2f} |")
        lines.append("")

        for layer in report["layers"]:
            lines.append(f"## {layer.get('layer', 'Unknown Layer')}")
            lines.append("")
            lines.append(f"- 测试数: {layer.get('tests', 0)}")
            lines.append(f"- 通过: {layer.get('passed', 0)}")
            lines.append(f"- 可疑分数: {layer.get('avg_score', 0):.2f}")
            lines.append("")

        return "\n".join(lines)

    def save(self, path: str, format: str = "json") -> None:
        """保存报告到文件"""
        content = self.generate(format)
        Path(path).write_text(content, encoding="utf-8")
