-- ============================================================
-- API 中转站比价平台 - 数据库 Schema V2
-- aiclubin.com
-- ============================================================

-- 1. 中转站基本信息表
CREATE TABLE IF NOT EXISTS providers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,                          -- 站名
  url text NOT NULL UNIQUE,                    -- 站点 URL
  logo_url text,                               -- Logo URL
  description text,                            -- 简介
  status text DEFAULT 'active',                -- active / inactive / closed / suspicious
  is_verified boolean DEFAULT false,           -- 是否经过验证
  risk_level text DEFAULT 'untested',          -- untested / A / B / C / D
  avg_multiplier numeric,                      -- 平均倍率（官方价格的倍数）
  model_count int DEFAULT 0,                   -- 支持模型数量
  avg_rating numeric DEFAULT 0,                -- 用户平均评分 (1-5)
  rating_count int DEFAULT 0,                  -- 评价数量
  last_detected_at timestamptz,               -- 最近一次检测时间
  notes text,                                  -- 备注
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- 2. 中转站支持的模型及定价
CREATE TABLE IF NOT EXISTS provider_models (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  model_name text NOT NULL,                    -- 模型名 (如 gpt-4o, claude-3.5-sonnet)
  multiplier numeric,                          -- 倍率 (1.0 = 官方原价)
  price_per_1k_input numeric,                  -- 输入价格 (每1K tokens, 美元)
  price_per_1k_output numeric,                 -- 输出价格 (每1K tokens, 美元)
  is_available boolean DEFAULT true,           -- 当前是否可用
  detected_at timestamptz,                     -- 检测到的时间
  created_at timestamptz DEFAULT now()
);

-- 3. 用户评价
CREATE TABLE IF NOT EXISTS provider_ratings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  rating int NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment text,
  usage_context text,                          -- 使用场景描述
  ip_hash text,                                -- IP 哈希（防刷，不存原始 IP）
  created_at timestamptz DEFAULT now()
);

-- 4. 检测结果历史
CREATE TABLE IF NOT EXISTS detection_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  endpoint_url text NOT NULL,
  claimed_model text NOT NULL,
  detected_model text,
  fraud_index int,                             -- 诈骗指数 0-100
  perf_grade text,                             -- 性能等级 S/A/B/C
  agent_grade text,                            -- Agent 兼容等级 A-F
  probe_details jsonb,                         -- 各探针详细结果
  is_fraud boolean,
  created_at timestamptz DEFAULT now()
);

-- 5. AI 生成的文章/评测
CREATE TABLE IF NOT EXISTS articles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  slug text NOT NULL UNIQUE,                   -- URL 友好的标识符
  content text NOT NULL,                       -- 文章内容 (Markdown)
  summary text,                                -- 摘要
  category text DEFAULT 'review',              -- review / report / guide / news
  cover_image text,                            -- 封面图 URL
  provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  is_published boolean DEFAULT false,
  published_at timestamptz,
  view_count int DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_providers_status ON providers(status);
CREATE INDEX IF NOT EXISTS idx_providers_risk ON providers(risk_level);
CREATE INDEX IF NOT EXISTS idx_provider_models_provider ON provider_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_provider_models_model ON provider_models(model_name);
CREATE INDEX IF NOT EXISTS idx_provider_ratings_provider ON provider_ratings(provider_id);
CREATE INDEX IF NOT EXISTS idx_detection_results_provider ON detection_results(provider_id);
CREATE INDEX IF NOT EXISTS idx_detection_results_created ON detection_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(is_published, published_at DESC);

-- ============================================================
-- Row Level Security
-- ============================================================
ALTER TABLE providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE detection_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

-- 公开读取
CREATE POLICY "Public read providers" ON providers FOR SELECT USING (true);
CREATE POLICY "Public read provider_models" ON provider_models FOR SELECT USING (true);
CREATE POLICY "Public read provider_ratings" ON provider_ratings FOR SELECT USING (true);
CREATE POLICY "Public read detection_results" ON detection_results FOR SELECT USING (true);
CREATE POLICY "Public read articles" ON articles FOR SELECT USING (is_published = true);

-- 匿名提交评价
CREATE POLICY "Public insert ratings" ON provider_ratings FOR INSERT WITH CHECK (true);

-- 匿名提交检测日志
CREATE POLICY "Public insert detection" ON detection_results FOR INSERT WITH CHECK (true);

-- ============================================================
-- 种子数据: 20 家主流中转站
-- ============================================================
INSERT INTO providers (name, url, description, status, risk_level, notes) VALUES
  ('OhMyGPT', 'https://api.ohmygpt.com', '老牌中转站，支持模型较全', 'active', 'untested', '运营时间较长'),
  ('API2D', 'https://api2d.net', '国内知名中转，价格适中', 'active', 'untested', '支持支付宝'),
  ('New API', 'https://newapi.pro', '开源 New API 模板站代表', 'active', 'untested', '基于开源项目'),
  ('CloseAI', 'https://console.closeai-asia.com', '面向亚洲用户的 API 中转', 'active', 'untested', ''),
  ('AI Hub', 'https://api.ai-hubs.com', '支持多种模型的 API 中转', 'active', 'untested', ''),
  ('GPT API', 'https://gptapi.us', '主打 GPT 系列中转', 'active', 'untested', ''),
  ('API Flash', 'https://api2flash.com', '轻量级 API 中转服务', 'active', 'untested', ''),
  ('CheapGPT', 'https://cheapgpt.tw', '主打低价的 API 中转', 'active', 'untested', ''),
  ('OpenAI Proxy', 'https://openai-proxy.com', '专注 OpenAI 模型代理', 'active', 'untested', ''),
  ('AI Proxy', 'https://aiproxy.io', '多模型 API 代理服务', 'active', 'untested', ''),
  ('Token Hub', 'https://tokenhub.com', 'Token 交易与中转', 'active', 'untested', ''),
  ('GPT Shop', 'https://gptshop.io', 'GPT 系列 API 中转', 'active', 'untested', ''),
  ('OneAPI', 'https://oneapi.pro', '基于 One API 开源系统', 'active', 'untested', ''),
  ('AI Gateway', 'https://aigateway.cn', '国内 API 网关服务', 'active', 'untested', ''),
  ('CloudGPT', 'https://cloudgpt.dev', '云端 API 中转服务', 'active', 'untested', ''),
  ('FastGPT', 'https://fastgpt.run', '国内 API 加速服务', 'active', 'untested', ''),
  ('API Market', 'https://apimarket.xyz', 'API 聚合市场', 'active', 'untested', ''),
  ('SmartProxy', 'https://smartproxy.ai', '智能 API 代理', 'active', 'untested', ''),
  ('NinjaAPI', 'https://ninjaapi.com', '高性能 API 中转', 'active', 'untested', ''),
  ('TokenAPI', 'https://tokenapi.net', 'Token API 中转服务', 'active', 'untested', '');

-- ============================================================
-- 触发器: 自动更新 updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER providers_updated_at
  BEFORE UPDATE ON providers
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER articles_updated_at
  BEFORE UPDATE ON articles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
