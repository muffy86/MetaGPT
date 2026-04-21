#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/5 22:59
@Author  : alexanderwu
@File    : __init__.py
"""

from importlib import import_module

__all__ = [
    "GeminiLLM",
    "OpenAILLM",
    "ZhiPuAILLM",
    "AzureOpenAILLM",
    "MetaGPTLLM",
    "OllamaLLM",
    "HumanProvider",
    "SparkLLM",
    "QianFanLLM",
    "DashScopeLLM",
    "AnthropicLLM",
    "BedrockLLM",
    "ArkLLM",
    "OpenrouterReasoningLLM",
]

_LAZY_IMPORTS = {
    "GeminiLLM": ("metagpt.provider.google_gemini_api", "GeminiLLM"),
    "OpenAILLM": ("metagpt.provider.openai_api", "OpenAILLM"),
    "ZhiPuAILLM": ("metagpt.provider.zhipuai_api", "ZhiPuAILLM"),
    "AzureOpenAILLM": ("metagpt.provider.azure_openai_api", "AzureOpenAILLM"),
    "MetaGPTLLM": ("metagpt.provider.metagpt_api", "MetaGPTLLM"),
    "OllamaLLM": ("metagpt.provider.ollama_api", "OllamaLLM"),
    "HumanProvider": ("metagpt.provider.human_provider", "HumanProvider"),
    "SparkLLM": ("metagpt.provider.spark_api", "SparkLLM"),
    "QianFanLLM": ("metagpt.provider.qianfan_api", "QianFanLLM"),
    "DashScopeLLM": ("metagpt.provider.dashscope_api", "DashScopeLLM"),
    "AnthropicLLM": ("metagpt.provider.anthropic_api", "AnthropicLLM"),
    "BedrockLLM": ("metagpt.provider.bedrock_api", "BedrockLLM"),
    "ArkLLM": ("metagpt.provider.ark_api", "ArkLLM"),
    "OpenrouterReasoningLLM": ("metagpt.provider.openrouter_reasoning", "OpenrouterReasoningLLM"),
}


def __getattr__(name):
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
