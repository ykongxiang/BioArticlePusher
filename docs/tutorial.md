# Bioinformatics Pusher 使用教程

本文档将详细介绍如何使用 Bioinformatics Pusher 系统进行生物信息学文章的智能搜索、过滤和推送。

## 📖 目录

- [快速开始](#快速开始)
- [配置详解](#配置详解)
- [命令行使用](#命令行使用)
- [Python API](#python-api)
- [AI过滤机制](#ai过滤机制)
- [作者过滤](#作者过滤)
- [飞书推送](#飞书推送)
- [故障排除](#故障排除)
- [高级配置](#高级配置)

## 🚀 快速开始

### 1. 环境准备

确保您的系统已安装 Python 3.8+：

```bash
python --version
# 应该显示 Python 3.8.0 或更高版本
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 获取API密钥

#### Kimi AI API密钥

1. 访问 [Kimi AI 官网](https://kimi.moonshot.cn/)
2. 注册账号并登录
3. 在控制台获取 API Key

#### 飞书 Webhook URL

1. 打开飞书，创建一个自定义机器人
2. 配置机器人权限（发送消息权限）
3. 获取 Webhook URL

### 4. 配置系统

创建配置文件：

```bash
# 复制模板
cp secrets.yaml.template secrets.yaml

# 编辑敏感信息
vim secrets.yaml
```

```yaml
ai:
  kimi:
    api_key: "sk-你的Kimi_API密钥"
    base_url: "https://api.moonshot.cn/v1"

feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook地址"
```

### 5. 首次运行

```bash
# 运行完整流程
bioarticle-pusher

# 查看帮助
bioarticle-pusher --help
```

## ⚙️ 配置详解

### 搜索配置

```yaml
search_config:
  days: 7                    # 搜索最近7天的文章
  max_results_per_journal: 20 # 每个期刊最多返回20篇文章
```

### 期刊配置

```yaml
journals:
  pubmed_journals:
    - Nature Biotechnology
    - Nature Methods
    - Genome Biology
    - PLOS Computational Biology

  biorxiv:
    enabled: true
    subjects:
      - bioinformatics
      - computational_biology
      - genomics
```

### 关键词配置

```yaml
keywords:
  any:                      # 任意匹配以下关键词之一
    - bioinformatics
    - computational biology
    - machine learning
    - deep learning

  all: []                   # 必须同时包含所有关键词（留空表示无要求）
```

### 作者过滤配置

```yaml
authors:
  mode: "biorxiv_only"      # 过滤模式：biorxiv_only 或 all
  include:                  # 只保留包含这些作者的文章
    - "Fabian Theis"
    - "David Baker"
  exclude: []               # 排除包含这些作者的文章
```

### AI过滤配置

```yaml
ai_filtering:
  enabled: true
  demo_mode: false          # 设为true可以测试而无需API密钥
  max_articles_for_filtering: 100  # 最大检索上限，控制交给AI过滤的文章数量（0表示无限制）

  model:
    provider: "kimi"
    name: "kimi-k2-0905-preview"
    temperature: 0.1
    max_tokens: 1000
```

**最大检索上限说明：**
- 当检索到的文章数量超过此上限时，只对前N篇文章进行AI过滤
- 可以有效控制AI过滤的处理时间，避免处理过多文章导致脚本运行时间过长
- 设置为 `0` 表示无限制，处理所有检索到的文章
- 设置为较小的值（如 `10`）可以快速测试功能
- 日志中会显示是否应用了限制，例如：`📊 检索到 209 篇文章，应用最大检索上限 10 篇`

## 💻 命令行使用

### 基本用法

```bash
# 搜索最近7天的文章（默认）
bioarticle-pusher

# 搜索最近3天的文章
bioarticle-pusher --days 3

# 只搜索，不推送结果
bioarticle-pusher --no-push --days 1

# 使用自定义配置文件
bioarticle-pusher --config my_config.yaml --secrets my_secrets.yaml
```

### 推送已保存的结果

```bash
# 推送之前保存的结果
bioarticle-pusher --push-saved search_results_7days.json
```

### 查看所有选项

```bash
bioarticle-pusher --help
```

## 🐍 Python API

### 基本使用

```python
from bioinformatics_pusher import ArticleSearcher

# 初始化
searcher = ArticleSearcher()

# 搜索文章
results = searcher.search_articles(days=7)
print(f"找到 {sum(len(articles) for articles in results.values())} 篇文章")

# AI过滤
filtered = searcher.filter_with_ai(results)
print(f"AI过滤后剩余 {sum(len(articles) for articles in filtered.values())} 篇文章")

# 推送结果
success = searcher.push_to_feishu(results, filtered, days=7)

# 保存结果
output_file = searcher.save_results(filtered, days=7)
```

### 自定义配置

```python
# 使用自定义配置文件
searcher = ArticleSearcher(
    config_file="custom_config.yaml",
    secrets_file="custom_secrets.yaml"
)

# 运行完整工作流程
final_results = searcher.run_complete_workflow(days=3)
```

### 处理结果

```python
# 遍历结果
for journal, articles in results.items():
    print(f"{journal}: {len(articles)} 篇文章")
    for article in articles[:3]:  # 只显示前3篇
        print(f"  - {article['title'][:50]}...")
        print(f"    作者: {', '.join(article['authors'][:2])}")
        print(f"    发布时间: {article['published']}")
```

## 🤖 AI过滤机制

### 工作原理

系统使用 Kimi AI 模型对每篇文章进行评估，判断其是否属于以下生物学应用领域：

1. 基因型到表型预测
2. 生命周期模拟
3. 细胞周期调控
4. 单细胞多组学分析
5. scATAC-seq
6. scRNA-seq
7. 染色质可及性分析
8. 基因调控网络建模
9. 增强子-基因连接
10. 染色质潜力分析
11. GWAS变异富集分析
12. eQTL分析
13. 代谢组学分析
14. 蛋白质组学分析
15. 计算代谢组学
16. 计算蛋白质组学
17. 虚拟细胞建模
18. 衰老生物学
19. 基础模型应用

### 评估标准

每篇文章获得0-10分的评分，评分标准：
- **8-10分**: 高度相关，直接 addresses 核心应用领域
- **5-7分**: 中等相关，间接相关或部分相关
- **0-4分**: 低相关，不属于指定领域

只有评分≥5的文章会被保留。

### 演示模式

如果没有API密钥，可以启用演示模式：

```yaml
ai_filtering:
  demo_mode: true  # 无需API密钥，直接使用预定义规则
```

### 语言设置

系统支持中文和英文两种语言，可以分别设置AI描述语言和推送消息语言。

**AI描述语言设置：**

在 `ai_filtering` 中设置 `language` 参数，影响AI生成的description字段的语言：

```yaml
ai_filtering:
  language: "en"  # "zh" 中文（默认）或 "en" 英文
```

**推送消息语言设置：**

在 `feishu.push_config` 中设置 `language` 参数，影响推送消息的标签语言：

```yaml
feishu:
  push_config:
    language: "en"  # "zh" 中文（默认）或 "en" 英文
```

**使用示例：**

设置AI描述为英文，推送消息为中文：
```yaml
ai_filtering:
  language: "en"  # AI描述使用英文

feishu:
  push_config:
    language: "zh"  # 推送标签使用中文
```

设置全部为英文：
```yaml
ai_filtering:
  language: "en"

feishu:
  push_config:
    language: "en"
```

**语言设置的影响：**

- **AI描述语言** (`ai_filtering.language`)：
  - 影响AI生成的 `description` 字段的语言
  - 需要在提示词中使用 `{language}` 占位符
  - 示例：`"Brief description in {language} of main work..."`

- **推送消息语言** (`feishu.push_config.language`)：
  - 影响推送消息中的标签语言（如"期刊"→"Journal"、"作者"→"Authors"）
  - 影响标题和统计信息的语言
  - 不影响文章标题和摘要（保持原文）

### AI模型配置

系统支持多种AI提供商，并且**代码会自动适配新的AI提供商**，只要该提供商支持OpenAI兼容的API格式。

#### 基本配置

```yaml
ai_filtering:
  enabled: true              # 是否启用AI过滤
  demo_mode: false          # 演示模式，无需API key
  max_articles_for_filtering: 100  # 最大检索上限，控制交给AI过滤的文章数量（0表示无限制）
  model:
    provider: "kimi"        # 模型提供商
    name: "kimi-k2-0905-preview"  # 模型名称
    api_key: "${secrets.ai.kimi.api_key}"  # API密钥
    base_url: "https://api.moonshot.cn/v1"  # API基础URL
    temperature: 0.1        # 温度参数（0.0-1.0）
    max_tokens: 1000        # 最大生成token数
  prompt: |                 # AI过滤提示词
    Evaluate this article...
```

**最大检索上限 (`max_articles_for_filtering`)：**
- **作用**：当检索到的文章数量超过此上限时，只对前N篇文章进行AI过滤
- **默认值**：100
- **设置为 0**：无限制，处理所有检索到的文章
- **使用场景**：
  - 快速测试：设置为 `10` 可以快速验证功能
  - 控制处理时间：设置为 `50` 可以限制AI过滤的处理时间
  - 大量文章：当检索到数百篇文章时，可以设置合理的上限避免处理时间过长
- **日志提示**：系统会在日志中显示是否应用了限制，例如：
  - `📊 检索到 209 篇文章，应用最大检索上限 10 篇`
  - `✓ 已限制为前 10 篇文章进行AI过滤`

#### 支持的AI提供商

**1. Kimi (Moonshot)**

```yaml
ai_filtering:
  model:
    provider: "kimi"
    name: "kimi-k2-0905-preview"
    api_key: "${secrets.ai.kimi.api_key}"
    base_url: "https://api.moonshot.cn/v1"
```

在 `secrets.yaml` 中配置：
```yaml
ai:
  kimi:
    api_key: "YOUR_KIMI_API_KEY"
    base_url: "https://api.moonshot.cn/v1"
```

**2. DeepSeek**

```yaml
ai_filtering:
  model:
    provider: "deepseek"
    name: "deepseek-chat"
    api_key: "${secrets.ai.deepseek.api_key}"
    base_url: "https://api.deepseek.com"
```

在 `secrets.yaml` 中配置：
```yaml
ai:
  deepseek:
    api_key: "YOUR_DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com"
```

**3. OpenAI**

```yaml
ai_filtering:
  model:
    provider: "openai"
    name: "gpt-4"
    api_key: "${secrets.ai.openai.api_key}"
    base_url: "https://api.openai.com/v1"
```

在 `secrets.yaml` 中配置：
```yaml
ai:
  openai:
    api_key: "YOUR_OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"
```

#### 添加新的AI提供商（无需修改代码）

系统使用**通用API调用方法**，自动适配所有支持OpenAI兼容API格式的AI提供商。这意味着：

✅ **无需修改代码** - 只需在配置文件中指定新的提供商即可

✅ **自动适配** - 系统会自动使用通用API调用方法

**使用步骤：**

1. 在 `secrets.yaml` 中添加新提供商的配置：
```yaml
ai:
  your_provider:  # 例如：claude, gemini, qwen等
    api_key: "YOUR_API_KEY"
    base_url: "https://api.yourprovider.com/v1"
```

2. 在 `article_search_config.yaml` 中配置：
```yaml
ai_filtering:
  model:
    provider: "your_provider"  # 使用新的提供商名称
    name: "your-model-name"    # 模型名称
    api_key: "${secrets.ai.your_provider.api_key}"
    base_url: "${secrets.ai.your_provider.base_url}"
    temperature: 0.1
    max_tokens: 1000
```

3. 完成！系统会自动使用新提供商。

**API格式要求：**

新AI提供商必须满足以下条件：

- ✅ 支持 `/chat/completions` 端点
- ✅ 使用 `Bearer` token认证（`Authorization: Bearer {api_key}`）
- ✅ 请求格式与OpenAI兼容：
  ```json
  {
    "model": "model-name",
    "messages": [{"role": "user", "content": "prompt"}],
    "temperature": 0.1,
    "max_tokens": 1000,
    "response_format": {"type": "json_object"}
  }
  ```
- ✅ 响应格式包含 `choices[0].message.content` 字段
- ✅ 响应内容为有效的JSON格式

**支持的AI提供商示例：**

以下提供商通常都支持OpenAI兼容的API格式，可以直接使用：

- ✅ **Claude (Anthropic)** - 如果提供OpenAI兼容接口
- ✅ **Gemini (Google)** - 如果提供OpenAI兼容接口
- ✅ **Qwen (阿里云)** - 如果提供OpenAI兼容接口
- ✅ **通义千问** - 如果提供OpenAI兼容接口
- ✅ **文心一言** - 如果提供OpenAI兼容接口
- ✅ **任何支持OpenAI API格式的提供商**

**注意事项：**

- 如果API不支持 `response_format: {"type": "json_object"}`，系统仍会尝试解析响应，但需要在提示词中明确要求返回JSON格式
- 如果API的响应格式不同，可能需要修改代码（但大多数现代AI API都兼容OpenAI格式）
- `demo_mode` 模式可用于测试，无需真实的API密钥
- 建议先在演示模式下测试配置，确认无误后再使用真实API

## 👥 作者过滤

### 过滤模式

- **`biorxiv_only`**: 仅对BioRxiv文章进行作者过滤
- **`all`**: 对所有来源（PubMed和BioRxiv）的文章进行作者过滤

### 配置示例

```yaml
authors:
  mode: "biorxiv_only"
  include:
    - "Fabian Theis"    # 匹配 "Fabian Theis" 或 "Fabian J. Theis"
    - "David Baker"
    - "Aviv Regev"
  exclude: []           # 排除的作者列表
```

### 匹配规则

- 支持部分匹配（如 "Fabian Theis" 匹配 "Fabian J. Theis"）
- 不区分大小写
- 多个作者用逗号分隔

## 📱 飞书推送

### 推送内容

每次推送包含：
- 搜索统计信息
- 筛选后的文章列表
- 文章标题、作者、摘要
- AI评估结果（可选）

### 推送配置

```yaml
feishu:
  enabled: true
  push_config:
    max_articles_per_push: 10    # 每次最多推送10篇文章
    include_abstract: true       # 是否包含摘要
    abstract_max_length: 200     # 摘要最大长度
    include_ai_evaluation: true  # 是否包含AI评估结果
```

### 自定义推送模板

可以通过修改配置来自定义推送消息格式。

## 🔧 故障排除

### 常见问题

#### 1. API密钥错误

```
错误: API key未设置
```

**解决方法**:
- 检查 `secrets.yaml` 文件是否存在
- 确认API密钥格式正确
- 验证API密钥有效性

#### 2. 网络连接问题

```
错误: 请求超时
```

**解决方法**:
- 检查网络连接
- 确认API服务可用
- 适当增加超时时间

#### 3. 配置文件不存在

```
错误: 配置文件不存在
```

**解决方法**:
- 确认配置文件路径正确
- 从模板创建配置文件
- 检查文件权限

#### 4. 飞书推送失败

```
错误: 飞书推送失败
```

**解决方法**:
- 验证Webhook URL正确性
- 检查机器人权限设置
- 确认网络连接正常

### 日志调试

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 然后运行搜索器
```

### 性能优化

- **减少搜索天数**：减少 `search_config.days` 值以加快速度
- **启用演示模式**：设置 `ai_filtering.demo_mode: true` 跳过AI调用
- **调整最大结果数限制**：减少 `search_config.max_results_per_journal` 值
- **设置AI过滤上限**：使用 `ai_filtering.max_articles_for_filtering` 限制处理文章数量
  - 例如：设置为 `50` 时，即使检索到200篇文章，也只会对前50篇进行AI过滤
  - 可以有效控制处理时间，避免脚本运行时间过长

## ⚡ 高级配置

### 自定义AI提示词

```yaml
ai_filtering:
  prompt: |
    自定义AI评估提示词...
```

### 批量处理

```python
# 处理多个时间段
for days in [1, 3, 7]:
    results = searcher.run_complete_workflow(days=days)
    print(f"{days}天: {len(results)} 篇文章")
```

### 结果分析

```python
# 统计各期刊文章数
journal_stats = {}
for journal, articles in results.items():
    journal_stats[journal] = len(articles)

# 统计AI评分分布
score_distribution = {}
for articles in results.values():
    for article in articles:
        score = article.get('ai_evaluation', {}).get('score', 0)
        score_distribution[score] = score_distribution.get(score, 0) + 1
```

### 定时任务

使用 cron 或其他调度器设置定期运行：

```bash
# 每天早上8点运行
0 8 * * * cd /path/to/bioinformatics-pusher && bioarticle-pusher --days 1
```

## 📞 获取帮助

- 📖 [完整文档](README.md)
- 🐛 [报告问题](https://github.com/your-repo/bioinformatics-pusher/issues)
- 💬 [讨论区](https://github.com/your-repo/bioinformatics-pusher/discussions)

---

**享受智能化的生物信息学文献管理！** 🎉