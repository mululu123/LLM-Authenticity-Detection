-- Migration: Add tier column to providers, update pricing to CNY/1M format
-- Run this in Supabase SQL Editor

-- 1. Add tier column
ALTER TABLE providers ADD COLUMN IF NOT EXISTS tier text DEFAULT 'neutral';
COMMENT ON COLUMN providers.tier IS 'recommended / neutral / not_recommended';

-- 2. Add channel_type and quality to provider_models
ALTER TABLE provider_models ADD COLUMN IF NOT EXISTS channel_type text DEFAULT 'mixed';
ALTER TABLE provider_models ADD COLUMN IF NOT EXISTS quality text DEFAULT 'unknown';
COMMENT ON COLUMN provider_models.channel_type IS 'official / reverse / max_pool / mixed';
COMMENT ON COLUMN provider_models.quality IS 'good / fair / diluted / unknown';

-- 3. Rename pricing columns conceptually (CNY per 1M tokens, not USD per 1K)
-- We'll reuse existing columns but with new semantics
COMMENT ON COLUMN provider_models.price_per_1k_input IS 'Input price in CNY per 1M tokens';
COMMENT ON COLUMN provider_models.price_per_1k_output IS 'Output price in CNY per 1M tokens';
