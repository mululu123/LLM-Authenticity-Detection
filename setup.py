from setuptools import setup, find_packages

setup(
    name="model-inspector",
    version="2.0.0",
    description="大语言模型 API 防欺诈与评测平台 (大模型指纹脱壳工具)",
    author="Cline",
    packages=find_packages(include=["src", "src.*", "scripts", "scripts.*"]),
    install_requires=[
        "httpx",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "model-inspector=scripts.model_inspector:main",
        ],
    },
    python_requires=">=3.8",
)