#!/usr/bin/env node
/**
 * generate-covers.js
 * Generates cover images for auto-generated articles using Gemini Banana.
 * Saves images to public/images/articles/ and updates Supabase articles.
 *
 * Usage:
 *   GEMINI_API_KEY=xxx node scripts/generate-covers.js
 *   GEMINI_API_KEY=xxx node scripts/generate-covers.js --regenerate
 */

const SUPABASE_URL = 'https://ijqizaquvtpphqkysaoi.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const GEMINI_KEY = process.env.GEMINI_API_KEY;
const FORCE = process.argv.includes('--regenerate');

const fs = require('fs');
const path = require('path');
const OUT_DIR = path.join(__dirname, '..', 'public', 'images', 'articles');

if (!GEMINI_KEY) {
  console.error('Error: GEMINI_API_KEY env var required');
  process.exit(1);
}

// ─── Image prompts per article type ───────────────────────────

const COVER_PROMPTS = {
  // Price rankings
  'price-ranking': 'A sleek dark-themed infographic header image showing glowing price comparison bar charts and data tables in cyan and magenta neon colors on a dark navy background, tech startup style, no readable text, futuristic data visualization, wide banner format',

  // Recommended providers
  'recommended': 'A clean modern tech illustration showing a golden trophy surrounded by glowing server nodes and API connection lines on a dark gradient background, cyberpunk aesthetic, no text, wide banner',

  // Model comparison
  'comparison': 'A futuristic split-screen visualization showing different AI model icons connected by data streams, binary code flowing between them, dark theme with blue and purple gradients, no readable text, wide banner',

  // Beginner guide
  'beginner-guide': 'A clean educational illustration showing a roadmap path through a digital landscape with signposts, light bulb icons, and shield symbols on a dark blue gradient background, friendly tech style, no readable text, wide banner format',

  // Default fallback
  'default': 'Abstract futuristic technology background with glowing neural network connections and data particles on dark navy background, no text, wide banner',
};

function getPromptForSlug(slug) {
  if (slug.includes('price-ranking')) return COVER_PROMPTS['price-ranking'];
  if (slug.includes('recommended')) return COVER_PROMPTS['recommended'];
  if (slug.includes('comparison')) return COVER_PROMPTS['comparison'];
  if (slug.includes('beginner')) return COVER_PROMPTS['beginner-guide'];
  return COVER_PROMPTS['default'];
}

// ─── Gemini API call ──────────────────────────────────────────

const { execSync } = require('child_process');

async function generateImage(prompt) {
  const body = JSON.stringify({
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      responseModalities: ['IMAGE'],
      imageConfig: { aspectRatio: '16:9', imageSize: '1K' },
    },
  });

  // Use curl to avoid Node.js fetch DNS issues
  const tmpOut = `/tmp/gemini-cover-${Date.now()}.json`;
  const tmpBody = `/tmp/gemini-cover-body-${Date.now()}.json`;
  fs.writeFileSync(tmpBody, body);

  execSync(
    `curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" ` +
    `-H "x-goog-api-key: ${GEMINI_KEY}" -H "Content-Type: application/json" ` +
    `-d @${tmpBody} -o ${tmpOut}`,
    { timeout: 60000 }
  );

  fs.unlinkSync(tmpBody);

  const data = JSON.parse(fs.readFileSync(tmpOut, 'utf8'));
  fs.unlinkSync(tmpOut);

  if (data.error) throw new Error(data.error.message);

  const parts = data.candidates?.[0]?.content?.parts || [];
  const imgPart = parts.find(p => p.inlineData);
  if (!imgPart) throw new Error('No image in response');

  return {
    mimeType: imgPart.inlineData.mimeType,
    data: Buffer.from(imgPart.inlineData.data, 'base64'),
  };
}

// ─── Main ─────────────────────────────────────────────────────

async function main() {
  // Create output directory
  if (!fs.existsSync(OUT_DIR)) {
    fs.mkdirSync(OUT_DIR, { recursive: true });
  }

  // Get all published articles
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/articles?select=id,slug,title,cover_image&is_published=eq.true&order=published_at.desc`,
    { headers: { apikey: SERVICE_ROLE_KEY, Authorization: `Bearer ${SERVICE_ROLE_KEY}` } }
  );
  const articles = await res.json();
  console.log(`Found ${articles.length} published articles\n`);

  for (const article of articles) {
    const filename = `${article.slug}.jpg`;
    const filepath = path.join(OUT_DIR, filename);
    const publicUrl = `/images/articles/${filename}`;

    // Skip if already has cover image and not forcing regeneration
    if (article.cover_image && !FORCE) {
      console.log(`  Skipping ${article.slug} (already has cover)`);
      continue;
    }

    const prompt = getPromptForSlug(article.slug);
    console.log(`Generating cover for: ${article.title}`);

    try {
      const img = await generateImage(prompt);
      // Save PNG then convert to JPEG for smaller size
      const tmpPng = filepath.replace('.jpg', '.tmp.png');
      fs.writeFileSync(tmpPng, img.data);
      try {
        execSync(`sips -s format jpeg -s formatOptions 80 "${tmpPng}" --out "${filepath}" 2>/dev/null`);
        fs.unlinkSync(tmpPng);
      } catch {
        // Fallback: just rename if sips fails (e.g. on Linux)
        fs.renameSync(tmpPng, filepath);
      }
      const finalSize = fs.statSync(filepath).size;
      console.log(`  Saved: ${filepath} (${(finalSize / 1024).toFixed(0)} KB)`);

      // Update article in Supabase
      const updRes = await fetch(
        `${SUPABASE_URL}/rest/v1/articles?id=eq.${article.id}`,
        {
          method: 'PATCH',
          headers: {
            apikey: SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
            Prefer: 'return=minimal',
          },
          body: JSON.stringify({ cover_image: publicUrl }),
        }
      );
      if (updRes.ok) {
        console.log(`  Updated cover_image: ${publicUrl}`);
      } else {
        console.error(`  Failed to update: ${await updRes.text()}`);
      }

      // Rate limit: wait 3 seconds between requests
      await new Promise(r => setTimeout(r, 3000));
    } catch (e) {
      console.error(`  Error: ${e.message}`);
    }
  }

  console.log('\nDone!');
}

main().catch(console.error);
