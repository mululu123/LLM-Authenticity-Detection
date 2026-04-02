#!/usr/bin/env python3
"""
模型指纹检测脚本 - 大模型照妖镜
用于识别 API 中转平台是否伪装模型

Usage:
    python fingerprint_test.py --api-key YOUR_KEY --model gpt-4
    python fingerprint_test.py --config config.yaml
    python fingerprint_test.py --endpoint https://api.example.com/v1 --api-key YOUR_KEY
"""

import argparse
import os
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI

from src.detectors.api_layer import APILayerDetector
from src.detectors.cognitive_layer import CognitiveLayerDetector
from src.detectors.alignment_layer import AlignmentLayerDetector
from src.detectors.logic_layer import LogicLayerDetector
from src.report_generator import ReportGenerator


def create_client(endpoint: str, api_key: str) -> OpenAI:
    """创建 OpenAI 兼容客户端"""
    return OpenAI(
        base_url=endpoint,
        api_key=api_key,
    )


def run_fingerprint_test(
    client: OpenAI,
    model_name: str,
    claimed_family: str = "openai",
    verbose: bool = True,
) -> ReportGenerator:
    """运行完整的指纹检测"""

    report = ReportGenerator(claimed_model=model_name)

    print(f"\n{'='*60}")
    print(f"  模型指纹检测 - 大模型照妖镜")
    print(f"  声称模型: {model_name}")
    print(f"{'='*60}\n")

    # Layer 1: API 与协议层
    if verbose:
        print("📡 第一层: API 与协议层侦测...")
    api_detector = APILayerDetector(client, model_name, claimed_family)
    api_detector.run_all_tests()
    report.add_summary(api_detector.get_summary())
    if verbose:
        print(f"   ✓ Tokenizer 计费检测")
        print(f"   ✓ 流式传输特征检测")

    # Layer 2: 认知与提示词层
    if verbose:
        print("\n🧠 第二层: 认知与提示词层探测...")
    cognitive_detector = CognitiveLayerDetector(client, model_name)
    cognitive_detector.run_all_tests()
    report.add_summary(cognitive_detector.get_summary())
    if verbose:
        print(f"   ✓ 翻译反向溯源")
        print(f"   ✓ Fallback 响应测试")
        print(f"   ✓ 知识截断测试")

    # Layer 3: 对齐与审查层
    if verbose:
        print("\n🛡️ 第三层: 对齐与审查机制探测...")
    alignment_detector = AlignmentLayerDetector(client, model_name)
    alignment_detector.run_all_tests()
    report.add_summary(alignment_detector.get_summary())
    if verbose:
        print(f"   ✓ 道德拒绝指纹")
        print(f"   ✓ 区域审查检测")

    # Layer 4: 逻辑与数学层
    if verbose:
        print("\n🔢 第四层: 逻辑与数学短板测试...")
    logic_detector = LogicLayerDetector(client, model_name)
    logic_detector.run_all_tests()
    report.add_summary(logic_detector.get_summary())
    if verbose:
        print(f"   ✓ 弱智吧逻辑题")
        print(f"   ✓ 浮点数陷阱")
        print(f"   ✓ 格式遵从度")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="模型指纹检测 - 识别 API 中转平台是否伪装模型"
    )
    parser.add_argument(
        "--endpoint",
        default="https://api.openai.com/v1",
        help="API 端点 URL (默认: OpenAI 官方)",
    )
    parser.add_argument(
        "--api-key",
        help="API Key (也可通过 OPENAI_API_KEY 环境变量设置)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4",
        help="声称的模型名称 (默认: gpt-4)",
    )
    parser.add_argument(
        "--family",
        default="openai",
        choices=["openai", "claude", "qwen", "llama"],
        help="声称的模型家族 (默认: openai)",
    )
    parser.add_argument(
        "--output",
        help="报告输出路径 (不指定则打印到控制台)",
    )
    parser.add_argument(
        "--format",
        default="markdown",
        choices=["json", "markdown"],
        help="报告格式 (默认: markdown)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，只输出报告",
    )

    args = parser.parse_args()

    # 获取 API Key (若无则使用默认占位符，适用于免密/本地测试)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or "sk-no-key-required"

    # 创建客户端
    client = create_client(args.endpoint, api_key)

    # 运行检测
    report = run_fingerprint_test(
        client=client,
        model_name=args.model,
        claimed_family=args.family,
        verbose=not args.quiet,
    )

    # 输出报告
    if args.output:
        report.save(args.output, args.format)
        if not args.quiet:
            print(f"\n📄 报告已保存到: {args.output}")
    else:
        print("\n" + "=" * 60)
        print(report.generate(args.format))

    # 返回退出码
    overall = report._calculate_overall()
    if overall["verdict"] == "fake":
        sys.exit(2)  # 确认为伪装
    elif overall["verdict"] == "suspicious":
        sys.exit(1)  # 存在可疑
    else:
        sys.exit(0)  # 真实可信


if __name__ == "__main__":
    main()
