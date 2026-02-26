#!/usr/bin/env python3
"""
运行 Supabase 数据库迁移

使用方式:
  python run_migration.py

说明:
- 脚本会按文件名顺序执行 backend/migrations 下的所有 .sql 文件
- 建议通过命名约定控制顺序（例如 001_xxx.sql, 002_xxx.sql）
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# Supabase 项目配置
SUPABASE_PROJECT_REF = "cnwgxcvsunbxclgkykln"
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")
EXPLICIT_DB_URL = (os.getenv("SUPABASE_DB_URL") or "").strip()
MIGRATIONS_DIR = Path(__file__).parent

# 数据库连接字符串（需要数据库密码）
# 格式: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
DB_URL = EXPLICIT_DB_URL or (
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{SUPABASE_DB_PASSWORD}"
    "@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
)


def _discover_sql_files() -> List[Path]:
    """按文件名顺序发现迁移 SQL 文件。"""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f for f in files if f.is_file()]


def _load_sql_documents(files: List[Path]) -> List[Tuple[Path, str]]:
    """读取全部 SQL 文件内容。"""
    docs: List[Tuple[Path, str]] = []
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            docs.append((file, f.read()))
    return docs


def _print_manual_sql(docs: List[Tuple[Path, str]]):
    """打印手工执行 SQL 内容。"""
    print("\n方式 2: 在 Supabase Dashboard 中手动执行")
    print("  1. 访问 https://supabase.com/dashboard/project/cnwgxcvsunbxclgkykln/sql/new")
    print("  2. 依次执行以下 SQL 文件内容：")

    for file, sql in docs:
        print("\n" + "-" * 50)
        print(f"-- FILE: {file.name}")
        print("-" * 50)
        print(sql)
        print("-" * 50)


def run_migration():
    """执行迁移"""
    migration_files = _discover_sql_files()
    if not migration_files:
        print("❌ 未找到任何 SQL 迁移文件")
        return False
    docs = _load_sql_documents(migration_files)

    print("=" * 50)
    print("渲染AI Supabase 数据库迁移")
    print("=" * 50)
    print(f"发现 {len(migration_files)} 个 SQL 文件：")
    for file in migration_files:
        print(f"  - {file.name}")

    if not DB_URL or (not EXPLICIT_DB_URL and not SUPABASE_DB_PASSWORD):
        print("\n⚠️  未设置数据库连接信息")
        print("\n请选择以下方式之一执行迁移：")
        print("\n方式 1: 设置环境变量后运行此脚本")
        print("  export SUPABASE_DB_URL='postgresql://...'\n  # 或")
        print("  export SUPABASE_DB_PASSWORD='your-password'")
        print("  python run_migration.py")
        _print_manual_sql(docs)
        return False

    try:
        import psycopg2

        print("\n连接到数据库...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False

        try:
            with conn.cursor() as cur:
                for file, sql in docs:
                    print(f"执行迁移 SQL: {file.name}")
                    cur.execute(sql)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        print("\n✅ 迁移成功！所有 SQL 文件已执行")
        return True

    except ImportError:
        print("\n❌ 需要安装 psycopg2:")
        print("  pip install psycopg2-binary")
        _print_manual_sql(docs)
        return False

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
