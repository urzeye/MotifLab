-- 历史记录表
-- 用于存储 RenderInk 生成的图文历史记录
--
-- 执行方式：
-- 1. 登录 Supabase Dashboard: https://supabase.com/dashboard
-- 2. 进入项目 -> SQL Editor
-- 3. 复制粘贴此 SQL 并执行

-- 确保 update_updated_at_column 函数存在
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建历史记录表
CREATE TABLE IF NOT EXISTS history_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 基本信息
  title TEXT NOT NULL,
  topic TEXT,
  task_id TEXT UNIQUE,

  -- 大纲数据 (JSONB 格式)
  -- 结构: { "raw": "原始文本", "pages": [{ "content": "...", "index": 0, "type": "cover" }] }
  outline JSONB DEFAULT '{}'::jsonb,

  -- 图片信息 (JSONB 数组)
  -- 结构: ["0.png", "1.png", ...]
  images JSONB DEFAULT '[]'::jsonb,

  -- 缩略图文件名
  thumbnail TEXT,

  -- 状态: draft, generating, partial, completed, error
  status VARCHAR(50) DEFAULT 'draft',

  -- 页面数量
  page_count INTEGER DEFAULT 0,

  -- 时间戳
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_history_records_status ON history_records(status);
CREATE INDEX IF NOT EXISTS idx_history_records_created_at ON history_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_records_task_id ON history_records(task_id);

-- 全文搜索索引 (用于标题搜索)
CREATE INDEX IF NOT EXISTS idx_history_records_title_search
  ON history_records USING gin(to_tsvector('simple', coalesce(title, '')));

-- 更新时间触发器
DROP TRIGGER IF EXISTS update_history_records_updated_at ON history_records;
CREATE TRIGGER update_history_records_updated_at
  BEFORE UPDATE ON history_records
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- RLS 策略
ALTER TABLE history_records ENABLE ROW LEVEL SECURITY;

-- 删除已存在的策略（如果有）
DROP POLICY IF EXISTS "Enable all access for service role" ON history_records;

-- 创建新策略：允许 service role 完全访问
CREATE POLICY "Enable all access for service role" ON history_records
  FOR ALL USING (true) WITH CHECK (true);

-- 输出成功信息
SELECT 'history_records 表创建成功' as message;
