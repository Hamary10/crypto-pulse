import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_DATABASE_PATH = "crypto_pulse.db"
DEFAULT_REPORTS_DIR = "reports"


def _now() -> datetime:
    return datetime.now()


def _database_path(database_path: Optional[str] = None) -> Path:
    return Path(database_path or os.getenv("DATABASE_PATH") or DEFAULT_DATABASE_PATH)


def _report_path(reports_dir: str, now: datetime) -> Path:
    return Path(reports_dir) / f"daily_report_{now.strftime('%Y%m%d')}.md"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _scalar(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0] or 0) if row else 0


def _rows(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
    return list(conn.execute(sql, params).fetchall())


def _today_bounds(now: datetime) -> Tuple[str, str]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def _last_24h_start(now: datetime) -> str:
    return (now - timedelta(hours=24)).isoformat(timespec="seconds")


def _table_missing_text(table_name: str) -> str:
    return f"表 `{table_name}` 不存在，暂无法统计。"


def _format_top_commands(rows: Iterable[sqlite3.Row]) -> List[str]:
    lines = ["| 排名 | 命令 | 次数 |", "|---|---|---|"]
    count = 0
    for count, row in enumerate(rows, start=1):
        lines.append(f"| {count} | {row['command']} | {row['total']} |")
    if count == 0:
        lines.append("| - | 暂无数据 | 0 |")
    return lines


def _format_top_coins(rows: Iterable[sqlite3.Row]) -> List[str]:
    lines = ["| 排名 | 币种 | Symbol | 查询次数 |", "|---|---|---|---|"]
    count = 0
    for count, row in enumerate(rows, start=1):
        lines.append(
            f"| {count} | {row['coin_id'] or 'N/A'} | {(row['symbol'] or 'N/A').upper()} | {row['query_count']} |"
        )
    if count == 0:
        lines.append("| - | 暂无数据 | - | 0 |")
    return lines


def _build_missing_database_report(path: Path, now: datetime) -> str:
    return "\n".join(
        [
            "# Crypto Pulse 运营观察报告",
            "",
            f"生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 数据库状态",
            "",
            f"未找到数据库文件：`{path}`。",
            "",
            "请确认 `DATABASE_PATH` 环境变量或默认 `crypto_pulse.db` 是否存在。",
            "",
            "## 隐私说明",
            "",
            "本报告只显示统计数据，不显示 Telegram 用户 ID、用户名、first_name 或 last_name。",
        ]
    )


def _build_report_from_database(path: Path, now: datetime) -> str:
    start_today, end_today = _today_bounds(now)
    last_24h = _last_24h_start(now)

    lines = [
        "# Crypto Pulse 运营观察报告",
        "",
        f"生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"数据库文件：`{path}`",
        "",
        "## 用户概览",
        "",
    ]

    conn = _connect(path)
    try:
        has_users = _table_exists(conn, "users")
        has_command_logs = _table_exists(conn, "command_logs")
        has_coin_query_stats = _table_exists(conn, "coin_query_stats")
        has_error_logs = _table_exists(conn, "error_logs")

        if has_users:
            total_users = _scalar(conn, "SELECT COUNT(*) FROM users")
            today_new_users = _scalar(
                conn,
                "SELECT COUNT(*) FROM users WHERE first_seen_at >= ? AND first_seen_at < ?",
                (start_today, end_today),
            )
            lines.extend(
                [
                    f"- 总用户数：{total_users}",
                    f"- 今日新增用户数：{today_new_users}",
                ]
            )
        else:
            lines.append(f"- {_table_missing_text('users')}")

        if has_command_logs:
            active_users = _scalar(
                conn,
                """
                SELECT COUNT(DISTINCT telegram_id)
                FROM command_logs
                WHERE created_at >= ? AND created_at < ? AND telegram_id IS NOT NULL
                """,
                (start_today, end_today),
            )
            today_commands = _scalar(
                conn,
                "SELECT COUNT(*) FROM command_logs WHERE created_at >= ? AND created_at < ?",
                (start_today, end_today),
            )
            lines.extend(
                [
                    f"- 今日活跃用户数：{active_users}",
                    f"- 今日命令调用总数：{today_commands}",
                ]
            )
        else:
            lines.append(f"- {_table_missing_text('command_logs')}")

        lines.extend(["", "## 命令使用", "", "### 最常用命令 TOP10", ""])
        if has_command_logs:
            top_commands = _rows(
                conn,
                """
                SELECT command, COUNT(*) AS total
                FROM command_logs
                GROUP BY command
                ORDER BY total DESC, command ASC
                LIMIT 10
                """,
            )
            lines.extend(_format_top_commands(top_commands))
        else:
            lines.append(_table_missing_text("command_logs"))

        lines.extend(["", "## 币种关注", "", "### 最常查询币种 TOP10", ""])
        if has_coin_query_stats:
            top_coins = _rows(
                conn,
                """
                SELECT coin_id, symbol, query_count
                FROM coin_query_stats
                ORDER BY query_count DESC, coin_id ASC
                LIMIT 10
                """,
            )
            lines.extend(_format_top_coins(top_coins))
        else:
            lines.append(_table_missing_text("coin_query_stats"))

        lines.extend(["", "## 错误观察", ""])
        if has_error_logs:
            error_count = _scalar(
                conn,
                "SELECT COUNT(*) FROM error_logs WHERE created_at >= ?",
                (last_24h,),
            )
            lines.append(f"- 最近 24 小时错误数量：{error_count}")
        else:
            lines.append("- 最近 24 小时错误数量：当前暂无错误日志表，暂无法统计。")
    finally:
        conn.close()

    lines.extend(
        [
            "",
            "## 隐私说明",
            "",
            "本报告只显示统计数据，不显示 Telegram 用户 ID、用户名、first_name 或 last_name。",
        ]
    )
    return "\n".join(lines)


def generate_report(
    database_path: Optional[str] = None,
    reports_dir: str = DEFAULT_REPORTS_DIR,
    now: Optional[datetime] = None,
) -> Path:
    current_time = now or _now()
    db_path = _database_path(database_path)
    output_path = _report_path(reports_dir, current_time)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        report = _build_missing_database_report(db_path, current_time)
    else:
        report = _build_report_from_database(db_path, current_time)

    output_path.write_text(report, encoding="utf-8")
    return output_path


def main() -> None:
    output_path = generate_report()
    print(f"运营观察报告已生成：{output_path}")


if __name__ == "__main__":
    main()
