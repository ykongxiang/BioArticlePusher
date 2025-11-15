#!/bin/bash

# 文章搜索与定时任务管理脚本（整合版）
# 用法: 
#   ./article_pusher.sh              - 执行文章搜索
#   ./article_pusher.sh setup-cron   - 快速设置每天3点的cron任务
#   ./article_pusher.sh manage       - 进入cron任务管理菜单

# ========== 自定义配置 ==========
# Conda 环境名称
CONDA_ENV_NAME="bioinfopusher"

# 配置文件路径
YAML_PATH="article_search_config.yaml"
SECRET_PATH="root/secret.yaml"

# 调试模式（通过环境变量 DEBUG=1 启用）
DEBUG=${DEBUG:-0}
# ================================

# 初始化
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
SEARCH_SCRIPT="$SCRIPT_DIR/article_pusher.sh"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/bioinfo_search_$(date +%Y%m%d).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ========== 文章搜索功能 ==========
run_search() {
    mkdir -p "$LOG_DIR"
    
    # 调试输出函数
    debug_log() {
        [ "$DEBUG" -eq 1 ] && echo "[DEBUG] $1" >> "$LOG_FILE" && [ -t 0 ] && echo "[DEBUG] $1"
    }
    
    # 日志记录
    echo "=========================================" >> "$LOG_FILE"
    echo "开始执行文章搜索 - $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    [ "$DEBUG" -eq 1 ] && echo "调试模式: 已启用" >> "$LOG_FILE"
    echo "=========================================" >> "$LOG_FILE"
    
    # 调试信息
    debug_log "脚本目录: $SCRIPT_DIR"
    debug_log "工作目录: $(pwd)"
    debug_log "用户: $(whoami)"
    
    # 检查配置文件
    if [ ! -f "$YAML_PATH" ]; then
        echo "错误: 配置文件 $YAML_PATH 不存在" >> "$LOG_FILE"
        exit 1
    fi
    debug_log "配置文件: $YAML_PATH"
    
    # 初始化 conda
    debug_log "初始化 conda..."
    CONDA_PATHS=(
        "/root/anaconda3/etc/profile.d/conda.sh"
        "$HOME/anaconda3/etc/profile.d/conda.sh"
        "$HOME/miniconda3/etc/profile.d/conda.sh"
        "/opt/conda/etc/profile.d/conda.sh"
        "/usr/local/anaconda3/etc/profile.d/conda.sh"
    )
    
    for conda_path in "${CONDA_PATHS[@]}"; do
        if [ -f "$conda_path" ]; then
            debug_log "找到 conda: $conda_path"
            source "$conda_path"
            break
        fi
    done
    
    # 如果未找到，尝试通过 which 查找
    if ! command -v conda &> /dev/null; then
        CONDA_BIN=$(which conda 2>/dev/null)
        if [ -n "$CONDA_BIN" ]; then
            CONDA_BASE=$(dirname $(dirname "$CONDA_BIN"))
            [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ] && source "$CONDA_BASE/etc/profile.d/conda.sh"
        fi
    fi
    
    # 激活 conda 环境
    if command -v conda &> /dev/null; then
        debug_log "conda 版本: $(conda --version 2>&1)"
        echo "激活 conda 环境: $CONDA_ENV_NAME" >> "$LOG_FILE"
        conda activate "$CONDA_ENV_NAME" 2>> "$LOG_FILE"
        if [ $? -ne 0 ]; then
            echo "错误: 无法激活 conda 环境 $CONDA_ENV_NAME" >> "$LOG_FILE"
            debug_log "可用环境: $(conda env list 2>&1)"
            exit 1
        fi
        echo "✓ Conda 环境已激活" >> "$LOG_FILE"
        echo "Python 路径: $(which python)" >> "$LOG_FILE"
        debug_log "Python 版本: $(python --version 2>&1)"
    else
        echo "警告: 未找到 conda 命令，将使用系统默认 Python" >> "$LOG_FILE"
    fi
    
    # 执行文章搜索
    debug_log "准备执行搜索..."
    echo "配置文件: $YAML_PATH" >> "$LOG_FILE"
    echo "Conda 环境: $CONDA_ENV_NAME" >> "$LOG_FILE"
    echo "执行搜索逻辑..." >> "$LOG_FILE"
    
    # ========== 在此处添加实际的搜索命令 ==========
    # 示例: python "$SCRIPT_DIR/article_search.py" --config "$YAML_PATH" >> "$LOG_FILE" 2>&1
    # EXIT_CODE=$?
    # ================================================
    
    EXIT_CODE=0  # 临时占位，添加实际命令后删除此行
    
    # 完成
    debug_log "执行完成，退出代码: $EXIT_CODE"
    echo "=========================================" >> "$LOG_FILE"
    echo "文章搜索完成 - $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    [ "$DEBUG" -eq 1 ] && debug_log "调试摘要: 目录=$SCRIPT_DIR, 环境=$CONDA_ENV_NAME, 退出=$EXIT_CODE"
    echo "=========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
    
    exit $EXIT_CODE
}

