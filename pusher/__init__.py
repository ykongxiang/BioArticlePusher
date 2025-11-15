# BioArticlePusher
"""
BioArticlePusher - 生物文章推送系统

一个智能的文章搜索、AI过滤和飞书推送系统。

主要功能:
- 从PubMed和BioRxiv搜索文章
- 使用AI模型评估文章相关性（19个核心生物学应用领域）
- 支持作者过滤（可选择仅BioRxiv或全部来源）
- 自动推送筛选后的文章到飞书群聊
- 关键词过滤和结果保存
"""
__version__ = "1.0.0"
__author__ = "ykongxiang"

from .search import ArticleSearcher
from .ai_filter import filter_articles_with_ai
from .feishu_pusher import push_to_feishu
from .config_templates import create_config_template, create_secrets_template

__all__ = [
    "ArticleSearcher",
    "filter_articles_with_ai",
    "push_to_feishu",
    "create_config_template",
    "create_secrets_template"
]