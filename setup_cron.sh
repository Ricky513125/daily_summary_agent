#!/bin/bash
# 设置 Linux Crontab 定时任务

echo "=================================="
echo "Daily Summary Agent V3"
echo "Crontab 定时任务配置"
echo "=================================="
echo ""

# 获取当前目录
CURRENT_DIR=$(pwd)
PYTHON_PATH=$(which python)

echo "项目目录: $CURRENT_DIR"
echo "Python路径: $PYTHON_PATH"
echo ""

# 生成crontab配置（每周二至周六10:00运行，抓取前一天的论文）
CRON_CMD="0 10 * * 2-6 cd $CURRENT_DIR && $PYTHON_PATH main_v3.py --days-ago 1 >> logs/cron.log 2>&1"

echo "将添加以下Crontab任务:"
echo "$CRON_CMD"
echo ""

read -p "确认添加？(y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    # 添加到crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Crontab任务已添加"
    echo ""
    echo "查看当前Crontab:"
    crontab -l | grep "main_v3.py"
    echo ""
    echo "说明:"
    echo "- 每周二至周六 10:00 (北京时间) 自动运行"
    echo "- 抓取前一天的论文（此时当天的更新已经完成）"
    echo "- 日志保存在: logs/cron.log"
    echo "- 查看所有任务: crontab -l"
    echo "- 删除任务: crontab -e（然后删除对应行）"
else
    echo "❌ 已取消"
fi

echo ""
echo "=================================="
echo "手动配置方法:"
echo "1. 运行: crontab -e"
echo "2. 添加以下行:"
echo "   0 10 * * 2-6 cd $CURRENT_DIR && $PYTHON_PATH main_v3.py --days-ago 1 >> logs/cron.log 2>&1"
echo "3. 保存退出（:wq）"
echo ""
echo "说明:"
echo "- 2-6 表示周二到周六"
echo "- 10:00 是北京时间上午10点"
echo "- --days-ago 1 表示抓取前一天的论文"
echo "=================================="
