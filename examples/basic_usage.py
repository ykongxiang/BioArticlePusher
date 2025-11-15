#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BioArticlePusher 使用示例

演示如何使用BioArticlePusher进行文章搜索、AI过滤和飞书推送
"""

from pusher import ArticleSearcher


def basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 初始化搜索器
    searcher = ArticleSearcher()
    
    # 搜索最近7天的文章
    print("搜索最近7天的文章...")
    results = searcher.search_articles(days=7)
    
    total = sum(len(articles) for articles in results.values())
    print(f"共找到 {total} 篇文章")
    
    # AI过滤
    print("\nAI过滤中...")
    filtered_results = searcher.filter_with_ai(results)
    
    filtered_count = sum(len(articles) for articles in filtered_results.values())
    print(f"AI过滤后剩余 {filtered_count} 篇文章")
    
    # 保存结果
    output_file = searcher.save_results(filtered_results, days=7)
    print(f"结果已保存到: {output_file}")
    
    # 推送到飞书（可选）
    # searcher.push_to_feishu(results, filtered_results, days=7)


def custom_config():
    """使用自定义配置"""
    print("\n=== 使用自定义配置 ===")
    
    # 使用自定义配置文件
    searcher = ArticleSearcher(
        config_file="my_config.yaml",
        secrets_file="my_secrets.yaml"
    )
    
    # 运行完整工作流程
    final_results = searcher.run_complete_workflow(days=3)
    
    print(f"完整流程完成，共 {sum(len(articles) for articles in final_results.values())} 篇文章")


def advanced_usage():
    """高级使用示例"""
    print("\n=== 高级使用示例 ===")
    
    searcher = ArticleSearcher()
    
    # 只搜索特定期刊
    results = searcher.search_articles(days=7)
    
    # 分析结果
    for journal, articles in results.items():
        print(f"\n{journal}: {len(articles)} 篇文章")
        
        for article in articles[:2]:  # 只显示前两篇
            print(f"  - {article['title'][:50]}...")
            print(f"    作者: {', '.join(article['authors'][:2])}")
            
            # 检查AI评估结果
            if 'ai_evaluation' in article:
                ai_eval = article['ai_evaluation']
                print(f"    AI评分: {ai_eval.get('score', 'N/A')}/10")
                print(f"    应用领域: {', '.join(ai_eval.get('application_areas', []))}")


if __name__ == "__main__":
    # 运行基本示例
    basic_usage()
    
    # 取消注释以运行其他示例
    # custom_config()
    # advanced_usage()