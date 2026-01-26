#!/bin/bash

echo "=================================="
echo "Daily Summary Agent 安装脚本"
echo "=================================="

# 安装 arxiv 库
echo "正在安装 arxiv 库..."
pip install --user arxiv

# 检查是否有 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp env.example .env
    echo "请编辑 .env 文件，配置您的 API 密钥和参数"
else
    echo ".env 文件已存在"
fi

echo ""
echo "=================================="
echo "安装完成！"
echo "=================================="
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，配置 DEEPSEEK_API_KEY（如需生成总结）"
echo "2. 运行: python main.py"
echo ""
echo "配置说明："
echo "- ENABLE_ARXIV=true  # 启用 arXiv 爬取"
echo "- ARXIV_CATEGORIES=cs.AI,cs.CV,cs.LG,cs.CL  # arXiv 分类"
echo "- KEYWORDS=大模型,AI,人工智能,计算机视觉,后训练,强化学习,多模态"
echo ""
