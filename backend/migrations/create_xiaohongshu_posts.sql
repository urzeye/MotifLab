-- 小红书发布记录表
-- 用于存储通过 渲染AI + VibeSurf 发布到小红书的帖子记录
--
-- 执行方式：
-- 1. 登录 Supabase Dashboard: https://supabase.com/dashboard
-- 2. 进入项目 -> SQL Editor
-- 3. 复制粘贴此 SQL 并执行

CREATE TABLE IF NOT EXISTS xiaohongshu_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 关联到项目（可选）
  project_id UUID,

  -- 发布内容
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tags JSONB DEFAULT '[]'::jsonb,
  images JSONB DEFAULT '[]'::jsonb,

  -- 发布状态: draft, publishing, published, failed
  status VARCHAR(50) DEFAULT 'draft',
  post_url TEXT,
  error TEXT,

  -- 时间戳
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_posts_status ON xiaohongshu_posts(status);
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_posts_created_at ON xiaohongshu_posts(created_at DESC);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_xiaohongshu_posts_updated_at ON xiaohongshu_posts;
CREATE TRIGGER update_xiaohongshu_posts_updated_at
  BEFORE UPDATE ON xiaohongshu_posts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- RLS 策略
ALTER TABLE xiaohongshu_posts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all access for service role" ON xiaohongshu_posts
  FOR ALL USING (true) WITH CHECK (true);
