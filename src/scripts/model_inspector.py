"""
Model-Inspector CLI - 大模型照妖镜
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.probe_engine import ProbeEngine, ScanResult
from src.probes.physical_probe import PhysicalProbe
from src.probes.subconscious_probe import SubconsciousProbe
from src.probes.alignment_probe import AlignmentProbe
from src.probes.logic_probe import LogicProbe
from src.probes.agent_probe import AgentProbe
from src.judge.judge_engine import JudgeEngine, Verdict


def print_header(model: str) -> None:
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  🔍 Model-Inspector 照妖镜 v2.0")
    print(f"  目标模型: {model}")
    print(f"{'='*60}\n")


def print_verdict(verdict: Verdict) -> None:
    """打印判定结果"""
    print("\n" + "=" * 60)
    print("  📋 检测报告")
    print("=" * 60)

    # 核心结论
    emoji = verdict.get_verdict_emoji()
    print(f"\n{emoji} 结论: ", end="")

    if verdict.scam_score < 30:
        print(f"真实可信 (诈骗指数: {verdict.scam_score:.0f})")
    elif verdict.scam_score < 60:
        print(f"存在可疑 (诈骗指数: {verdict.scam_score:.0f})")
    else:
        print(f"高度疑似套壳 (诈骗指数: {verdict.scam_score:.0f})")

    print(f"\n📊 模型分析:")
    print(f"   声称模型: {verdict.claimed_model}")
    print(f"   真实模型: {verdict.real_model} (概率: {verdict.real_probability:.1f}%)")
    print(f"   性能等级: {verdict.performance_tier} 级")
    print(f"   Agent兼容: {verdict.agent_rank} 级")

    # 雷达图
    print(f"\n📈 雷达图:")
    radar = {
        "物理真实性": verdict.physical_authenticity,
        "认知清晰度": verdict.cognitive_clarity,
        "价值观符合度": verdict.alignment_match,
        "指令遵从度": verdict.instruction_following,
        "API稳定性": verdict.api_stability,
    }
    for name, value in radar.items():
        bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
        print(f"   {name}: {bar} {value:.0%}")

    # 发现
    if verdict.findings:
        print(f"\n🔎 关键发现:")
        for finding in verdict.findings:
            print(f"   {finding}")


def print_markdown_report(verdict: Verdict, scan_result: ScanResult) -> str:
    """生成 Markdown 报告"""
    lines = [
        "# Model-Inspector 检测报告",
        "",
        f"**检测时间**: {datetime.now().isoformat()}",
        "",
        "## 核心结论",
        "",
        f"| 项目 | 结果 |",
        f"|------|------|",
        f"| 声称模型 | {verdict.claimed_model} |",
        f"| 真实模型 | {verdict.real_model} ({verdict.real_probability:.1f}%) |",
        f"| 诈骗指数 | {verdict.scam_score:.0f}/100 |",
        f"| 性能等级 | {verdict.performance_tier} |",
        f"| Agent兼容 | {verdict.agent_rank} |",
        "",
        "## 雷达图",
        "",
        f"- 物理真实性: {verdict.physical_authenticity:.0%}",
        f"- 认知清晰度: {verdict.cognitive_clarity:.0%}",
        f"- 价值观符合度: {verdict.alignment_match:.0%}",
        f"- 指令遵从度: {verdict.instruction_following:.0%}",
        f"- API稳定性: {verdict.api_stability:.0%}",
        "",
        "## 关键发现",
        "",
    ]
    for f in verdict.findings:
        lines.append(f"- {f}")

    return "\n".join(lines)


async def run_inspector(
    base_url: str,
    api_key: str,
    model: str,
    verbose: bool = True,
) -> tuple[ScanResult, Verdict]:
    """运行检测"""

    # 创建引擎
    engine = ProbeEngine(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=60.0,
    )

    # 注册探针
    engine.register_probes([
        PhysicalProbe(base_url, api_key, model),
        SubconsciousProbe(base_url, api_key, model),
        AlignmentProbe(base_url, api_key, model),
        LogicProbe(base_url, api_key, model),
        AgentProbe(base_url, api_key, model),
    ])

    # 执行扫描
    scan_result = await engine.run_all(verbose=verbose)

    # 判定
    judge = JudgeEngine(model)
    verdict = judge.analyze(scan_result)

    return scan_result, verdict


def main():
    parser = argparse.ArgumentParser(
        description="Model-Inspector 照妖镜 - 大模型指纹脱壳检测"
    )
    parser.add_argument(
        "--endpoint", "-e",
        required=True,
        help="API 端点 URL",
    )
    parser.add_argument(
        "--api-key", "-k",
        help="API Key (也可通过环境变量设置)",
    )
    parser.add_argument(
        "--model", "-m",
        required=True,
        help="声称的模型名称",
    )
    parser.add_argument(
        "--output", "-o",
        help="报告输出路径",
    )
    parser.add_argument(
        "--format", "-f",
        default="text",
        choices=["text", "json", "markdown"],
        help="报告格式 (默认: text)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="静默模式",
    )

    args = parser.parse_args()

    # 获取 API Key (若无则使用默认占位符，适用于免密/本地测试)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or "sk-no-key-required"

    # 打印标题
    if not args.quiet:
        print_header(args.model)

    # 运行检测
    try:
        scan_result, verdict = asyncio.run(
            run_inspector(
                base_url=args.endpoint,
                api_key=api_key,
                model=args.model,
                verbose=not args.quiet,
            )
        )
    except Exception as e:
        print(f"❌ 检测失败: {e}")
        sys.exit(1)

    # 输出结果
    if args.format == "json":
        import json
        output = json.dumps({
            "verdict": verdict.to_dict(),
            "scan": scan_result.to_dict(),
        }, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        output = print_markdown_report(verdict, scan_result)
    else:
        print_verdict(verdict)
        output = None

    if args.output:
        Path(args.output).write_text(output or "", encoding="utf-8")
        print(f"\n📄 报告已保存到: {args.output}")
    elif output:
        print(output)

    # 退出码
    if verdict.scam_score >= 60:
        sys.exit(2)  # 高度可疑
    elif verdict.scam_score >= 30:
        sys.exit(1)  # 存在可疑
    else:
        sys.exit(0)  # 真实可信


if __name__ == "__main__":
    main()
