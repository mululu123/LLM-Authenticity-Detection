#!/usr/bin/env node
/**
 * sync-providers.js
 * Fetches hvoy's GitHub README, parses provider data, and syncs to Supabase.
 * Can be run standalone or scheduled via n8n/cron.
 *
 * Usage:
 *   node scripts/sync-providers.js                  # fetch + sync
 *   node scripts/sync-providers.js --dry-run        # parse only, print results
 *   node scripts/sync-providers.js --json-only      # output parsed JSON only
 */

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://ijqizaquvtpphqkysaoi.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const README_URL = 'https://raw.githubusercontent.com/zzsting88/relayAPI/main/README.md';
const README_LOCAL = '/tmp/hvoy-readme.md';

// ─── README Parser ────────────────────────────────────────────

function parseProviders(readme) {
  const providers = [];
  const lines = readme.split('\n');

  let currentTier = 'neutral';
  let currentProvider = null;
  let textBuffer = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Detect tier sections
    if (line.startsWith('## ')) {
      if (line.includes('推荐') && !line.includes('不推荐')) {
        currentTier = 'recommended';
      } else if (line.includes('不推荐')) {
        currentTier = 'not_recommended';
      } else if (line.includes('中性')) {
        currentTier = 'neutral';
      }
      continue;
    }

    // Detect provider sections
    const providerMatch = line.match(/^###\s+\[([^\]]+)\]\(([^)]+)\)/);
    const plainProviderMatch = line.match(/^###\s+(.+)$/);

    if (providerMatch) {
      if (currentProvider) {
        currentProvider.description = buildDescription(textBuffer);
        currentProvider.pricing = extractPricing(textBuffer.join('\n'));
        currentProvider.notes = extractNotes(textBuffer.join('\n'));
        providers.push(currentProvider);
      }

      const name = providerMatch[1];
      const rawUrl = providerMatch[2];
      const url = extractRealUrl(rawUrl);

      currentProvider = { name, url, tier: currentTier };
      textBuffer = [];
    } else if (plainProviderMatch && !providerMatch && !line.startsWith('####')) {
      // Provider without link (like "codesome.ai")
      const name = plainProviderMatch[1].trim();
      if (name.length < 30 && !name.includes('写在前面') && !name.includes('更新')) {
        if (currentProvider) {
          currentProvider.description = buildDescription(textBuffer);
          currentProvider.pricing = extractPricing(textBuffer.join('\n'));
          currentProvider.notes = extractNotes(textBuffer.join('\n'));
          providers.push(currentProvider);
        }
        currentProvider = { name, url: '', tier: currentTier };
        textBuffer = [];
      }
    } else if (currentProvider) {
      textBuffer.push(line);
    }
  }

  // Don't forget the last provider
  if (currentProvider) {
    currentProvider.description = buildDescription(textBuffer);
    currentProvider.pricing = extractPricing(textBuffer.join('\n'));
    currentProvider.notes = extractNotes(textBuffer.join('\n'));
    providers.push(currentProvider);
  }

  return providers;
}

function extractRealUrl(rawUrl) {
  // Decode hvoy redirect URLs
  if (rawUrl.includes('hvoy.ai/relaySite')) {
    try {
      const url = new URL(rawUrl);
      const target = url.searchParams.get('target');
      if (target) return target;
      // No target param - extract domain from name param
      const name = url.searchParams.get('name');
      if (name) {
        const domainHints = {
          'RightCode': 'https://www.right.codes',
          '柏拉图AI': 'https://pltai.com',
          '发现AI': 'https://faxian.ai',
          'ANYONE.ai': 'https://anyone.ai',
          'DawCode': 'https://dawclaudecode.com',
          'AI派': 'https://aipai.ai',
          'SunnyPumpkinAPI': 'https://sunny-pumpkin.com',
        };
        if (domainHints[name]) return domainHints[name];
      }
    } catch {}
  }
  // Strip common affiliate params
  try {
    const url = new URL(rawUrl);
    if (url.searchParams.has('aff') || url.searchParams.has('ref') || url.searchParams.has('inviteCode')) {
      // Keep the base URL with path but strip tracking params
      const clean = `${url.origin}${url.pathname}`;
      return clean.endsWith('/') ? clean.slice(0, -1) : clean;
    }
  } catch {}
  return rawUrl;
}

function buildDescription(lines) {
  // Take first meaningful paragraph (non-empty, non-heading)
  const paras = [];
  let current = [];
  for (const line of lines) {
    if (line.trim() === '') {
      if (current.length > 0) {
        paras.push(current.join(' ').trim());
        current = [];
      }
    } else if (!line.startsWith('#') && !line.startsWith('!') && !line.startsWith('[') && !line.startsWith('~')) {
      current.push(line.trim());
    }
  }
  if (current.length > 0) paras.push(current.join(' ').trim());

  // Return first substantial paragraph
  return paras.find(p => p.length > 10) || '';
}

function extractPricing(text) {
  const prices = [];

  // Pattern 1: "人民币 X(进)Y(出)/一百万Token" or "X(进)Y(出)/一百万Token"
  const priceRegex = /(?:人民币\s*)?(\d+\.?\d*)\(进\)(\d+\.?\d*)\(出\)\/一百万[Tt]oken/g;
  let match;
  while ((match = priceRegex.exec(text)) !== null) {
    const inputPrice = parseFloat(match[1]);
    const outputPrice = parseFloat(match[2]);
    const context = text.substring(Math.max(0, match.index - 80), match.index);
    const model = detectModel(context);

    prices.push({
      model: model || 'unknown',
      input_cny_per_1m: inputPrice,
      output_cny_per_1m: outputPrice,
      channel_type: detectChannelType(context),
      quality: detectQuality(context, text.substring(match.index, match.index + 60))
    });
  }

  // Pattern 2: "X/Y一百万token" (simplified format like "3/15一百万token")
  const simpleRegex = /(\d+\.?\d*)\/(\d+\.?\d*)\s*一百万\s*[Tt]oken/g;
  while ((match = simpleRegex.exec(text)) !== null) {
    const inputPrice = parseFloat(match[1]);
    const outputPrice = parseFloat(match[2]);
    // Check if already captured by pattern 1
    const alreadyCaptured = prices.some(p =>
      Math.abs(p.input_cny_per_1m - inputPrice) < 0.01 &&
      Math.abs(p.output_cny_per_1m - outputPrice) < 0.01
    );
    if (!alreadyCaptured) {
      const context = text.substring(Math.max(0, match.index - 80), match.index);
      const model = detectModel(context);
      prices.push({
        model: model || 'unknown',
        input_cny_per_1m: inputPrice,
        output_cny_per_1m: outputPrice,
        channel_type: detectChannelType(context),
        quality: detectQuality(context, text.substring(match.index, match.index + 60))
      });
    }
  }

  return prices;
}

function detectModel(context) {
  const ctx = context.toLowerCase();
  // Check in reverse order (most specific first)
  if (ctx.includes('opus') && ctx.includes('4.7')) return 'claude-opus-4-7';
  if (ctx.includes('opus') && ctx.includes('4.6')) return 'claude-opus-4-6';
  if (ctx.includes('sonnet') && ctx.includes('4.6')) return 'claude-sonnet-4-6';
  if (ctx.includes('sonnet')) return 'claude-sonnet-4-6';
  if (ctx.includes('opus')) return 'claude-opus-4-6';
  if (ctx.includes('gpt') && ctx.includes('5.6')) return 'gpt-5.6';
  if (ctx.includes('gpt') && ctx.includes('5.5')) return 'gpt-5.5';
  if (ctx.includes('gpt') && ctx.includes('5.4')) return 'gpt-5.4';
  if (ctx.includes('gpt') && ctx.includes('5.3')) return 'gpt-5.3';
  if (ctx.includes('gpt') && ctx.includes('5.2')) return 'gpt-5.2';
  if (ctx.includes('gpt')) return 'gpt-5.4';
  if (ctx.includes('gemini') && ctx.includes('3.1')) return 'gemini-3.1-pro';
  if (ctx.includes('gemini')) return 'gemini-3.1-pro';
  return null;
}

function detectChannelType(context) {
  const ctx = context.toLowerCase();
  if (ctx.includes('官转') || ctx.includes('官方') || ctx.includes('官key')) return 'official';
  if (ctx.includes('逆向') || ctx.includes('反代') || ctx.includes('反重力') || ctx.includes('kiro') || ctx.includes('aws')) return 'reverse';
  if (ctx.includes('max') || ctx.includes('号池') || ctx.includes('拼车')) return 'max_pool';
  if (ctx.includes('质量较好') || ctx.includes('cc-') || ctx.includes('推荐')) return 'official';
  if (ctx.includes('质量一般') || ctx.includes('便宜')) return 'reverse';
  return 'mixed';
}

function detectQuality(context, priceText) {
  const combined = (context + ' ' + priceText).toLowerCase();
  if (combined.includes('不掺水') || combined.includes('没掺水') || combined.includes('质量相当好') || combined.includes('质量很好') || combined.includes('质量好') || combined.includes('质量较好')) return 'good';
  if (combined.includes('掺水') && !combined.includes('不掺水') && !combined.includes('没掺水')) return 'diluted';
  if (combined.includes('质量一般') || combined.includes('质量还行')) return 'fair';
  return 'unknown';
}

function extractNotes(text) {
  const features = [];
  if (text.includes('开发票')) features.push('支持开发票');
  if (text.includes('签到')) features.push('每日签到送额度');
  if (text.includes('注册送') || text.includes('送') && text.includes('额度')) features.push('新用户送额度');
  if (text.includes('包月') || text.includes('月卡') || text.includes('套餐')) features.push('支持月卡');
  if (text.includes('香港') || text.includes('新加坡')) features.push('亚洲节点');
  if (text.includes('QQ群') || text.includes('QQ邮箱')) features.push('有QQ群');
  return features.join('、');
}

// ─── Supabase Sync ────────────────────────────────────────────

async function syncToSupabase(providers) {
  let inserted = 0, updated = 0, modelsInserted = 0;

  for (const p of providers) {
    if (!p.url || p.url.length < 5) {
      console.log(`  ⚠ Skipping ${p.name}: no valid URL`);
      continue;
    }

    // Upsert provider
    const providerData = {
      name: p.name,
      url: p.url,
      description: (p.description || '').substring(0, 500),
      status: p.tier === 'not_recommended' ? 'suspicious' : 'active',
      risk_level: p.tier === 'recommended' ? 'B' : p.tier === 'not_recommended' ? 'D' : 'untested',
      notes: [`[${p.tier === 'recommended' ? '推荐' : p.tier === 'not_recommended' ? '不推荐' : '中性'}]`, p.notes].filter(Boolean).join(' '),
      is_verified: p.tier === 'recommended',
    };

    // Check if provider exists
    const checkRes = await fetch(
      `${SUPABASE_URL}/rest/v1/providers?url=eq.${encodeURIComponent(p.url)}&select=id,name`,
      {
        headers: {
          apikey: SERVICE_ROLE_KEY,
          Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
        },
      }
    );

    let providerId;
    const existing = await checkRes.json();

    if (existing && existing.length > 0) {
      providerId = existing[0].id;
      // Update
      const updRes = await fetch(
        `${SUPABASE_URL}/rest/v1/providers?id=eq.${providerId}`,
        {
          method: 'PATCH',
          headers: {
            apikey: SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal',
          },
          body: JSON.stringify(providerData),
        }
      );
      if (updRes.ok) {
        updated++;
        console.log(`  ✓ Updated: ${p.name}`);
      } else {
        const err = await updRes.text();
        console.error(`  ✗ Update failed for ${p.name}: ${err}`);
        continue;
      }
    } else {
      // Insert
      const insRes = await fetch(`${SUPABASE_URL}/rest/v1/providers`, {
        method: 'POST',
        headers: {
          apikey: SERVICE_ROLE_KEY,
          Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
          'Content-Type': 'application/json',
          Prefer: 'return=representation',
        },
        body: JSON.stringify(providerData),
      });
      if (insRes.ok) {
        const row = await insRes.json();
        providerId = row[0].id;
        inserted++;
        console.log(`  ✓ Inserted: ${p.name}`);
      } else {
        const err = await insRes.text();
        console.error(`  ✗ Insert failed for ${p.name}: ${err}`);
        continue;
      }
    }

    // Sync pricing models
    if (p.pricing && p.pricing.length > 0) {
      // Delete old models for this provider
      await fetch(
        `${SUPABASE_URL}/rest/v1/provider_models?provider_id=eq.${providerId}`,
        {
          method: 'DELETE',
          headers: {
            apikey: SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
            Prefer: 'return=minimal',
          },
        }
      );

      // Insert new models (deduplicate by model name, keep cheapest)
      const modelMap = {};
      for (const price of p.pricing) {
        const key = `${price.model}_${price.channel_type}`;
        if (!modelMap[key] || price.input_cny_per_1m < modelMap[key].input_cny_per_1m) {
          modelMap[key] = price;
        }
      }

      for (const [, price] of Object.entries(modelMap)) {
        const modelData = {
          provider_id: providerId,
          model_name: price.model,
          price_per_1k_input: price.input_cny_per_1m,   // Now stores CNY/1M tokens
          price_per_1k_output: price.output_cny_per_1m,  // Now stores CNY/1M tokens
          multiplier: null,
          is_available: price.quality !== 'diluted',
        };

        const mRes = await fetch(`${SUPABASE_URL}/rest/v1/provider_models`, {
          method: 'POST',
          headers: {
            apikey: SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal',
          },
          body: JSON.stringify(modelData),
        });
        if (mRes.ok) modelsInserted++;
      }
    }
  }

  return { inserted, updated, modelsInserted };
}

// ─── Main ─────────────────────────────────────────────────────

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const jsonOnly = args.includes('--json-only');

  if (!SERVICE_ROLE_KEY && !dryRun && !jsonOnly) {
    console.error('Error: SUPABASE_SERVICE_ROLE_KEY env var required for sync');
    console.error('Usage: SUPABASE_SERVICE_ROLE_KEY=xxx node scripts/sync-providers.js');
    process.exit(1);
  }

  console.log('Fetching README from GitHub...');
  let readme;
  try {
    // Try local cache first, then remote
    const fs = await import('fs');
    if (fs.existsSync(README_LOCAL)) {
      readme = fs.readFileSync(README_LOCAL, 'utf8');
      console.log(`Loaded from local cache: ${readme.length} bytes`);
    } else {
      const res = await fetch(README_URL, {
        headers: { 'User-Agent': 'Mozilla/5.0' },
        redirect: 'follow',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      readme = await res.text();
      console.log(`Fetched ${readme.length} bytes from GitHub`);
      fs.writeFileSync(README_LOCAL, readme);
    }
  } catch (e) {
    console.error('Failed to fetch README:', e.message);
    process.exit(1);
  }

  console.log('Parsing providers...');
  const providers = parseProviders(readme);
  console.log(`Found ${providers.length} providers`);

  // Filter out entries without URLs (incomplete data)
  const validProviders = providers.filter(p => p.url && p.url.length > 5);
  console.log(`Valid providers with URLs: ${validProviders.length}`);

  if (jsonOnly) {
    console.log(JSON.stringify(validProviders, null, 2));
    return;
  }

  // Summary
  const tierCounts = { recommended: 0, neutral: 0, not_recommended: 0 };
  let totalPrices = 0;
  for (const p of validProviders) {
    tierCounts[p.tier] = (tierCounts[p.tier] || 0) + 1;
    totalPrices += (p.pricing || []).length;
  }
  console.log(`\nTiers: ${tierCounts.recommended} recommended, ${tierCounts.neutral} neutral, ${tierCounts.not_recommended} not recommended`);
  console.log(`Total price entries: ${totalPrices}`);

  if (dryRun) {
    console.log('\n--- Dry Run: Provider List ---');
    for (const p of validProviders) {
      console.log(`\n[${p.tier}] ${p.name} - ${p.url}`);
      if (p.description) console.log(`  Desc: ${p.description.substring(0, 100)}...`);
      if (p.pricing?.length) {
        for (const price of p.pricing) {
          console.log(`  ${price.model}: ¥${price.input_cny_per_1m}/${price.output_cny_per_1m} per 1M tokens (${price.channel_type}, ${price.quality})`);
        }
      }
    }
    return;
  }

  console.log('\nSyncing to Supabase...');
  const result = await syncToSupabase(validProviders);
  console.log(`\nDone! Inserted: ${result.inserted}, Updated: ${result.updated}, Models: ${result.modelsInserted}`);

  // Also remove old fake seed data that doesn't exist in hvoy's list
  console.log('\nCleaning up old seed data...');
  const hvoyUrls = new Set(validProviders.map(p => p.url));
  const { default: allProviders } = await fetch(
    `${SUPABASE_URL}/rest/v1/providers?select=id,name,url`,
    { headers: { apikey: SERVICE_ROLE_KEY, Authorization: `Bearer ${SERVICE_ROLE_KEY}` } }
  ).then(r => r.json());

  // We keep old providers that have user ratings or detection results
  // Only remove providers that are untested and have no ratings
  let removed = 0;
  for (const existing of allProviders || []) {
    if (!hvoyUrls.has(existing.url)) {
      // Check if it has ratings
      const ratingsRes = await fetch(
        `${SUPABASE_URL}/rest/v1/provider_ratings?provider_id=eq.${existing.id}&select=id&limit=1`,
        { headers: { apikey: SERVICE_ROLE_KEY, Authorization: `Bearer ${SERVICE_ROLE_KEY}` } }
      ).then(r => r.json());
      if (ratingsRes && ratingsRes.length === 0) {
        // Check if it has detection results
        const detRes = await fetch(
          `${SUPABASE_URL}/rest/v1/detection_results?provider_id=eq.${existing.id}&select=id&limit=1`,
          { headers: { apikey: SERVICE_ROLE_KEY, Authorization: `Bearer ${SERVICE_ROLE_KEY}` } }
        ).then(r => r.json());
        if (detRes && detRes.length === 0) {
          await fetch(
            `${SUPABASE_URL}/rest/v1/providers?id=eq.${existing.id}`,
            {
              method: 'DELETE',
              headers: {
                apikey: SERVICE_ROLE_KEY,
                Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
                Prefer: 'return=minimal',
              },
            }
          );
          console.log(`  Removed old seed: ${existing.name}`);
          removed++;
        }
      }
    }
  }
  console.log(`Removed ${removed} old seed entries`);
}

main().catch(console.error);
