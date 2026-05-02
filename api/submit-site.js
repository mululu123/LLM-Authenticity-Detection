const SUPABASE_URL = "https://ijqizaquvtpphqkysaoi.supabase.co";
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { name, url, description } = req.body || {};

  if (!name || !url) {
    return res.status(400).json({ error: "站点名称和URL为必填项" });
  }

  try {
    new URL(url);
  } catch {
    return res.status(400).json({ error: "URL格式不正确，需要包含 http:// 或 https://" });
  }

  try {
    const resp = await fetch(`${SUPABASE_URL}/rest/v1/providers`, {
      method: "POST",
      headers: {
        apikey: SERVICE_ROLE_KEY,
        Authorization: `Bearer ${SERVICE_ROLE_KEY}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal"
      },
      body: JSON.stringify({
        name: name.trim().substring(0, 100),
        url: url.trim().substring(0, 500),
        description: (description || "").trim().substring(0, 500) || null,
        status: "pending",
        is_verified: false,
        risk_level: "untested"
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      if (err.code === "23505") {
        return res.status(409).json({ error: "该站点已被收录或待审核" });
      }
      return res.status(500).json({ error: "提交失败，请稍后重试" });
    }

    return res.status(200).json({ success: true, message: "感谢提交！我们会尽快审核收录。" });
  } catch (e) {
    return res.status(500).json({ error: "服务器错误" });
  }
}
