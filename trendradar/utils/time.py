# coding=utf-8
"""
时间工具模块

本模块提供统一的时间处理函数，所有时区相关操作都应使用 DEFAULT_TIMEZONE 常量。
"""

from datetime import datetime
from typing import Optional, Tuple

import pytz

# 默认时区常量 - 仅作为 fallback，正常运行时使用 config.yaml 中的 app.timezone
DEFAULT_TIMEZONE = "Asia/Shanghai"


def get_configured_time(timezone: str = DEFAULT_TIMEZONE) -> datetime:
    """
    获取配置时区的当前时间

    Args:
        timezone: 时区名称，如 'Asia/Shanghai', 'America/Los_Angeles'

    Returns:
        带时区信息的当前时间
    """
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        print(f"[警告] 未知时区 '{timezone}'，使用默认时区 {DEFAULT_TIMEZONE}")
        tz = pytz.timezone(DEFAULT_TIMEZONE)
    return datetime.now(tz)


def format_date_folder(
    date: Optional[str] = None, timezone: str = DEFAULT_TIMEZONE
) -> str:
    """
    格式化日期文件夹名 (ISO 格式: YYYY-MM-DD)

    Args:
        date: 指定日期字符串，为 None 则使用当前日期
        timezone: 时区名称

    Returns:
        格式化后的日期字符串，如 '2025-12-09'
    """
    if date:
        return date
    return get_configured_time(timezone).strftime("%Y-%m-%d")


def format_time_filename(timezone: str = DEFAULT_TIMEZONE) -> str:
    """
    格式化时间文件名 (格式: HH-MM，用于文件名)

    Windows 系统不支持冒号作为文件名，因此使用连字符

    Args:
        timezone: 时区名称

    Returns:
        格式化后的时间字符串，如 '15-30'
    """
    return get_configured_time(timezone).strftime("%H-%M")


def get_current_time_display(timezone: str = DEFAULT_TIMEZONE) -> str:
    """
    获取当前时间显示 (格式: HH:MM，用于显示)

    Args:
        timezone: 时区名称

    Returns:
        格式化后的时间字符串，如 '15:30'
    """
    return get_configured_time(timezone).strftime("%H:%M")


def convert_time_for_display(time_str: str) -> str:
    """
    将 HH-MM 格式转换为 HH:MM 格式用于显示

    Args:
        time_str: 输入时间字符串，如 '15-30'

    Returns:
        转换后的时间字符串，如 '15:30'
    """
    if time_str and "-" in time_str and len(time_str) == 5:
        return time_str.replace("-", ":")
    return time_str


def format_iso_time_friendly(
    iso_time: str,
    timezone: str = DEFAULT_TIMEZONE,
    include_date: bool = True,
) -> str:
    """
    将 ISO 格式时间转换为用户时区的友好显示格式

    Args:
        iso_time: ISO 格式时间字符串，如 '2025-12-29T00:20:00' 或 '2025-12-29T00:20:00+00:00'
        timezone: 目标时区名称
        include_date: 是否包含日期部分

    Returns:
        友好格式的时间字符串，如 '12-29 08:20' 或 '08:20'
    """
    if not iso_time:
        return ""

    try:
        # 尝试解析各种 ISO 格式
        dt = None

        # 尝试解析带时区的格式
        if "+" in iso_time or iso_time.endswith("Z"):
            iso_time = iso_time.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso_time)
            except ValueError:
                pass

        # 尝试解析不带时区的格式（假设为 UTC）
        if dt is None:
            try:
                # 处理 T 分隔符
                if "T" in iso_time:
                    dt = datetime.fromisoformat(iso_time.replace("T", " ").split(".")[0])
                else:
                    dt = datetime.fromisoformat(iso_time.split(".")[0])
                # 假设为 UTC 时间
                dt = pytz.UTC.localize(dt)
            except ValueError:
                pass

        if dt is None:
            # 无法解析，返回原始字符串的简化版本
            if "T" in iso_time:
                parts = iso_time.split("T")
                if len(parts) == 2:
                    date_part = parts[0][5:]  # MM-DD
                    time_part = parts[1][:5]  # HH:MM
                    return f"{date_part} {time_part}" if include_date else time_part
            return iso_time

        # 转换到目标时区
        try:
            target_tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            target_tz = pytz.timezone(DEFAULT_TIMEZONE)

        dt_local = dt.astimezone(target_tz)

        # 格式化输出
        if include_date:
            return dt_local.strftime("%m-%d %H:%M")
        else:
            return dt_local.strftime("%H:%M")

    except Exception:
        # 出错时返回原始字符串的简化版本
        if "T" in iso_time:
            parts = iso_time.split("T")
            if len(parts) == 2:
                date_part = parts[0][5:]  # MM-DD
                time_part = parts[1][:5]  # HH:MM
                return f"{date_part} {time_part}" if include_date else time_part
        return iso_time


