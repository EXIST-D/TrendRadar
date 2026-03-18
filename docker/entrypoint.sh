#!/bin/bash
set -e

# 检查配置文件
if [ ! -f "/app/config/config.yaml" ] || [ ! -f "/app/config/frequency_words.txt" ]; then
    echo "❌ 配置文件缺失"
    exit 1
fi

# 保存环境变量
env >> /etc/environment

case "${RUN_MODE:-cron}" in
"once")
    echo "🔄 单次执行"
    exec /usr/local/bin/python -m trendradar
    ;;
"cron")
    # 生成 crontab
    echo "${CRON_SCHEDULE:-*/30 * * * *} cd /app && /usr/local/bin/python -m trendradar" > /tmp/crontab
    
    echo "📅 生成的crontab内容:"
    cat /tmp/crontab

    if ! /usr/local/bin/supercronic -test /tmp/crontab; then
        echo "❌ crontab格式验证失败"
        exit 1
    fi

    # 立即执行一次（如果配置了）
    if [ "${IMMEDIATE_RUN:-false}" = "true" ]; then
        echo "▶️ 立即执行一次"
        /usr/local/bin/python -m trendradar
    fi

    # 启动 Web 服务器（如果配置了）
    if [ "${ENABLE_WEBSERVER:-false}" = "true" ]; then
        echo "🌐 启动 Web 服务器..."
        /usr/local/bin/python manage.py start_webserver

        WEBSERVER_WATCHDOG_ENABLED=$(echo "${WEBSERVER_WATCHDOG:-true}" | tr '[:upper:]' '[:lower:]')
        WEBSERVER_WATCHDOG_INTERVAL=${WEBSERVER_WATCHDOG_INTERVAL:-60}
        if [ "$WEBSERVER_WATCHDOG_ENABLED" = "true" ] || [ "$WEBSERVER_WATCHDOG_ENABLED" = "1" ] || [ "$WEBSERVER_WATCHDOG_ENABLED" = "yes" ] || [ "$WEBSERVER_WATCHDOG_ENABLED" = "on" ]; then
            # 启动后台 watchdog 定期检查 Web 服务器健康状态
            echo "🔄 启动 Web 服务器 watchdog (间隔: ${WEBSERVER_WATCHDOG_INTERVAL}s)..."
            (
                while true; do
                    sleep "$WEBSERVER_WATCHDOG_INTERVAL"
                    /usr/local/bin/python manage.py webserver_autofix
                done
            ) &
            WEBSERVER_WATCHDOG_PID=$!
            echo "  ✅ watchdog 已启动 (PID: $WEBSERVER_WATCHDOG_PID)"
        else
            echo "⏸️ Web 服务器 watchdog 已禁用"
        fi
    fi

    echo "⏰ 启动supercronic: ${CRON_SCHEDULE:-*/30 * * * *}"
    echo "🎯 supercronic 将作为 PID 1 运行"

    exec /usr/local/bin/supercronic -passthrough-logs /tmp/crontab
    ;;
*)
    exec "$@"
    ;;
esac
