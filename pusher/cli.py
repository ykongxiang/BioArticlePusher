#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
命令行接口
"""

import argparse
import sys
from pathlib import Path

from .search import ArticleSearcher


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="生物文章推送系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 搜索最近7天的文章并推送
  bioinfo-pusher

  # 搜索最近3天的文章
  bioinfo-pusher --days 3

  # 只搜索，不推送
  bioinfo-pusher --no-push

  # 推送已保存的结果
  bioinfo-pusher --push-saved results.json
        """
    )

    parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="搜索最近几天 (默认: 7)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="article_search_config.yaml",
        help="配置文件路径 (默认: article_search_config.yaml)"
    )

    parser.add_argument(
        "--secrets",
        type=str,
        default="secrets.yaml",
        help="敏感信息配置文件路径 (默认: secrets.yaml)"
    )

    parser.add_argument(
        "--no-push",
        action="store_true",
        help="只搜索和过滤，不推送结果"
    )

    parser.add_argument(
        "--push-saved",
        type=str,
        help="推送已保存的结果文件"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="输出文件路径 (默认使用配置文件中的格式)"
    )

    args = parser.parse_args()

    try:
        # 检查配置文件是否存在
        if not Path(args.config).exists():
            print(f"❌ 配置文件不存在: {args.config}")
            print("请创建配置文件或使用 --config 指定正确的路径")
            sys.exit(1)

        # 初始化搜索器
        searcher = ArticleSearcher(args.config, args.secrets)

        if args.push_saved:
            # 推送已保存的结果
            if not Path(args.push_saved).exists():
                print(f"❌ 结果文件不存在: {args.push_saved}")
                sys.exit(1)

            import json
            with open(args.push_saved, 'r', encoding='utf-8') as f:
                saved_results = json.load(f)

            # 推断天数
            days = args.days  # 或者从文件名解析

            # 创建空的原始结果（因为我们只有过滤后的结果）
            original_results = {}

            success = searcher.push_to_feishu(original_results, saved_results, days)
            if success:
                print("✅ 推送完成")
            else:
                print("❌ 推送失败")
                sys.exit(1)

        else:
            # 完整工作流程
            print(f"🚀 开始搜索最近 {args.days} 天的生物文章...")

            # 搜索
            results = searcher.search_articles(days=args.days)
            total_articles = sum(len(articles) for articles in results.values())
            print(f"📊 搜索完成，共找到 {total_articles} 篇文章")

            # AI过滤
            filtered_results = searcher.filter_with_ai(results)
            filtered_count = sum(len(articles) for articles in filtered_results.values())
            print(f"🤖 AI过滤完成，剩余 {filtered_count} 篇文章")

            # 保存结果
            output_file = searcher.save_results(filtered_results, args.days)

            # 推送（除非指定不推送）
            if not args.no_push:
                success = searcher.push_to_feishu(results, filtered_results, args.days)
                if success:
                    print("✅ 飞书推送完成")
                else:
                    print("❌ 飞书推送失败")
                    sys.exit(1)

            print(f"🎉 工作流程完成！结果已保存到: {output_file}")

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()