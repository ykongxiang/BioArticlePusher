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
        推送文章到飞书（按主题分批次推送）

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
            # 检查是否启用主题分组推送
            group_by_topic = self.config.get('push_config', {}).get('group_by_topic', True)
            
            if group_by_topic:
                # 按主题分组并分批推送
                return self._push_by_topics(all_results, filtered_articles, search_days)
            else:
                # 原有推送方式（单次推送）
                card_message = self._prepare_message(all_results, filtered_articles, search_days)
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

    def _group_articles_by_topic(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        按主题分组文章

        Args:
            articles: 文章列表

        Returns:
            Dict[str, List[Dict]]: 按主题分组的文章字典
        """
        topic_groups = {}
        
        for article in articles:
            # 获取文章的主题
            topic = "other"  # 默认主题
            if 'ai_evaluation' in article:
                ai_eval = article['ai_evaluation']
                topic = ai_eval.get('topic', 'other')
            
            # 标准化主题名称
            topic = topic.lower().strip()
            if not topic or topic == '':
                topic = 'other'
            
            # 添加到对应主题组
            if topic not in topic_groups:
                topic_groups[topic] = []
            topic_groups[topic].append(article)
        
        return topic_groups
    
    def _push_by_topics(self, all_results: Dict[str, List[Dict[str, Any]]],
                       filtered_articles: List[Dict[str, Any]],
                       search_days: int) -> bool:
        """
        按主题分批次推送文章

        Args:
            all_results: 原始搜索结果
            filtered_articles: 过滤后的文章列表
            search_days: 搜索天数

        Returns:
            bool: 推送是否成功
        """
        # 按主题分组
        topic_groups = self._group_articles_by_topic(filtered_articles)
        
        logger.info(f"📊 文章已按主题分组，共 {len(topic_groups)} 个主题")
        for topic, articles in topic_groups.items():
            logger.info(f"  - {topic}: {len(articles)} 篇文章")
        
        # 计算统计信息
        journal_count = len(all_results)
        total_articles = sum(len(articles) for articles in all_results.values())
        
        # 按主题顺序推送（按文章数量降序）
        sorted_topics = sorted(topic_groups.items(), key=lambda x: len(x[1]), reverse=True)
        
        all_success = True
        topic_index = 0
        
        for topic, topic_articles in sorted_topics:
            topic_index += 1
            topic_name_display = self._get_topic_display_name(topic)
            
            logger.info(f"📤 推送主题 [{topic_index}/{len(sorted_topics)}]: {topic_name_display} ({len(topic_articles)} 篇文章)")
            
            # 如果该主题的文章超过单条消息限制，需要分批推送
            if len(topic_articles) > self.max_articles_per_push:
                # 分批推送
                batch_count = (len(topic_articles) + self.max_articles_per_push - 1) // self.max_articles_per_push
                logger.info(f"  ⚠️ 主题文章数量超过限制，将分为 {batch_count} 批推送")
                
                for batch_idx in range(batch_count):
                    start_idx = batch_idx * self.max_articles_per_push
                    end_idx = min(start_idx + self.max_articles_per_push, len(topic_articles))
                    batch_articles = topic_articles[start_idx:end_idx]
                    
                    logger.info(f"  📨 推送第 {batch_idx + 1}/{batch_count} 批 ({len(batch_articles)} 篇文章)")
                    
                    # 构建该批次的推送消息
                    card_message = self._build_topic_message(
                        all_results, batch_articles, search_days,
                        journal_count, total_articles, len(filtered_articles),
                        topic_name_display, batch_idx + 1, batch_count
                    )
                    
                    # 发送推送
                    if not self._send_to_feishu(card_message):
                        all_success = False
                        logger.error(f"  ❌ 主题 {topic_name_display} 第 {batch_idx + 1} 批推送失败")
                    else:
                        logger.info(f"  ✅ 主题 {topic_name_display} 第 {batch_idx + 1} 批推送成功")
                    
                    # 批次之间稍作延迟，避免请求过快
                    if batch_idx < batch_count - 1:
                        import time
                        time.sleep(0.5)
            else:
                # 单批推送
                card_message = self._build_topic_message(
                    all_results, topic_articles, search_days,
                    journal_count, total_articles, len(filtered_articles),
                    topic_name_display, 1, 1
                )
                
                if not self._send_to_feishu(card_message):
                    all_success = False
                    logger.error(f"  ❌ 主题 {topic_name_display} 推送失败")
                else:
                    logger.info(f"  ✅ 主题 {topic_name_display} 推送成功")
        
        if all_success:
            logger.info(f"✅ 所有主题推送完成，共推送 {len(sorted_topics)} 个主题")
        else:
            logger.warning(f"⚠️ 部分主题推送失败，共 {len(sorted_topics)} 个主题")
        
        return all_success
    
    def _get_topic_display_name(self, topic: str) -> str:
        """
        获取主题的显示名称

        Args:
            topic: 主题名称

        Returns:
            str: 显示名称
        """
        topic_names = {
            'single-cell': '单细胞分析' if self.language == 'zh' else 'Single-cell Analysis',
            'genomics': '基因组学' if self.language == 'zh' else 'Genomics',
            'proteomics': '蛋白质组学' if self.language == 'zh' else 'Proteomics',
            'metabolomics': '代谢组学' if self.language == 'zh' else 'Metabolomics',
            'network': '网络分析' if self.language == 'zh' else 'Network Analysis',
            'simulation': '模拟建模' if self.language == 'zh' else 'Simulation',
            'foundation_model': '基础模型' if self.language == 'zh' else 'Foundation Model',
            'aging': '衰老研究' if self.language == 'zh' else 'Aging',
            'other': '其他' if self.language == 'zh' else 'Other'
        }
        return topic_names.get(topic.lower(), topic)
    
    def _build_topic_message(self, all_results: Dict[str, List[Dict[str, Any]]],
                            topic_articles: List[Dict[str, Any]],
                            search_days: int,
                            journal_count: int,
                            total_articles: int,
                            filtered_count: int,
                            topic_name: str,
                            batch_num: int = 1,
                            total_batches: int = 1) -> Dict[str, Any]:
        """
        构建主题推送消息

        Args:
            all_results: 原始搜索结果
            topic_articles: 该主题的文章列表
            search_days: 搜索天数
            journal_count: 期刊数量
            total_articles: 总文章数
            filtered_count: 过滤后文章总数
            topic_name: 主题名称
            batch_num: 当前批次号
            total_batches: 总批次数

        Returns:
            Dict[str, Any]: 卡片消息结构
        """
        elements = []
        
        # 标题部分
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.language == 'en':
            header_content = f"""**📰 Biological Article Push - {topic_name}**

**📊 Search Statistics**
- Journals searched: {journal_count}
- Candidate articles: {total_articles}
- After AI filtering: {filtered_count}
- Topic: {topic_name} ({len(topic_articles)} articles)"""
            if total_batches > 1:
                header_content += f"\n- Batch: {batch_num}/{total_batches}"
            header_content += f"\n- Generated at: {timestamp}"""
        else:
            header_content = f"""**📰 生物文章推送 - {topic_name}**

**📊 搜索统计**
- 搜索期刊: {journal_count} 个
- 候选文章: {total_articles} 篇
- AI筛选后: {filtered_count} 篇
- 主题: {topic_name} ({len(topic_articles)} 篇)"""
            if total_batches > 1:
                header_content += f"\n- 批次: {batch_num}/{total_batches}"
            header_content += f"\n- 生成时间: {timestamp}"""
        
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
        if not topic_articles:
            no_articles_msg = "📭 No articles found" if self.language == 'en' else "📭 未找到文章"
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": no_articles_msg
                }
            })
        else:
            for i, article in enumerate(topic_articles, 1):
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
                if i < len(topic_articles):
                    elements.append({"tag": "hr"})
        
        # 底部信息
        elements.append({"tag": "hr"})
        footer_text = f"🤖 *AI Smart Filtering | {topic_name}*" if self.language == 'en' else f"🤖 *AI智能筛选 | {topic_name}*"
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

