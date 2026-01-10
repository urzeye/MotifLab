#!/usr/bin/env python3
"""
运行 Supabase 数据库迁移

使用方式:
  python run_migration.py

需要设置环境变量 SUPABASE_DB_URL 或使用默认的项目配置
"""

import os
import sys

# Supabase 项目配置
SUPABASE_PROJECT_REF = "cnwgxcvsunbxclgkykln"
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", "")

# 数据库连接字符串（需要数据库密码）
# 格式: postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
DB_URL = os.getenv(
    "SUPABASE_DB_URL",
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{SUPABASE_DB_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
)


def run_migration():
    """执行迁移"""
    # 读取 SQL 文件
    migration_file = os.path.join(os.path.dirname(__file__), "create_xiaohongshu_posts.sql")

    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    print("=" * 50)
    print("渲染AI Supabase 数据库迁移")
    print("=" * 50)

    if not SUPABASE_DB_PASSWORD:
        print("\n⚠️  未设置 SUPABASE_DB_PASSWORD 环境变量")
        print("\n请选择以下方式之一执行迁移：")
        print("\n方式 1: 设置环境变量后运行此脚本")
        print("  export SUPABASE_DB_PASSWORD='your-password'")
        print("  python run_migration.py")
        print("\n方式 2: 在 Supabase Dashboard 中手动执行")
        print("  1. 访问 https://supabase.com/dashboard/project/cnwgxcvsunbxclgkykln/sql/new")
        print("  2. 复制以下 SQL 并执行：")
        print("\n" + "-" * 50)
        print(sql)
        print("-" * 50)
        return False

    try:
        import psycopg2

        print(f"\n连接到数据库...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True

        with conn.cursor() as cur:
            print("执行迁移 SQL...")
            cur.execute(sql)

        conn.close()
        print("\n✅ 迁移成功！xiaohongshu_posts 表已创建")
        return True

    except ImportError:
        print("\n❌ 需要安装 psycopg2:")
        print("  pip install psycopg2-binary")
        print("\n或者在 Supabase Dashboard 中手动执行 SQL")
        return False

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