def is_within_days(
    iso_time: str,
    max_days: int,
    timezone: str = DEFAULT_TIMEZONE,
) -> bool:
    """
    检查 ISO 格式时间是否在指定天数内

    用于 RSS 文章新鲜度过滤，判断文章发布时间是否超过指定天数。

    Args:
        iso_time: ISO 格式时间字符串（如 '2025-12-29T00:20:00' 或带时区）
        max_days: 最大天数（文章发布时间距今不超过此天数则返回 True）
            - max_days > 0: 正常过滤，保留 N 天内的文章
            - max_days <= 0: 禁用过滤，保留所有文章
        timezone: 时区名称（用于获取当前时间）

    Returns:
        True 如果时间在指定天数内（应保留），False 如果超过指定天数（应过滤）
        如果无法解析时间，返回 True（保留文章）
    """
    # 无时间戳或禁用过滤时，保留文章
    if not iso_time:
        return True
    if max_days <= 0:
        return True  # max_days=0 表示禁用过滤

    try:
        dt = None

        # 尝试解析带时区的格式
        if "+" in iso_time or iso_time.endswith("Z"):
            iso_time_normalized = iso_time.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso_time_normalized)
            except ValueError:
                pass

        # 尝试解析不带时区的格式（假设为 UTC）
        if dt is None:
            try:
                if "T" in iso_time:
                    dt = datetime.fromisoformat(iso_time.replace("T", " ").split(".")[0])
                else:
                    dt = datetime.fromisoformat(iso_time.split(".")[0])
                dt = pytz.UTC.localize(dt)
            except ValueError:
                pass

        if dt is None:
            # 无法解析时间，保留文章
            return True

        # 获取当前时间（配置的时区，带时区信息）
        now = get_configured_time(timezone)

        # 计算时间差（两个带时区的 datetime 相减会自动处理时区差异）
        diff = now - dt
        days_diff = diff.total_seconds() / (24 * 60 * 60)

        return days_diff <= max_days

    except Exception:
        # 出错时保留文章
        return True


def calculate_days_old(iso_time: str, timezone: str = DEFAULT_TIMEZONE) -> Optional[float]:
    """
    计算 ISO 格式时间距今多少天

    Args:
        iso_time: ISO 格式时间字符串
        timezone: 时区名称

    Returns:
        距今天数（浮点数），如果无法解析返回 None
    """
    if not iso_time:
        return None

    try:
        dt = None

        # 尝试解析带时区的格式
        if "+" in iso_time or iso_time.endswith("Z"):
            iso_time_normalized = iso_time.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(iso_time_normalized)
            except ValueError:
                pass

        # 尝试解析不带时区的格式（假设为 UTC）
        if dt is None:
            try:
                if "T" in iso_time:
                    dt = datetime.fromisoformat(iso_time.replace("T", " ").split(".")[0])
                else:
                    dt = datetime.fromisoformat(iso_time.split(".")[0])
                dt = pytz.UTC.localize(dt)
            except ValueError:
                pass

        if dt is None:
            return None

        now = get_configured_time(timezone)
        diff = now - dt
        return diff.total_seconds() / (24 * 60 * 60)

    except Exception:
        return None


