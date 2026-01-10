-- 小红书发布记录表
-- 用于存储通过 RedInk + VibeSurf 发布到小红书的帖子记录

CREATE TABLE IF NOT EXISTS xiaohongshu_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 关联到生成记录（可选，如果有历史记录功能）
  project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

  -- 发布内容
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tags JSONB DEFAULT '[]'::jsonb,
  images JSONB DEFAULT '[]'::jsonb,  -- [{url, index}]

  -- 发布状态
  status VARCHAR(50) DEFAULT 'draft',  -- draft, publishing, published, failed
  post_url TEXT,  -- 发布后的小红书链接
  error TEXT,     -- 失败时的错误信息

  -- 时间戳
  published_at TIMESTAMPTZ,  -- 实际发布时间
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_posts_status ON xiaohongshu_posts(status);
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_posts_created_at ON xiaohongshu_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_xiaohongshu_posts_project_id ON xiaohongshu_posts(project_id);

-- 添加更新时间自动更新触发器
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

-- 添加 RLS (Row Level Security) 策略
ALTER TABLE xiaohongshu_posts ENABLE ROW LEVEL SECURITY;

-- 允许所有认证用户读取和写入
CREATE POLICY "Allow all operations for authenticated users" ON xiaohongshu_posts
  FOR ALL
  USING (true)
  WITH CHECK (true);

COMMENT ON TABLE xiaohongshu_posts IS '小红书发布记录表 - 存储通过 RedInk 自动发布的帖子';
COMMENT ON COLUMN xiaohongshu_posts.status IS '发布状态: draft-草稿, publishing-发布中, published-已发布, failed-失败';
COMMENT ON COLUMN xiaohongshu_posts.images IS 'JSON 数组，包含图片 URL 和顺序索引';
COMMENT ON COLUMN xiaohongshu_posts.tags IS 'JSON 数组，包含标签字符串';