# ========== Cron 任务管理功能 ==========
# 验证 cron 表达式
validate_cron() {
    local cron_expr="$1"
    local minute hour day month weekday
    read -r minute hour day month weekday <<< "$cron_expr"
    
    local part_count=$(echo "$cron_expr" | awk '{print NF}')
    if [ "$part_count" -ne 5 ] || [ -z "$minute" ] || [ -z "$hour" ] || [ -z "$day" ] || [ -z "$month" ] || [ -z "$weekday" ]; then
        echo -e "${RED}错误: cron 表达式必须包含5个部分（分钟 小时 日 月 星期）${NC}"
        return 1
    fi
    
    [[ "$minute" =~ ^[0-9]+$ ]] && ([ "$minute" -lt 0 ] || [ "$minute" -gt 59 ]) && { echo -e "${RED}错误: 分钟值必须在 0-59 之间${NC}"; return 1; }
    [[ "$hour" =~ ^[0-9]+$ ]] && ([ "$hour" -lt 0 ] || [ "$hour" -gt 23 ]) && { echo -e "${RED}错误: 小时值必须在 0-23 之间${NC}"; return 1; }
    [[ "$day" =~ ^[0-9]+$ ]] && ([ "$day" -lt 1 ] || [ "$day" -gt 31 ]) && { echo -e "${RED}错误: 日期值必须在 1-31 之间${NC}"; return 1; }
    [[ "$month" =~ ^[0-9]+$ ]] && ([ "$month" -lt 1 ] || [ "$month" -gt 12 ]) && { echo -e "${RED}错误: 月份值必须在 1-12 之间${NC}"; return 1; }
    [[ "$weekday" =~ ^[0-9]+$ ]] && ([ "$weekday" -lt 0 ] || [ "$weekday" -gt 7 ]) && { echo -e "${RED}错误: 星期值必须在 0-7 之间${NC}"; return 1; }
    
    return 0
}

# 查看 cron 任务
view_cron() {
    echo ""
    echo "当前所有 cron 任务:"
    echo "----------------------------------------"
    if crontab -l 2>/dev/null | grep -q "$SEARCH_SCRIPT"; then
        crontab -l | grep "$SEARCH_SCRIPT"
        echo -e "\n${GREEN}✓ 文章搜索任务已设置${NC}"
    else
        echo -e "${YELLOW}未找到文章搜索的 cron 任务${NC}"
    fi
    echo ""
    crontab -l 2>/dev/null
}

# 设置 cron 任务
set_cron() {
    echo ""
    echo "设置执行时间"
    echo "----------------------------------------"
    echo "常用示例: 0 3 * * * (每天3点) | 0 18 * * * (每天18点) | 0 */6 * * * (每6小时)"
    echo "格式: 分钟 小时 日 月 星期"
    echo -n "请输入 cron 表达式: "
    read CRON_TIME
    
    [ -z "$CRON_TIME" ] && { echo -e "${RED}错误: 时间表达式不能为空${NC}"; return; }
    validate_cron "$CRON_TIME" || return
    
    CRON_JOB="$CRON_TIME $SEARCH_SCRIPT"
    TEMP_CRON=$(mktemp)
    crontab -l 2>/dev/null > "$TEMP_CRON"
    grep -v "$SEARCH_SCRIPT" "$TEMP_CRON" > "${TEMP_CRON}.new" 2>/dev/null
    mv "${TEMP_CRON}.new" "$TEMP_CRON" 2>/dev/null
    echo "$CRON_JOB" >> "$TEMP_CRON"
    
    if ! crontab "$TEMP_CRON" 2>/dev/null; then
        echo -e "\n${RED}✗ Cron 任务设置失败！语法错误${NC}"
        crontab "$TEMP_CRON" 2>&1 | head -2
        rm -f "$TEMP_CRON"
        return
    fi
    
    crontab -l 2>/dev/null | grep -q "$SEARCH_SCRIPT" || {
        echo -e "\n${RED}✗ 任务未能成功添加${NC}"
        rm -f "$TEMP_CRON"
        return
    }
    
    rm -f "$TEMP_CRON"
    echo -e "\n${GREEN}✓ Cron 任务已成功设置${NC}"
    echo "执行时间: $CRON_TIME"
    echo "完整任务: $CRON_JOB"
    echo ""
    crontab -l
}

