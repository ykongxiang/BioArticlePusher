# config_templates.py
"""
配置文件模板生成模块
"""

import yaml
from pathlib import Path
from typing import Optional


def create_config_template(output_path: Optional[str] = None) -> str:
    """
    创建主配置文件模板 (article_search_config.yaml)
    
    Args:
        output_path: 输出文件路径，如果为None则使用默认路径 "article_search_config.yaml"
    
    Returns:
        str: 创建的配置文件路径
    """
    if output_path is None:
        output_path = "article_search_config.yaml"
    
    config = {
        "search_config": {
            "days": 7,
            "max_results_per_journal": 20
        },
        "journals": {
            "pubmed_journals": [
                "Nature",
                "Science",
                "Cell",
                "Nature Biotechnology",
                "Nature Methods",
                "Genome Biology",
                "Genome Research",
                "Bioinformatics",
                "Briefings in Bioinformatics",
                "PLOS Computational Biology"
            ],
            "biorxiv": {
                "enabled": True,
                "subjects": [
                    "bioinformatics",
                    "computational_biology",
                    "genomics",
                    "systems_biology"
                ]
            }
        },
        "keywords": {
            "any": [
                "bioinformatics",
                "computational biology",
                "machine learning",
                "deep learning",
                "neural network",
                "transformer",
                "foundation model",
                "large language model",
                "protein language model",
                "genomic model",
                "multi-modal",
                "graph neural network",
                "single-cell",
                "spatial transcriptomics",
                "metabolomics",
                "proteomics",
                "virtual cell",
                "aging",
                "foundation model"
            ],
            "all": [""]
        },
        "authors": {
            "mode": "biorxiv_only",
            "include": [],
            "exclude": []
        },
        "output": {
            "filename_format": "search_results_{days}days.json",
            "show_details": True,
            "abstract_max_length": -1
        },
        "ai_filtering": {
            "enabled": True,
            "demo_mode": False,
            "language": "zh",  # 语言设置 (zh: 中文, en: 英文)
            "max_articles_for_filtering": 100,  # 最大检索上限，控制交给AI过滤的文章数量（0表示无限制）
            "model": {
                "provider": "kimi",
                "name": "kimi-k2-0905-preview",
                "api_key": "${secrets.ai.kimi.api_key}",
                "base_url": "${secrets.ai.kimi.base_url}",
                "temperature": 0.1,
                "max_tokens": 1000
            },
            "prompt": """Evaluate this article for relevance to specific biological processes/applications.

Core Application Areas:
1. phenotype from genotype
2. life cycle simulation
3. cell cycle regulator
4. single-cell multi-omics
5. scATAC-seq
6. scRNA-seq
7. chromatin accessibility
8. gene regulatory network
9. enhancer-gene linking
10. chromatin potential
11. GWAS variant enrichment
12. eQTL
13. metabolomics analysis
14. proteomics analysis
15. computational metabolomics
16. computational proteomics
17. virtual cell
18. aging
19. foundation model

Article Information:
Title: {title}
Abstract: {abstract}
Journal: {journal}

Instructions:
- Determine if the article focuses on ONE OR MORE of the core application areas above
- If relevant, provide a brief description in {language} of the main work and which application area(s) it addresses
- Score relevance from 1-10 (10 being most relevant to core areas)
- Be strict: only mark as relevant if it directly addresses biological processes in these areas

Return JSON only:
{{
  "relevant": true/false,
  "score": 1-10,
  "description": "Brief description in {language} of main work and application area(s)",
  "application_areas": ["list of matching areas from above"]
}}"""
        },
        "feishu": {
            "enabled": True,
            "webhook_url": "${secrets.feishu.webhook_url}",
            "push_config": {
                "max_articles_per_push": 10,
                "include_abstract": True,
                "abstract_max_length": 200,
                "include_ai_evaluation": True,
                "language": "zh",  # 推送语言设置 (zh: 中文, en: 英文)
                "template": """📰 **生物文章推送**

📊 **搜索统计**
- 搜索期刊: {journal_count} 个
- 候选文章: {total_articles} 篇
- AI筛选后: {filtered_articles} 篇

📝 **精选文章**

{articles_content}

---
🤖 *AI智能筛选 | 生物文章推送*
⏰ *生成时间: {timestamp}*"""
            }
        }
    }
    
    # 写入文件
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    return str(output_file.absolute())


def create_secrets_template(output_path: Optional[str] = None) -> str:
    """
    创建敏感信息配置文件模板 (secrets.yaml)
    
    Args:
        output_path: 输出文件路径，如果为None则使用默认路径 "secrets.yaml"
    
    Returns:
        str: 创建的配置文件路径
    """
    if output_path is None:
        output_path = "secrets.yaml"
    
    config = {
        "ai": {
            "kimi": {
                "api_key": "YOUR_KIMI_API_KEY_HERE",
                "base_url": "https://api.moonshot.cn/v1"
            },
            "deepseek": {
                "api_key": "",
                "base_url": "https://api.deepseek.com"
            },
            "openai": {
                "api_key": "",
                "base_url": "https://api.openai.com/v1"
            }
        },
        "feishu": {
            "webhook_url": "YOUR_FEISHU_WEBHOOK_URL_HERE"
        }
    }
    
    # 写入文件
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    return str(output_file.absolute())

