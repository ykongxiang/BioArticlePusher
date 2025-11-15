# ai_filter.py
"""
AI辅助文章过滤模块
使用AI模型对文章进行智能筛选和评估
"""

import json
import os
import logging
import yaml
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AIFilter:
    """AI过滤器类"""

class AIFilter:
    """AI过滤器类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化AI过滤器

        Args:
            config: AI配置字典
        """
        self.config = config
        self.provider = config['model']['provider']
        self.model_name = config['model']['name']
        self.base_url = config['model']['base_url']
        self.demo_mode = config.get('demo_mode', False)  # 演示模式
        
        # 在演示模式下不需要API key
        if self.demo_mode:
            self.api_key = "demo"
        else:
            self.api_key = self._resolve_api_key(config['model']['api_key'])
            
        self.temperature = config['model']['temperature']
        self.max_tokens = config['model']['max_tokens']
        self.prompt_template = config['prompt']
        self.language = config.get('language', 'zh')  # 默认中文

        # 验证配置
        if not self.demo_mode and not self.api_key:
            raise ValueError("API key未设置，请在配置文件中设置或设置环境变量，或启用demo_mode")

    def _resolve_api_key(self, api_key_config: str) -> str:
        """
        解析API key，支持环境变量

        Args:
            api_key_config: API key配置字符串

        Returns:
            str: 解析后的API key
        """
        if api_key_config.startswith("${") and api_key_config.endswith("}"):
            env_var = api_key_config[2:-1]
            api_key = os.getenv(env_var)
            if not api_key:
                raise ValueError(f"环境变量 {env_var} 未设置")
            return api_key
        return api_key_config

    def filter_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用AI过滤文章列表

        Args:
            articles: 文章列表

        Returns:
            List[Dict]: 过滤后的文章列表（包含AI评估结果）
        """
        if not self.config.get('enabled', False):
            logger.info("AI过滤已禁用，返回所有文章")
            return articles

        logger.info(f"开始AI过滤，共 {len(articles)} 篇文章")

        filtered_articles = []

        for i, article in enumerate(articles):
            logger.info(f"AI评估文章 {i+1}/{len(articles)}: {article['title'][:50]}...")

            try:
                # AI评估文章
                ai_result = self._evaluate_article(article)

                # 添加AI评估结果到文章
                article_with_ai = article.copy()
                article_with_ai['ai_evaluation'] = ai_result

                # 如果文章相关，添加到结果中
                if ai_result.get('relevant', False):
                    filtered_articles.append(article_with_ai)
                    logger.info(f"✓ 文章通过AI过滤 (评分: {ai_result.get('score', 0)})")
                else:
                    logger.info(f"✗ 文章被AI过滤 (评分: {ai_result.get('score', 0)})")

            except Exception as e:
                logger.error(f"AI评估文章失败: {e}")
                # 如果AI评估失败，默认保留文章
                article_with_ai = article.copy()
                article_with_ai['ai_evaluation'] = {
                    'relevant': True,  # 默认保留
                    'score': 5,
                    'reason': f'AI评估失败: {str(e)}',
                    'tags': []
                }
                filtered_articles.append(article_with_ai)

        logger.info(f"AI过滤完成，保留 {len(filtered_articles)}/{len(articles)} 篇文章")
        return filtered_articles

    def _evaluate_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用AI评估单篇文章

        Args:
            article: 文章信息字典

        Returns:
            Dict: AI评估结果
        """
        # 准备提示词
        prompt = self._prepare_prompt(article)

        # 调用AI API
        # 优先尝试使用特定提供商的实现（如果有特殊需求）
        provider_lower = self.provider.lower()
        specific_method = f"_call_{provider_lower}_api"
        
        if hasattr(self, specific_method):
            # 使用特定提供商的实现
            method = getattr(self, specific_method)
            return method(prompt)
        else:
            # 使用通用API调用方法（适用于所有OpenAI兼容的API）
            return self._call_generic_api(prompt)

    def _prepare_prompt(self, article: Dict[str, Any]) -> str:
        """
        准备AI提示词

        Args:
            article: 文章信息

        Returns:
            str: 格式化的提示词
        """
        # 提取文章信息
        title = article.get('title', 'N/A')
        abstract = article.get('abstract', 'N/A')
        journal = article.get('journal', 'N/A')
        authors = ', '.join(article.get('authors', [])) if article.get('authors') else 'N/A'

        # 根据语言设置调整提示词
        prompt = self.prompt_template
        language_name = "English" if self.language == 'en' else "Chinese"
        
        # 替换语言占位符
        prompt = prompt.replace("{language}", language_name)
        if self.language == 'en':
            # 将提示词中的中文要求改为英文
            prompt = prompt.replace("Brief description in Chinese", "Brief description in English")
            prompt = prompt.replace("provide a brief description in Chinese", "provide a brief description in English")
            prompt = prompt.replace("description in Chinese", "description in English")

        # 格式化提示词
        return prompt.format(
            title=title,
            abstract=abstract,
            journal=journal,
            authors=authors
        )

    def _call_generic_api(self, prompt: str) -> Dict[str, Any]:
        """
        通用API调用方法，适用于所有OpenAI兼容的API
        
        此方法会自动适配任何支持OpenAI API格式的AI提供商，
        无需修改代码即可使用新的AI提供商。

        Args:
            prompt: 提示词

        Returns:
            Dict: API响应结果
        """
        if self.demo_mode:
            # 演示模式：返回模拟结果
            return self._get_demo_response(prompt)

        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # 解析JSON响应
            return json.loads(content)

        except requests.exceptions.RequestException as e:
            raise Exception(f"{self.provider} API请求失败: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析AI响应失败: {e}")

    def _call_deepseek_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用DeepSeek API（使用通用方法）

        Args:
            prompt: 提示词

        Returns:
            Dict: API响应结果
        """
        return self._call_generic_api(prompt)

    def _get_demo_response(self, prompt: str) -> Dict[str, Any]:
        """
        获取演示模式的模拟响应

        Args:
            prompt: 提示词

        Returns:
            Dict: 模拟的AI评估结果
        """
        # 解析文章信息
        title = ""
        abstract = ""
        if "Title: " in prompt:
            title_start = prompt.find("Title: ") + 7
            title_end = prompt.find("\n", title_start)
            title = prompt[title_start:title_end].lower()
        
        if "Abstract: " in prompt:
            abstract_start = prompt.find("Abstract: ") + 10
            abstract_end = prompt.find("\nJournal:", abstract_start)
            if abstract_end == -1:
                abstract_end = len(prompt)
            abstract = prompt[abstract_start:abstract_end].lower()

        # 模拟AI的完整评估过程
        full_text = (title + " " + abstract).lower()
        
        # 检查是否包含核心应用领域关键词
        application_areas = []
        descriptions = []
        
        # phenotype from genotype
        if any(word in full_text for word in ['phenotype', 'genotype', 'phenotype from genotype']):
            application_areas.append("phenotype from genotype")
            descriptions.append("predicts phenotypes from genotype data")
        
        # life cycle simulation
        if any(word in full_text for word in ['life cycle', 'lifecycle', 'simulation']):
            application_areas.append("life cycle simulation")
            descriptions.append("simulates life cycle processes")
        
        # cell cycle regulator
        if any(word in full_text for word in ['cell cycle', 'cell cycle regulator']):
            application_areas.append("cell cycle regulator")
            descriptions.append("studies cell cycle regulation")
        
        # single-cell multi-omics
        if any(word in full_text for word in ['single-cell', 'single cell', 'multi-omics', 'multiomics']):
            application_areas.append("single-cell multi-omics")
            descriptions.append("integrates single-cell multi-omics data")
        
        # scATAC-seq
        if 'scatac-seq' in full_text or 'scatac' in full_text:
            application_areas.append("scATAC-seq")
            descriptions.append("analyzes scATAC-seq data")
        
        # scRNA-seq
        if 'scrna-seq' in full_text or 'scrna' in full_text:
            application_areas.append("scRNA-seq")
            descriptions.append("analyzes scRNA-seq data")
        
        # chromatin accessibility
        if any(word in full_text for word in ['chromatin accessibility', 'chromatin access']):
            application_areas.append("chromatin accessibility")
            descriptions.append("studies chromatin accessibility")
        
        # gene regulatory network
        if any(word in full_text for word in ['gene regulatory', 'regulatory network']):
            application_areas.append("gene regulatory network")
            descriptions.append("models gene regulatory networks")
        
        # enhancer-gene linking
        if any(word in full_text for word in ['enhancer', 'enhancer-gene', 'enhancer gene']):
            application_areas.append("enhancer-gene linking")
            descriptions.append("links enhancers to genes")
        
        # chromatin potential
        if 'chromatin potential' in full_text:
            application_areas.append("chromatin potential")
            descriptions.append("analyzes chromatin potential")
        
        # GWAS variant enrichment
        if any(word in full_text for word in ['gwas', 'variant enrichment']):
            application_areas.append("GWAS variant enrichment")
            descriptions.append("performs GWAS variant enrichment")
        
        # eQTL
        if 'eqtl' in full_text:
            application_areas.append("eQTL")
            descriptions.append("conducts eQTL analysis")
        
        # metabolomics analysis
        if any(word in full_text for word in ['metabolomics', 'metabolome', 'metabolic profiling', 'metabolite']):
            application_areas.append("metabolomics analysis")
            descriptions.append("analyzes metabolomics data")
        
        # proteomics analysis
        if any(word in full_text for word in ['proteomics', 'proteome', 'protein identification', 'protein quantification']):
            application_areas.append("proteomics analysis")
            descriptions.append("analyzes proteomics data")
        
        # computational metabolomics
        if any(word in full_text for word in ['computational metabolomics', 'metabolomics algorithm', 'metabolomics method']):
            application_areas.append("computational metabolomics")
            descriptions.append("develops computational methods for metabolomics")
        
        # computational proteomics
        if any(word in full_text for word in ['computational proteomics', 'proteomics algorithm', 'proteomics method']):
            application_areas.append("computational proteomics")
            descriptions.append("develops computational methods for proteomics")
        
        # virtual cell
        if any(word in full_text for word in ['virtual cell', 'cell simulation', 'cellular modeling', 'in silico cell']):
            application_areas.append("virtual cell")
            descriptions.append("creates virtual cell models and simulations")
        
        # aging
        if any(word in full_text for word in ['aging', 'ageing', 'senescence', 'longevity', 'aging biology']):
            application_areas.append("aging")
            descriptions.append("studies aging processes and mechanisms")
        
        # foundation model
        if any(word in full_text for word in ['foundation model', 'foundational model', 'multimodal foundation model', 'biology foundation model', 'omics foundation model']):
            application_areas.append("foundation model")
            descriptions.append("develops foundation models for biological data")
        if application_areas:
            relevant = True
            score = min(10, 6 + len(application_areas) * 1)  # 基础分6，每匹配一个领域加1分
            
            # 根据语言设置生成描述
            if self.language == 'zh':
                # 中文描述
                zh_descriptions = {
                    "predicts phenotypes from genotype data": "预测基因型到表型",
                    "simulates life cycle processes": "模拟生命周期过程",
                    "studies cell cycle regulation": "研究细胞周期调控",
                    "integrates single-cell multi-omics data": "整合单细胞多组学数据",
                    "analyzes scATAC-seq data": "分析scATAC-seq数据",
                    "analyzes scRNA-seq data": "分析scRNA-seq数据",
                    "studies chromatin accessibility": "研究染色质可及性",
                    "models gene regulatory networks": "建模基因调控网络",
                    "links enhancers to genes": "连接增强子到基因",
                    "analyzes chromatin potential": "分析染色质潜力",
                    "performs GWAS variant enrichment": "进行GWAS变异富集分析",
                    "conducts eQTL analysis": "进行eQTL分析",
                    "analyzes metabolomics data": "分析代谢组学数据",
                    "analyzes proteomics data": "分析蛋白质组学数据",
                    "develops computational methods for metabolomics": "开发代谢组学计算方法",
                    "develops computational methods for proteomics": "开发蛋白质组学计算方法",
                    "creates virtual cell models and simulations": "创建虚拟细胞模型和模拟",
                    "studies aging processes and mechanisms": "研究衰老过程和机制",
                    "develops foundation models for biological data": "开发生物数据基础模型"
                }
                zh_desc = zh_descriptions.get(descriptions[0], descriptions[0])
                description = f"文章{zh_desc}"
                if len(descriptions) > 1:
                    zh_others = [zh_descriptions.get(d, d) for d in descriptions[1:]]
                    description += f"和{', '.join(zh_others)}"
            else:
                # 英文描述
                description = f"Article {descriptions[0]}"
                if len(descriptions) > 1:
                    description += f" and {', '.join(descriptions[1:])}"
        else:
            relevant = False
            score = 1
            if self.language == 'zh':
                description = "文章不属于指定的生物学应用领域"
            else:
                description = "Article does not focus on specified biological applications"
            application_areas = []

        return {
            "relevant": relevant,
            "score": score,
            "description": description,
            "application_areas": application_areas
        }

    def _call_kimi_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用Kimi API (Moonshot)（使用通用方法）

        Args:
            prompt: 提示词

        Returns:
            Dict: API响应结果
        """
        return self._call_generic_api(prompt)

    def _call_openai_api(self, prompt: str) -> Dict[str, Any]:
        """
        调用OpenAI API（使用通用方法）

        Args:
            prompt: 提示词

        Returns:
            Dict: API响应结果
        """
        return self._call_generic_api(prompt)


def load_ai_filter(config: Dict[str, Any]) -> AIFilter:
    """
    从配置创建AI过滤器

    Args:
        config: 完整配置字典

    Returns:
        AIFilter: AI过滤器实例
    """
    ai_config = config.get('ai_filtering', {})
    if not ai_config.get('enabled', False):
        # 返回一个禁用的过滤器
        return AIFilter({'enabled': False, 'model': {}, 'prompt': ''})

    # 检查是否启用演示模式
    demo_mode = ai_config.get('demo_mode', False)
    if demo_mode:
        logger.info("🤖 AI过滤器启用演示模式")
        ai_config['demo_mode'] = True

    return AIFilter(ai_config)


def filter_articles_with_ai(articles: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    使用AI过滤文章的便捷函数

    Args:
        articles: 文章列表
        config: 配置字典

    Returns:
        List[Dict]: 过滤后的文章列表
    """
    ai_filter = load_ai_filter(config)
    return ai_filter.filter_articles(articles)