# 删除 cron 任务
remove_cron() {
    if crontab -l 2>/dev/null | grep -q "$SEARCH_SCRIPT"; then
        echo -n "确认删除文章搜索的 cron 任务? (y/n): "
        read -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && crontab -l 2>/dev/null | grep -v "$SEARCH_SCRIPT" | crontab - && echo -e "${GREEN}✓ Cron 任务已删除${NC}" || echo "操作已取消"
    else
        echo -e "${YELLOW}未找到文章搜索的 cron 任务${NC}"
    fi
}

# 测试执行脚本
test_script() {
    echo "执行: $SEARCH_SCRIPT"
    bash "$SEARCH_SCRIPT"
    [ $? -eq 0 ] && echo -e "\n${GREEN}✓ 脚本执行完成${NC}" || echo -e "\n${RED}✗ 脚本执行失败${NC}"
}

# 查看日志
view_logs() {
    [ ! -d "$LOG_DIR" ] && { echo -e "${YELLOW}日志目录不存在${NC}"; return; }
    
    echo "日志文件列表:"
    ls -lht "$LOG_DIR" | head -10
    echo -n "是否查看最新的日志文件? (y/n): "
    read -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] && {
        LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
        [ -n "$LATEST_LOG" ] && { echo "最新日志: $LATEST_LOG"; tail -50 "$LATEST_LOG"; } || echo -e "${YELLOW}未找到日志文件${NC}"
    }
}

# 快速设置 cron（每天3点）
setup_cron() {
    chmod +x "$SEARCH_SCRIPT"
    CRON_JOB="0 3 * * * $SEARCH_SCRIPT"
    
    if crontab -l 2>/dev/null | grep -q "$SEARCH_SCRIPT"; then
        echo "警告: 已存在相同的 cron 任务"
        crontab -l | grep "$SEARCH_SCRIPT"
        echo ""
        read -p "是否要删除旧任务并添加新任务? (y/n): " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] && {
            crontab -l 2>/dev/null | grep -v "$SEARCH_SCRIPT" | crontab -
            (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
            echo "✓ Cron 任务已更新"
        } || { echo "操作已取消"; exit 0; }
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✓ Cron 任务已添加"
    fi
    
    echo ""
    echo "当前所有 cron 任务:"
    crontab -l
    echo ""
    echo "任务说明: 每天凌晨3点自动执行文章搜索"
    echo "日志文件位置: $LOG_DIR/"
}

# 管理菜单
manage_cron() {
    show_menu() {
        echo ""
        echo "========================================="
        echo "  文章搜索 Cron 任务管理"
        echo "========================================="
        echo "1. 查看当前 cron 任务"
        echo "2. 设置新的执行时间"
        echo "3. 删除 cron 任务"
        echo "4. 测试执行脚本（立即运行）"
        echo "5. 查看日志文件"
        echo "6. 退出"
        echo "========================================="
        echo -n "请选择操作 [1-6]: "
    }
    
    while true; do
        show_menu
        read choice
        case $choice in
            1) view_cron ;;
            2) set_cron ;;
            3) remove_cron ;;
            4) test_script ;;
            5) view_logs ;;
            6) echo "退出"; exit 0 ;;
            *) echo -e "${RED}无效选择，请重新输入${NC}" ;;
        esac
    done
}

# ========== 主程序入口 ==========
case "${1:-run}" in
    run|"")
        run_search
        ;;
    setup-cron|setup)
        setup_cron
        ;;
    manage|m)
        manage_cron
        ;;
    help|--help|-h)
        echo "文章搜索与定时任务管理脚本"
        echo ""
        echo "用法:"
        echo "  $0              - 执行文章搜索"
        echo "  $0 setup-cron   - 快速设置每天3点的cron任务"
        echo "  $0 manage       - 进入cron任务管理菜单"
        echo "  $0 help         - 显示此帮助信息"
        echo ""
        echo "环境变量:"
        echo "  DEBUG=1         - 启用调试模式"
        ;;
    *)
        echo -e "${RED}错误: 未知参数 '$1'${NC}"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac

