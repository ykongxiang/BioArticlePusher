# feishu_pusher.py
"""
飞书推送模块
将文章搜索结果推送到飞书机器人
"""

import json
import logging
import requests
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FeishuPusher:
    """飞书推送器类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化飞书推送器

        Args:
            config: 飞书配置字典
        """
        self.config = config
        self.webhook_url = config['webhook_url']
        self.max_articles_per_push = config['push_config']['max_articles_per_push']
        self.include_abstract = config['push_config']['include_abstract']
        self.abstract_max_length = config['push_config']['abstract_max_length']
        self.include_ai_evaluation = config['push_config']['include_ai_evaluation']
        self.template = config['push_config']['template']
        self.language = config['push_config'].get('language', 'zh')  # 默认中文

        # 验证配置
        if not self.webhook_url or self.webhook_url == "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id":
            logger.warning("⚠️ 飞书webhook URL未配置，将跳过推送")
            self.enabled = False
        else:
            self.enabled = True

    def push_articles(self, all_results: Dict[str, List[Dict[str, Any]]],
                     filtered_articles: List[Dict[str, Any]],
                     search_days: int) -> bool:
        """
        推送文章到飞书

        Args:
            all_results: 原始搜索结果，按期刊分组
            filtered_articles: AI过滤后的文章列表
            search_days: 搜索天数

        Returns:
            bool: 推送是否成功
        """
        if not self.config.get('enabled', False) or not self.enabled:
            logger.info("飞书推送已禁用")
            return True

        try:
            # 准备推送内容（卡片消息格式）
            card_message = self._prepare_message(all_results, filtered_articles, search_days)

            # 发送到飞书
            return self._send_to_feishu(card_message)

        except Exception as e:
            logger.error(f"飞书推送失败: {e}")
            return False

    def _format_single_article(self, article: Dict[str, Any], index: int) -> str:
        """
        格式化单篇文章为推送文本

        Args:
            article: 文章信息
            index: 文章序号

        Returns:
            str: 格式化的文章文本
        """
        # 基本信息
        title = article.get('title', 'N/A')
        journal = article.get('journal', 'N/A')
        # 显示所有作者，不截断
        authors_list = article.get('authors', [])
        if authors_list:
            authors = ', '.join(authors_list)
        else:
            authors = 'N/A'
        link = article.get('link', '')

        # AI评估信息
        ai_info = ""
        if self.include_ai_evaluation and 'ai_evaluation' in article:
            eval_data = article['ai_evaluation']
            score = eval_data.get('score', 0)
            description = eval_data.get('description', '')
            application_areas = eval_data.get('application_areas', [])
            
            # 构建AI评估信息
            ai_parts = [f"⭐ 评分: {score}"]
            
            # 添加应用领域
            if application_areas:
                areas_display = ', '.join(application_areas[:3])  # 最多显示3个领域
                ai_parts.append(f"🔬 领域: {areas_display}")
            
            # 添加AI总结描述
            if description:
                ai_parts.append(f"� AI总结: {description}")
            
            ai_info = "\n🤖 " + " | ".join(ai_parts)

        # 摘要信息
        abstract_info = ""
        if self.include_abstract and article.get('abstract'):
            abstract = article['abstract']
            if self.abstract_max_length > 0 and len(abstract) > self.abstract_max_length:
                abstract = abstract[:self.abstract_max_length] + "..."
            abstract_info = f"\n📄 摘要: {abstract}"

        # 格式化单篇文章
        article_text = f"""
{index}. {title}
   📰 期刊: {journal}
   👥 作者: {authors}{ai_info}{abstract_info}
   🔗 [查看原文]({link})"""

        return article_text

    def _prepare_message(self, all_results: Dict[str, List[Dict[str, Any]]],
                        filtered_articles: List[Dict[str, Any]],
                        search_days: int) -> Dict[str, Any]:
        """
        准备推送消息内容（卡片消息格式）

        Args:
            all_results: 原始搜索结果
            filtered_articles: 过滤后的文章
            search_days: 搜索天数

        Returns:
            Dict[str, Any]: 卡片消息结构
        """
        # 计算统计信息
        journal_count = len(all_results)
        total_articles = sum(len(articles) for articles in all_results.values())

        # 构建卡片消息
        return self._build_card_message(all_results, filtered_articles, search_days, 
                                       journal_count, total_articles)

    def _format_articles(self, articles: List[Dict[str, Any]]) -> str:
        """
        格式化文章列表为飞书消息格式

        Args:
            articles: 文章列表

        Returns:
            str: 格式化的文章内容
        """
        if not articles:
            return "📭 本次搜索未找到符合条件的文章"

        # 限制推送文章数量
        articles_to_push = articles[:self.max_articles_per_push]

        formatted_articles = []

        for i, article in enumerate(articles_to_push, 1):
            # 基本信息
            title = article.get('title', 'N/A')
            journal = article.get('journal', 'N/A')
            # 显示所有作者，不截断
            authors_list = article.get('authors', [])
            if authors_list:
                authors = ', '.join(authors_list)
            else:
                authors = 'N/A'
            link = article.get('link', '')

            # AI评估信息
            ai_info = ""
            if self.include_ai_evaluation and 'ai_evaluation' in article:
                eval_data = article['ai_evaluation']
                score = eval_data.get('score', 0)
                description = eval_data.get('description', '')
                application_areas = eval_data.get('application_areas', [])
                
                # 构建AI评估信息
                ai_parts = [f"⭐ 评分: {score}"]
                
                # 添加应用领域
                if application_areas:
                    areas_display = ', '.join(application_areas[:3])  # 最多显示3个领域
                    ai_parts.append(f"🔬 领域: {areas_display}")
                
                # 添加AI总结描述
                if description:
                    ai_parts.append(f"� AI总结: {description}")
                
                ai_info = "\n🤖 **AI评估**: " + " | ".join(ai_parts)

            # 摘要信息
            abstract_info = ""
            if self.include_abstract and article.get('abstract'):
                abstract = article['abstract']
                if self.abstract_max_length > 0 and len(abstract) > self.abstract_max_length:
                    abstract = abstract[:self.abstract_max_length] + "..."
                abstract_info = f"\n📄 **摘要**: {abstract}"

            # 格式化单篇文章
            article_text = f"""
{i}. **{title}**
   📰 **期刊**: {journal}
   👥 **作者**: {authors}{ai_info}{abstract_info}
   🔗 [查看原文]({link})"""

            formatted_articles.append(article_text)

        return "\n".join(formatted_articles)

    def _format_article_markdown(self, article: Dict[str, Any], index: int) -> str:
        """
        格式化单篇文章为Markdown格式

        Args:
            article: 文章信息
            index: 文章序号

        Returns:
            str: Markdown格式的文章内容
        """
        # 基本信息
        title = article.get('title', 'N/A')
        journal = article.get('journal', 'N/A')
        # 显示所有作者，不截断
        authors_list = article.get('authors', [])
        if authors_list:
            authors = ', '.join(authors_list)
        else:
            authors = 'N/A'
        link = article.get('link', '')
        
        # 构建文章内容
        content_parts = [f"**{index}. {title}**"]
        journal_label = "📰 **Journal**: " if self.language == 'en' else "📰 **期刊**: "
        authors_label = "👥 **Authors**: " if self.language == 'en' else "👥 **作者**: "
        content_parts.append(f"{journal_label}{journal}")
        content_parts.append(f"{authors_label}{authors}")
        
        # AI评估信息
        if self.include_ai_evaluation and 'ai_evaluation' in article:
            eval_data = article['ai_evaluation']
            score = eval_data.get('score', 0)
            description = eval_data.get('description', '')
            application_areas = eval_data.get('application_areas', [])
            
            # 根据语言设置显示不同的标签
            if self.language == 'en':
                ai_parts = [f"⭐ Score: {score}"]
                if application_areas:
                    areas_display = ', '.join(application_areas[:3])
                    ai_parts.append(f"🔬 Areas: {areas_display}")
                if description:
                    ai_parts.append(f"💡 AI Summary: {description}")
                content_parts.append(f"🤖 **AI Evaluation**: {' | '.join(ai_parts)}")
            else:
                ai_parts = [f"⭐ 评分: {score}"]
                if application_areas:
                    areas_display = ', '.join(application_areas[:3])
                    ai_parts.append(f"🔬 领域: {areas_display}")
                if description:
                    ai_parts.append(f"💡 AI总结: {description}")
                content_parts.append(f"🤖 **AI评估**: {' | '.join(ai_parts)}")
        
        # 摘要信息
        if self.include_abstract and article.get('abstract'):
            abstract = article['abstract']
            if self.abstract_max_length > 0 and len(abstract) > self.abstract_max_length:
                abstract = abstract[:self.abstract_max_length] + "..."
            abstract_label = "📄 **Abstract**: " if self.language == 'en' else "📄 **摘要**: "
            content_parts.append(f"{abstract_label}{abstract}")
        
        # 链接
        if link:
            link_text = "[View Article]({link})" if self.language == 'en' else "[查看原文]({link})"
            content_parts.append(f"🔗 {link_text.format(link=link)}")
        
        return "\n".join(content_parts)
    
    def _build_card_message(self, all_results: Dict[str, List[Dict[str, Any]]],
                           filtered_articles: List[Dict[str, Any]],
                           search_days: int,
                           journal_count: int,
                           total_articles: int) -> Dict[str, Any]:
        """
        构建飞书卡片消息结构

        Args:
            all_results: 原始搜索结果
            filtered_articles: 过滤后的文章
            search_days: 搜索天数
            journal_count: 期刊数量
            total_articles: 总文章数

        Returns:
            Dict[str, Any]: 卡片消息结构
        """
        elements = []
        
        # 标题部分
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.language == 'en':
            header_content = f"""**📰 Biological Article Push**

**📊 Search Statistics**
- Journals searched: {journal_count}
- Candidate articles: {total_articles}
- After AI filtering: {len(filtered_articles)}
- Generated at: {timestamp}"""
        else:
            header_content = f"""**📰 生物文章推送**

**📊 搜索统计**
- 搜索期刊: {journal_count} 个
- 候选文章: {total_articles} 篇
- AI筛选后: {len(filtered_articles)} 篇
- 生成时间: {timestamp}"""
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": header_content
            }
        })
        
        # 分隔线
        elements.append({"tag": "hr"})
        
        # 文章列表
        if not filtered_articles:
            no_articles_msg = "📭 No articles found matching the criteria" if self.language == 'en' else "📭 本次搜索未找到符合条件的文章"
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": no_articles_msg
                }
            })
        else:
            # 限制推送文章数量
            articles_to_push = filtered_articles[:self.max_articles_per_push]
            
            for i, article in enumerate(articles_to_push, 1):
                # 每篇文章作为一个div
                article_content = self._format_article_markdown(article, i)
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": article_content
                    }
                })
                
                # 文章之间添加分隔线（除了最后一篇）
                if i < len(articles_to_push):
                    elements.append({"tag": "hr"})
        
        # 底部信息
        elements.append({"tag": "hr"})
        footer_text = "🤖 *AI Smart Filtering | Biological Article Push*" if self.language == 'en' else "🤖 *AI智能筛选 | 生物文章推送*"
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": footer_text
            }
        })
        
        # 构建卡片消息
        card_message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": elements
            }
        }
        
        return card_message

    def _send_to_feishu(self, card_message: Dict[str, Any]) -> bool:
        """
        发送卡片消息到飞书

        Args:
            card_message: 卡片消息结构

        Returns:
            bool: 发送是否成功
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.webhook_url,
                headers=headers,
                json=card_message,
                timeout=30
            )

            response.raise_for_status()

            result = response.json()
            if result.get('code') == 0:
                logger.info("✅ 飞书推送成功")
                return True
            else:
                logger.error(f"飞书推送失败: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"飞书推送网络错误: {e}")
            return False
        except Exception as e:
            logger.error(f"飞书推送未知错误: {e}")
            return False


def create_feishu_pusher(config: Dict[str, Any]) -> FeishuPusher:
    """
    从配置创建飞书推送器

    Args:
        config: 完整配置字典

    Returns:
        FeishuPusher: 飞书推送器实例
    """
    feishu_config = config.get('feishu', {})
    return FeishuPusher(feishu_config)


def push_to_feishu(all_results: Dict[str, List[Dict[str, Any]]],
                  filtered_articles: List[Dict[str, Any]],
                  search_days: int,
                  config: Dict[str, Any]) -> bool:
    """
    推送文章到飞书的便捷函数

    Args:
        all_results: 原始搜索结果
        filtered_articles: 过滤后的文章
        search_days: 搜索天数
        config: 配置字典

    Returns:
        bool: 推送是否成功
    """
    pusher = create_feishu_pusher(config)
    return pusher.push_articles(all_results, filtered_articles, search_days)

