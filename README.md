# Daily Summary Agent

一个智能的每日AI/大模型/计算机视觉内容总结Agent系统。

## 功能特性

- 📄 **arXiv论文爬虫**: 自动从arXiv获取最新AI/ML论文
- 🔍 **微信公众号爬虫**: 自动抓取微信公众号文章
- 📚 **Archive爬虫**: 从Archive网站抓取历史文章
- 🔄 **信息整合**: 自动去重、分类、格式化内容
- 🧠 **RAG系统**: 基于向量数据库的检索增强生成
- ✍️ **文档撰写**: 自动生成每日总结报告

## 安装

```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 到 `.env`
2. 填写必要的配置信息（API密钥等）

## 使用

### 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
# 创建 .env 文件并配置（参考 env.example）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# arXiv配置
ENABLE_ARXIV=true
ARXIV_CATEGORIES=cs.AI,cs.CV,cs.LG,cs.CL
ARXIV_MAX_RESULTS=50
ARXIV_DAYS_BACK=7

# 关键词配置
KEYWORDS=大模型,AI,人工智能,计算机视觉,后训练,强化学习,多模态,多模态大模型
```

3. 运行Agent：
```bash
python main.py
```

4. 查看生成的总结：
总结文件保存在 `output/` 目录下，文件名格式为 `daily_summary_YYYYMMDD.md`

### 高级使用

参考 `example_usage.py` 查看更多使用示例。

## 项目结构

```
daily_summary_agent/
├── main.py                 # 主入口
├── run.py                  # 快速启动脚本
├── scheduler.py            # 定时任务调度器
├── config.py              # 配置文件
├── example_usage.py       # 使用示例
├── crawlers/              # 爬虫模块
│   ├── __init__.py
│   ├── base_crawler.py    # 基础爬虫类
│   ├── arxiv_crawler.py   # arXiv论文爬虫
│   ├── wechat_crawler.py  # 微信公众号爬虫
│   └── archive_crawler.py # Archive爬虫
├── processors/            # 数据处理模块
│   ├── __init__.py
│   ├── integrator.py      # 信息整合
│   └── content_filter.py  # 内容过滤
├── rag/                   # RAG模块
│   ├── __init__.py
│   ├── vector_store.py    # 向量数据库
│   └── retriever.py       # 检索器
├── writers/               # 文档撰写模块
│   ├── __init__.py
│   └── summary_writer.py  # 总结撰写
├── utils/                 # 工具函数
│   ├── __init__.py
│   └── logger.py          # 日志工具
├── data/                  # 数据目录（自动创建）
│   └── vector_db/         # 向量数据库
├── logs/                  # 日志目录（自动创建）
└── output/                # 输出目录（自动创建）
```

## 使用方式

### 方式1: 直接运行
```bash
python main.py
```

### 方式2: 使用启动脚本
```bash
# 使用RAG（默认）
python run.py

# 不使用RAG
python run.py --no-rag
```

### 方式3: 定时任务
```bash
# 启动定时任务调度器（每天09:00自动执行）
python scheduler.py
```

## 工作流程

1. **数据爬取**: 从arXiv、微信公众号和Archive网站爬取文章
2. **内容过滤**: 根据关键词过滤无效内容
3. **信息整合**: 去重、分类、格式化
4. **向量化存储**: 将文章内容向量化并存储到向量数据库
5. **RAG检索**: 从向量数据库中检索相关内容
6. **总结生成**: 使用DeepSeek LLM生成结构化的每日总结报告
7. **保存输出**: 将总结保存为Markdown文件

## 注意事项

- 需要配置DeepSeek API密钥（DEEPSEEK_API_KEY）才能生成总结
- arXiv爬虫使用官方API，稳定可靠，支持按关键词和分类搜索
- 微信公众号爬取可能需要特殊处理（RSS订阅或第三方服务）
- Archive网站爬取需要根据具体网站结构调整解析逻辑
- 首次运行会自动下载嵌入模型（可能需要一些时间）

## GitHub Actions 自动运行 + OneDrive 备份

本项目已内置 GitHub Actions 工作流：`.github/workflows/daily_task.yml`，会按计划每天自动运行 `python run_v3.py`，并将产物备份到云盘（推荐 OneDrive）。

### 1) 在 GitHub 上开启自动运行

1. 将仓库推到 GitHub（或 Fork 后使用自己的仓库）
2. 打开仓库的 **Actions**（首次可能需要点一下启用）
3. 配置必要的 Secrets / Variables（参考 `.github/workflows/daily_task.yml` 里的 `env:`）

> 提醒：GitHub Actions 的定时 `cron` 使用 **UTC**。当前配置 `0 0 * * *` 对应新加坡时间 **08:00**。

### 2) 将每日文件备份到 OneDrive（通过 rclone）

工作流会在检测到 `RCLONE_CONFIG`（GitHub Secret）后执行备份：
- `output/` → `CLOUD_BACKUP_REMOTE/output`
- `data/papers/` → `CLOUD_BACKUP_REMOTE/papers`

按下面步骤把 OneDrive “挂载”成 rclone remote：

1. 在你自己的电脑安装 rclone，并创建 OneDrive remote（示例 remote 名称为 `onedrive`）：
```bash
rclone config
```

2. 复制 rclone 配置文件内容（用于放到 GitHub Secret）：
```bash
rclone config file
cat "$(rclone config file)"
```

3. 在 GitHub 仓库里配置：
- **Settings → Secrets and variables → Actions → Secrets**
  - 新增 Secret：`RCLONE_CONFIG`（把上一步的 `rclone.conf` 全文粘贴进去）
- **Settings → Secrets and variables → Actions → Variables**
  - 设置 `CLOUD_BACKUP_REMOTE`，例如：`onedrive:DailySummaryAgent`（也可以放到 Secrets 里，同名即可）
  - 注意：`CLOUD_BACKUP_REMOTE` 必须是 `<remote>:<path>` 形式，例如 `gdrive:DailySummaryAgent`，不能只填文件夹名或路径（比如 `DailySummaryAgent` / `DailySummaryAgent/output`）

之后每天工作流运行完成，产物会自动同步到你的 OneDrive 对应目录下。

## arXiv支持的分类

常用AI/ML相关分类：
- `cs.AI`: Artificial Intelligence
- `cs.CV`: Computer Vision and Pattern Recognition
- `cs.LG`: Machine Learning
- `cs.CL`: Computation and Language (NLP)
- `cs.NE`: Neural and Evolutionary Computing
- `stat.ML`: Machine Learning (Statistics)