class TimeWindowChecker:
    """
    时间窗口检查器

    统一管理时间窗口控制逻辑，支持：
    - 推送窗口控制 (push_window)
    - AI 分析窗口控制 (analysis_window)
    - once_per_day 功能
    """

    def __init__(
        self,
        storage_backend,
        get_time_func=None,
        window_name: str = "时间窗口",
    ):
        """
        初始化时间窗口检查器

        Args:
            storage_backend: 存储后端实例
            get_time_func: 获取当前时间的函数
            window_name: 窗口名称（用于日志输出）
        """
        self.storage_backend = storage_backend
        self.get_time_func = get_time_func or (lambda: get_configured_time(DEFAULT_TIMEZONE))
        self.window_name = window_name

    def is_in_time_range(self, start_time: str, end_time: str) -> bool:
        """
        检查当前时间是否在指定时间范围内

        支持跨日时间窗口，例如：
        - 正常窗口：09:00-21:00（当天 9 点到 21 点）
        - 跨日窗口：22:00-02:00（当天 22 点到次日 2 点）

        Args:
            start_time: 开始时间（格式：HH:MM）
            end_time: 结束时间（格式：HH:MM）

        Returns:
            是否在时间范围内
        """
        now = self.get_time_func()
        current_time = now.strftime("%H:%M")

        normalized_start = self._normalize_time(start_time)
        normalized_end = self._normalize_time(end_time)
        normalized_current = self._normalize_time(current_time)

        # 判断是否跨日窗口（start > end 表示跨日，如 22:00-02:00）
        if normalized_start <= normalized_end:
            # 正常窗口：09:00-21:00
            result = normalized_start <= normalized_current <= normalized_end
        else:
            # 跨日窗口：22:00-02:00
            # 当前时间 >= 开始时间（如 23:00 >= 22:00）或 当前时间 <= 结束时间（如 01:00 <= 02:00）
            result = normalized_current >= normalized_start or normalized_current <= normalized_end

        if not result:
            print(f"[{self.window_name}] 当前 {normalized_current}，窗口 {normalized_start}-{normalized_end}")

        return result

    def _normalize_time(self, time_str: str) -> str:
        """将时间字符串标准化为 HH:MM 格式"""
        try:
            parts = time_str.strip().split(":")
            if len(parts) != 2:
                raise ValueError(f"时间格式错误: {time_str}")

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError(f"时间范围错误: {time_str}")

            return f"{hour:02d}:{minute:02d}"
        except Exception as e:
            print(f"[{self.window_name}] 时间格式化错误 '{time_str}': {e}")
            return time_str

    def check_window(
        self,
        window_config: dict,
        check_once_per_day_func=None,
        record_func=None,
    ) -> Tuple[bool, str]:
        """
        统一的时间窗口检查逻辑

        Args:
            window_config: 窗口配置字典，包含：
                - ENABLED: 是否启用窗口控制
                - TIME_RANGE: {"START": "HH:MM", "END": "HH:MM"}
                - ONCE_PER_DAY: 是否每天只执行一次
            check_once_per_day_func: 检查今天是否已执行的函数
            record_func: 记录执行的函数（成功后调用）

        Returns:
            (should_proceed, reason) 元组：
            - should_proceed: 是否应该继续执行
            - reason: 原因说明
        """
        if not window_config.get("ENABLED", False):
            return True, "窗口控制未启用"

        time_range = window_config.get("TIME_RANGE", {})
        start_time = time_range.get("START", "00:00")
        end_time = time_range.get("END", "23:59")

        # 检查时间范围
        if not self.is_in_time_range(start_time, end_time):
            now = self.get_time_func()
            return False, f"当前时间 {now.strftime('%H:%M')} 不在窗口 {start_time}-{end_time} 内"

        # 检查 once_per_day
        if window_config.get("ONCE_PER_DAY", False) and check_once_per_day_func:
            if check_once_per_day_func():
                return False, "今天已执行过"
            else:
                print(f"[{self.window_name}] 今天首次执行")

        return True, "在窗口内"

    def get_status(self, window_config: dict, check_once_per_day_func=None) -> dict:
        """
        获取窗口状态信息

        Args:
            window_config: 窗口配置
            check_once_per_day_func: 检查今天是否已执行的函数

        Returns:
            状态信息字典
        """
        now = self.get_time_func()
        status = {
            "enabled": window_config.get("ENABLED", False),
            "current_time": now.strftime("%H:%M:%S"),
            "current_date": now.strftime("%Y-%m-%d"),
            "timezone": str(now.tzinfo),
        }

        if status["enabled"]:
            time_range = window_config.get("TIME_RANGE", {})
            status["window_start"] = time_range.get("START", "00:00")
            status["window_end"] = time_range.get("END", "23:59")
            status["in_window"] = self.is_in_time_range(
                status["window_start"], status["window_end"]
            )
            status["once_per_day"] = window_config.get("ONCE_PER_DAY", False)

            if status["once_per_day"] and check_once_per_day_func:
                status["executed_today"] = check_once_per_day_func()

        return status
