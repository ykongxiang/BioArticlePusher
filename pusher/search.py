# search.py
"""
文章搜索和过滤模块
"""

import json
import logging
import re
import yaml
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dateutil import parser as date_parser

from .ai_filter import filter_articles_with_ai
from .feishu_pusher import push_to_feishu

logger = logging.getLogger(__name__)

# PubMed E-utilities API
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ESEARCH_URL = PUBMED_BASE_URL + "esearch.fcgi"
EFETCH_URL = PUBMED_BASE_URL + "efetch.fcgi"


class ArticleSearcher:
    """
    生物文章搜索器

    支持从PubMed和BioRxiv搜索文章，并进行关键词和作者过滤。
    """

    def __init__(self, config_file: str = "article_search_config.yaml",
                 secrets_file: str = "secrets.yaml"):
        """
        初始化文章搜索器

        Args:
            config_file: 主配置文件路径
            secrets_file: 敏感信息配置文件路径
        """
        self.config = self._load_config(config_file, secrets_file)
        self._setup_logging()

    def _load_config(self, config_file: str, secrets_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        # 加载主配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ 主配置文件加载成功: {config_file}")
        except FileNotFoundError:
            logger.warning(f"⚠️ 主配置文件不存在: {config_file}，使用默认配置")
            config = self._get_default_config()

        # 加载敏感信息配置
        secrets = {}
        if Path(secrets_file).exists():
            try:
                with open(secrets_file, 'r', encoding='utf-8') as f:
                    secrets = yaml.safe_load(f) or {}
                logger.info(f"✅ 敏感信息配置加载成功: {secrets_file}")
            except Exception as e:
                logger.warning(f"⚠️ 敏感信息配置加载失败: {e}")

        # 合并配置
        merged_config = self._merge_configs(config, secrets)

        # 解析变量引用
        merged_config = self._resolve_variable_references(merged_config, merged_config)

        return merged_config

    def _merge_configs(self, main_config: Dict, secrets_config: Dict) -> Dict:
        """合并主配置和敏感信息配置"""
        import copy
        merged = copy.deepcopy(main_config)
        merged['secrets'] = secrets_config
        return merged

    def _resolve_variable_references(self, config: Any, root_config: Dict, max_depth: int = 10) -> Any:
        """解析配置中的变量引用"""
        if max_depth <= 0:
            raise ValueError("配置变量引用深度过大，可能存在循环引用")

        if isinstance(config, dict):
            resolved = {}
            for key, value in config.items():
                resolved[key] = self._resolve_variable_references(value, root_config, max_depth - 1)
            return resolved
        elif isinstance(config, list):
            return [self._resolve_variable_references(item, root_config, max_depth - 1) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # 解析变量引用
            var_path = config[2:-1]
            try:
                return self._get_nested_value(root_config, var_path)
            except KeyError:
                logger.warning(f"⚠️ 无法解析变量引用: {config}，保留原值")
                return config
        else:
            return config

    def _get_nested_value(self, config: Dict, path: str) -> Any:
        """从嵌套字典中获取值"""
        keys = path.split(".")
        current = config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                raise KeyError(f"路径 {path} 中的键 {key} 不存在")

        return current

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "search_config": {
                "days": 7,
                "max_results_per_journal": 20
            },
            "journals": {
                "pubmed_journals": ["nature", "science", "genome_biology"],
                "biorxiv": {
                    "enabled": True,
                    "subjects": ["bioinformatics", "computational_biology"]
                }
            },
            "keywords": {
                "any": ["cancer", "tumor", "DNA", "RNA"],
                "all": []
            },
            "authors": {
                "include": [],
                "exclude": []
            },
            "output": {
                "filename_format": "search_results_{days}days.json",
                "show_details": True,
                "abstract_max_length": -1
            }
        }

    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def search_articles(self, days: int = 7, max_results_per_journal: int = 20) -> Dict[str, List[Dict]]:
        """
        搜索文章

        Args:
            days: 搜索最近几天
            max_results_per_journal: 每个期刊最大结果数

        Returns:
            Dict[str, List[Dict]]: 各期刊的文章列表
        """
        # 获取期刊列表
        journals = self.config["journals"]["pubmed_journals"].copy()
        if self.config["journals"]["biorxiv"]["enabled"]:
            journals.append("biorxiv")

        # 获取关键词
        keywords = self.config["keywords"]["any"] + self.config["keywords"]["all"]

        # BioRxiv 学科
        biorxiv_subjects = self.config["journals"]["biorxiv"]["subjects"]

        # 作者配置
        author_config = self.config.get("authors", {})

        logger.info(f"开始搜索最近 {days} 天的文章...")
        results = self._search_journals(journals, keywords, days, max_results_per_journal,
                                      biorxiv_subjects, author_config)

        logger.info(f"搜索完成，共找到 {sum(len(articles) for articles in results.values())} 篇文章")
        return results

    def _search_journals(self, journals: List[str], keywords: List[str], days: int,
                        max_results_per_journal: int, biorxiv_subjects: List[str],
                        author_config: Dict) -> Dict[str, List[Dict]]:
        """从指定期刊搜索文章"""
        results = {}

        for journal in journals:
            journal_lower = journal.lower()

            logger.info(f"搜索期刊: {journal}")

            if journal_lower == "biorxiv":
                articles = self._search_biorxiv(biorxiv_subjects, keywords, days, max_results_per_journal)
                # 对BioRxiv文章进行作者过滤
                articles = self._filter_by_authors(articles, author_config, source="biorxiv")
            else:
                # 直接使用期刊名称加上[Journal]后缀作为PubMed查询
                journal_query = f"{journal}[Journal]"
                articles = self._search_pubmed_journal(journal_query, keywords, days, max_results_per_journal)
                # PubMed文章根据模式决定是否进行作者过滤
                if author_config.get("mode") == "all":
                    articles = self._filter_by_authors(articles, author_config, source="pubmed")

            results[journal] = articles
            logger.info(f"{journal}: 找到 {len(articles)} 篇文章")

        return results

    def _search_pubmed_journal(self, journal_query: str, keywords: List[str],
                              days: int, max_results: int) -> List[Dict]:
        """从PubMed指定期刊搜索文章"""
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_range = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[dp]"

        # 构建查询
        query_parts = [journal_query, date_range]
        if keywords:
            keyword_query = " OR ".join(f'"{kw}"' for kw in keywords)
            query_parts.append(f"({keyword_query})")

        query = " AND ".join(f"({part})" for part in query_parts)

        # 搜索
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance"
        }

        try:
            response = requests.get(ESEARCH_URL, params=search_params, timeout=30)
            response.raise_for_status()
            search_results = response.json()

            pmids = search_results["esearchresult"]["idlist"]
            if not pmids:
                return []

            # 获取文章详情
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml"
            }

            fetch_response = requests.get(EFETCH_URL, params=fetch_params, timeout=30)
            fetch_response.raise_for_status()

            # 解析XML结果
            articles = self._parse_pubmed_xml(fetch_response.text)
            return articles[:max_results]

        except Exception as e:
            logger.error(f"搜索PubMed失败: {e}")
            return []

    def _parse_pubmed_xml(self, xml_content: str) -> List[Dict]:
        """解析PubMed XML结果"""
        import xml.etree.ElementTree as ET

        articles = []
        root = ET.fromstring(xml_content)

        for article in root.findall(".//PubmedArticle"):
            try:
                # 提取标题
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else "No title"

                # 提取摘要
                abstract_elem = article.find(".//AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""

                # 提取作者
                authors = []
                for author_elem in article.findall(".//Author"):
                    last_name = author_elem.find("LastName")
                    fore_name = author_elem.find("ForeName")
                    if last_name is not None and fore_name is not None:
                        # PubMed格式: "LastName, ForeName"
                        # 转换为更常见的 "ForeName LastName" 格式
                        authors.append(f"{fore_name.text} {last_name.text}")
                    elif last_name is not None:
                        authors.append(last_name.text)

                # 提取期刊信息
                journal_elem = article.find(".//Journal/Title")
                journal = journal_elem.text if journal_elem is not None else "Unknown"

                # 提取DOI
                doi_elem = article.find(".//ELocationID[@EIdType='doi']")
                doi = doi_elem.text if doi_elem is not None else ""

                # 提取发表日期
                pub_date_elem = article.find(".//PubDate")
                published = "Unknown"
                if pub_date_elem is not None:
                    year = pub_date_elem.find("Year")
                    month = pub_date_elem.find("Month")
                    day = pub_date_elem.find("Day")
                    if year is not None:
                        date_str = year.text
                        if month is not None:
                            date_str += f"-{month.text.zfill(2)}"
                            if day is not None:
                                date_str += f"-{day.text.zfill(2)}"
                        try:
                            published = datetime.strptime(date_str, "%Y-%m-%d").isoformat()
                        except:
                            published = date_str

                articles.append({
                    'title': title,
                    'abstract': abstract,
                    'authors': authors,
                    'journal': journal,
                    'doi': doi,
                    'published': published,
                    'link': f"https://doi.org/{doi}" if doi else "",
                    'source': 'PubMed'
                })

            except Exception as e:
                logger.error(f"解析PubMed文章失败: {e}")
                continue

        return articles

    def _search_biorxiv(self, subjects: List[str], keywords: List[str],
                       days: int, max_results: int) -> List[Dict]:
        """从BioRxiv搜索文章"""
        all_articles = []

        for subject in subjects:
            logger.info(f"获取RSS: https://connect.biorxiv.org/biorxiv_xml.php?subject={subject}")

            try:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                # 构建RSS URL
                rss_url = f"https://connect.biorxiv.org/biorxiv_xml.php?subject={subject}"

                # 解析RSS
                feed = feedparser.parse(rss_url)

                for entry in feed.entries:
                    try:
                        # 解析发表日期 - BioRxiv可能使用不同的日期字段
                        published_str = entry.get('published', '') or entry.get('updated', '') or entry.get('prism_publicationdate', '')
                        
                        if not published_str:
                            # 如果没有日期信息，跳过此条目
                            continue
                        
                        # 尝试解析日期
                        try:
                            published_dt = date_parser.parse(published_str)
                        except (ValueError, TypeError):
                            # 如果日期解析失败，尝试从其他字段获取
                            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                import time
                                published_dt = datetime(*entry.published_parsed[:6])
                            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                                import time
                                published_dt = datetime(*entry.updated_parsed[:6])
                            else:
                                # 无法解析日期，跳过
                                continue
                        
                        if published_dt < start_date:
                            continue

                        # 解析作者
                        author_str = entry.get('author', '')
                        authors = self._parse_biorxiv_authors(author_str)

                        article = {
                            'title': entry.get('title', ''),
                            'abstract': entry.get('summary', ''),
                            'authors': authors,
                            'journal': 'BioRxiv',
                            'published': published_dt.isoformat(),
                            'link': entry.get('link', ''),
                            'source': 'BioRxiv',
                        }

                        all_articles.append(article)

                    except Exception as e:
                        # 静默跳过解析失败的条目，避免大量错误日志
                        continue

                # 避免请求过于频繁
                import time
                time.sleep(1)

            except Exception as e:
                logger.error(f"获取RSS失败: {e}")
                continue

        # 关键词过滤
        filtered = self._filter_by_keywords(all_articles, keywords)
        return filtered[:max_results]

    def _parse_biorxiv_authors(self, author_str: str) -> List[str]:
        """
        解析BioRxiv作者字符串，保留完整的作者名字
        
        BioRxiv格式示例:
        - "Theis, Fabian J." -> "Fabian J. Theis"
        - "Baker, David" -> "David Baker"
        - "Regev, Aviv" -> "Aviv Regev"
        """
        if not author_str or not isinstance(author_str, str):
            return []

        # 移除可能的换行符和多余空格
        author_str = author_str.strip()

        # BioRxiv格式: "LastName, FirstName/Initials., LastName, FirstName/Initials."
        # 使用正则表达式来正确解析
        pattern = r'([^,]+),\s*([^,]+?)(?:\.|,|$)'
        matches = re.findall(pattern, author_str)

        authors = []
        for match in matches:
            last_name = match[0].strip()
            first_name_or_initials = match[1].strip().rstrip('.')
            
            # 将格式从 "LastName, FirstName" 转换为 "FirstName LastName"
            # 这样更符合常见的名字显示格式
            if first_name_or_initials:
                # 如果first_name_or_initials是缩写（如 "F. J."），保留原格式
                # 如果是全名（如 "Fabian"），转换为 "FirstName LastName"
                if len(first_name_or_initials.split()) == 1 and len(first_name_or_initials) <= 3:
                    # 可能是单个缩写，保持 "LastName, Initials" 格式
                    authors.append(f"{last_name}, {first_name_or_initials}")
                else:
                    # 全名格式，转换为 "FirstName LastName"
                    authors.append(f"{first_name_or_initials} {last_name}")
            else:
                # 只有姓，保留原格式
                authors.append(last_name)

        # 如果没有匹配到任何作者，尝试按逗号分割
        if not authors:
            parts = [p.strip() for p in author_str.split(',')]
            if len(parts) >= 2:
                # 假设格式是 "LastName, FirstName"
                authors.append(f"{parts[1]} {parts[0]}")
            elif author_str.strip():
                authors.append(author_str.strip())

        return authors

    def _filter_by_keywords(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """根据关键词过滤文章"""
        if not keywords:
            return articles

        filtered = []
        for article in articles:
            title = article.get('title', '').lower()
            abstract = article.get('abstract', '').lower()
            text = title + " " + abstract

            if any(kw.lower() in text for kw in keywords):
                filtered.append(article)

        return filtered

    def _normalize_author_name(self, author_name: str) -> str:
        """
        标准化作者名字，用于匹配
        
        将不同格式的名字转换为统一的格式进行比较：
        - "Fabian Theis" -> "fabian theis"
        - "Theis, Fabian" -> "fabian theis"
        - "Theis, Fabian J." -> "fabian theis"
        - "Fabian J. Theis" -> "fabian theis"
        """
        if not author_name:
            return ""
        
        # 转换为小写并移除多余空格
        normalized = author_name.lower().strip()
        
        # 处理 "LastName, FirstName" 格式
        if ',' in normalized:
            parts = [p.strip() for p in normalized.split(',')]
            if len(parts) >= 2:
                # 交换顺序：LastName, FirstName -> FirstName LastName
                normalized = f"{parts[1]} {parts[0]}"
            else:
                normalized = parts[0]
        
        # 移除中间名和缩写（保留姓和名）
        # 例如 "fabian j. theis" -> "fabian theis"
        words = normalized.split()
        if len(words) >= 2:
            # 保留第一个词（名）和最后一个词（姓）
            # 移除中间的缩写（如 "j.", "f.", 等）
            first_name = words[0]
            last_name = words[-1]
            # 如果中间有单字母或缩写，忽略它们
            normalized = f"{first_name} {last_name}"
        
        return normalized.strip()
    
    def _author_names_match(self, author1: str, author2: str) -> bool:
        """
        判断两个作者名字是否指向同一个人
        
        支持多种格式匹配：
        - "Fabian Theis" 匹配 "Fabian J. Theis"
        - "Theis, Fabian" 匹配 "Fabian Theis"
        - "Fabian Theis" 匹配 "Theis, Fabian J."
        """
        if not author1 or not author2:
            return False
        
        # 标准化两个名字
        norm1 = self._normalize_author_name(author1)
        norm2 = self._normalize_author_name(author2)
        
        # 完全匹配
        if norm1 == norm2:
            return True
        
        # 部分匹配：检查是否包含对方的姓和名
        # 例如 "fabian theis" 应该匹配 "fabian j. theis"
        words1_list = norm1.split()
        words2_list = norm2.split()
        
        # 如果两个名字的姓和名都匹配，认为是同一个人
        # 至少需要匹配姓（最后一个词）和名（第一个词）
        if len(words1_list) >= 2 and len(words2_list) >= 2:
            # 检查姓和名是否都匹配
            first1 = words1_list[0]
            last1 = words1_list[-1]
            first2 = words2_list[0]
            last2 = words2_list[-1]
            
            # 检查姓和名是否匹配
            if (last1 == last2) and (first1 == first2):
                return True
        
        # 如果标准化后的名字有包含关系，也认为是匹配
        # 例如 "fabian theis" 包含在 "fabian j. theis" 中
        if norm1 in norm2 or norm2 in norm1:
            # 但需要确保至少包含姓
            words1_list = norm1.split()
            words2_list = norm2.split()
            if words1_list and words2_list:
                if words1_list[-1] == words2_list[-1]:  # 姓匹配
                    return True
        
        return False

    def _filter_by_authors(self, articles: List[Dict], author_config: Dict, source: str = "all") -> List[Dict]:
        """
        根据作者配置过滤文章
        
        使用智能匹配算法，能够识别同一个人的不同名字格式
        """
        if not author_config or not author_config.get("include"):
            return articles

        mode = author_config.get("mode", "biorxiv_only")
        include_authors = author_config.get("include", [])
        exclude_authors = author_config.get("exclude", [])

        # 如果模式是biorxiv_only且来源不是biorxiv，则不进行作者过滤
        if mode == "biorxiv_only" and source != "biorxiv":
            return articles

        filtered = []
        for article in articles:
            article_authors = article.get("authors", [])
            if not article_authors:
                # 如果文章没有作者信息，根据模式决定是否保留
                if mode == "all" and exclude_authors:
                    # all模式下，如果有排除列表且文章无作者，保留
                    filtered.append(article)
                continue

            # 检查是否包含排除的作者
            if exclude_authors:
                excluded = False
                for excl_author in exclude_authors:
                    for article_author in article_authors:
                        if self._author_names_match(excl_author, article_author):
                            excluded = True
                            break
                    if excluded:
                        break
                if excluded:
                    continue

            # 检查是否包含指定的作者
            if include_authors:
                author_match = False
                for incl_author in include_authors:
                    for article_author in article_authors:
                        if self._author_names_match(incl_author, article_author):
                            author_match = True
                            break
                    if author_match:
                        break
                if not author_match:
                    continue

            filtered.append(article)

        return filtered

    def filter_with_ai(self, articles: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """
        使用AI过滤文章

        Args:
            articles: 各期刊的文章字典

        Returns:
            Dict[str, List[Dict]]: 过滤后的文章字典
        """
        ai_config = self.config.get("ai_filtering", {})
        if not ai_config.get("enabled", False):
            logger.info("AI过滤已禁用")
            return articles

        logger.info("🤖 开始AI过滤...")

        # 收集所有文章
        all_articles = []
        for journal_articles in articles.values():
            all_articles.extend(journal_articles)

        # 应用最大检索上限
        max_articles = ai_config.get("max_articles_for_filtering", 0)
        original_count = len(all_articles)
        if max_articles > 0 and len(all_articles) > max_articles:
            logger.info(f"📊 检索到 {original_count} 篇文章，应用最大检索上限 {max_articles} 篇")
            all_articles = all_articles[:max_articles]
            logger.info(f"✓ 已限制为前 {max_articles} 篇文章进行AI过滤")
        else:
            logger.info(f"📊 检索到 {original_count} 篇文章，全部进行AI过滤")

        # AI过滤
        filtered_articles = filter_articles_with_ai(all_articles, self.config)

        # 重新组织结果按期刊分组
        filtered_results = {}
        for article in filtered_articles:
            journal = article.get('journal', 'Unknown')
            if journal not in filtered_results:
                filtered_results[journal] = []
            filtered_results[journal].append(article)

        logger.info(f"✅ AI过滤完成，剩余 {sum(len(articles) for articles in filtered_results.values())} 篇文章")
        return filtered_results

    def push_to_feishu(self, original_results: Dict[str, List[Dict]],
                      filtered_results: Dict[str, List[Dict]], days: int = 7) -> bool:
        """
        推送结果到飞书

        Args:
            original_results: 原始搜索结果
            filtered_results: AI过滤后的结果
            days: 搜索天数

        Returns:
            bool: 推送是否成功
        """
        feishu_config = self.config.get("feishu", {})
        if not feishu_config.get("enabled", False):
            logger.info("飞书推送已禁用")
            return True

        logger.info("📨 开始飞书推送...")

        # 将字典结果转换为扁平的列表
        filtered_articles_list = []
        for journal, articles in filtered_results.items():
            filtered_articles_list.extend(articles)

        # 推送
        success = push_to_feishu(original_results, filtered_articles_list, days, self.config)

        if success:
            logger.info("✅ 飞书推送成功")
        else:
            logger.error("❌ 飞书推送失败")

        return success

    def save_results(self, results: Dict[str, List[Dict]], days: int = 7) -> str:
        """
        保存结果到文件

        Args:
            results: 搜索结果
            days: 搜索天数

        Returns:
            str: 保存的文件路径
        """
        filename_format = self.config["output"]["filename_format"]
        output_file = filename_format.format(days=days)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 结果已保存到 {output_file}")
        except Exception as e:
            logger.error(f"❌ 保存结果失败: {e}")
            raise

        return output_file

    def run_complete_workflow(self, days: int = 7) -> Dict[str, List[Dict]]:
        """
        运行完整工作流程：搜索 -> AI过滤 -> 飞书推送 -> 保存结果

        Args:
            days: 搜索最近几天

        Returns:
            Dict[str, List[Dict]]: 最终的过滤结果
        """
        # 搜索
        results = self.search_articles(days=days)

        # AI过滤
        filtered_results = self.filter_with_ai(results)

        # 飞书推送
        self.push_to_feishu(results, filtered_results, days)

        # 保存结果
        self.save_results(filtered_results, days)

        return filtered_results