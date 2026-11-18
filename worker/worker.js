// Winterhouse survey relay (Cloudflare Worker).
// Checks each person's personal code, then commits their answers or photo to the PRIVATE data repo.
// The GitHub token lives only here, as a Worker secret, never in the public site.
//
// Secrets / vars (set with `wrangler secret put NAME` or in the dashboard):
//   GITHUB_TOKEN   fine-grained token: Contents read+write on the data repo only
//   REPO           "owner/winterhouse-data"
//   TOKENS         JSON {"Ryan":"<sha256 of Ryan's code>", ...} from tools/make_links.py
//   ALLOWED_ORIGIN "https://<you>.github.io"
//   CLOSES_AT      optional ISO time after which submissions are refused, e.g. 2026-11-23T05:00:00Z
//   BRANCH         optional, default "main"

const enc = new TextEncoder();
const MAX_JSON = 300_000;        // characters of answers JSON
const MAX_PHOTO_B64 = 8_000_000; // ~6 MB image

async function sha256hex(s) {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function b64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}
const slug = name => name.normalize("NFKD").replace(/[^A-Za-z0-9_-]/g, "");

function cors(env, req) {
  const origin = req.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGIN || "").split(",").map(s => s.trim()).filter(Boolean);
  return {
    "Access-Control-Allow-Origin": allowed.includes(origin) ? origin : (allowed[0] || "*"),
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}
const json = (body, status, headers) => new Response(JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json" } });

async function gh(env, path, method = "GET", body) {
  return fetch(`${env.GITHUB_API || "https://api.github.com"}/repos/${env.REPO}/contents/${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "User-Agent": "winterhouse-survey",
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
}
async function putFile(env, path, contentB64, message) {
  const branch = env.BRANCH || "main";
  for (let attempt = 0; attempt < 3; attempt++) {
    let sha;
    const cur = await gh(env, `${path}?ref=${branch}`);
    if (cur.status === 200) sha = (await cur.json()).sha;
    else if (cur.status !== 404) throw new Error(`GitHub read failed (${cur.status})`);
    const res = await gh(env, path, "PUT", { message, content: contentB64, branch, ...(sha ? { sha } : {}) });
    if (res.ok) return;
    if (res.status !== 409 && res.status !== 422) throw new Error(`GitHub write failed (${res.status})`);
  }
  throw new Error("GitHub write kept conflicting");
}

export default {
  async fetch(req, env) {
    const headers = cors(env, req);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (req.method !== "POST") return json({ error: "Not found" }, 404, headers);
    const route = new URL(req.url).pathname;

    let body;
    try { body = await req.json(); } catch { return json({ error: "Bad request" }, 400, headers); }
    const { me, k, part } = body || {};
    let tokens;
    try { tokens = JSON.parse(env.TOKENS || "{}"); } catch { return json({ error: "Survey isn't configured" }, 500, headers); }
    if (typeof me !== "string" || typeof k !== "string" || !tokens[me] || (await sha256hex(k)) !== tokens[me])
      return json({ error: "This link isn't recognised. Use the personal link Ryan sent you." }, 403, headers);
    if (part !== 1 && part !== 2) return json({ error: "Bad request" }, 400, headers);
    const base = body.pilot === true ? "pilot/" : "";   // pilot links save to a separate folder
    if (route !== "/load" && env.CLOSES_AT && Date.now() > Date.parse(env.CLOSES_AT))
      return json({ error: "The survey has closed. Message Ryan if you still need to send something." }, 403, headers);

    try {
      if (route === "/submit") {
        const text = JSON.stringify({ me, part, pilot: !!base, answers: body.answers, meta: { ...(body.meta || {}), receivedAt: new Date().toISOString() } }, null, 1);
        if (text.length > MAX_JSON) return json({ error: "That's too much text to save. Shorten a long answer and try again." }, 413, headers);
        const path = `${base}responses/part${part}/${slug(me)}.json`;
        await putFile(env, path, b64(enc.encode(text)), `${base ? "Pilot " : ""}Part ${part}: ${me}`);
        return json({ ok: true, path }, 200, headers);
      }
      if (route === "/load") {
        const path = `${base}responses/part${part}/${slug(me)}.json`;
        const r = await gh(env, `${path}?ref=${env.BRANCH || "main"}`);
        if (r.status === 404) return json({ found: false }, 200, headers);
        if (!r.ok) throw new Error(`GitHub read failed (${r.status})`);
        const file = await r.json();
        const bytes = Uint8Array.from(atob(file.content.replace(/\n/g, "")), c => c.charCodeAt(0));
        const saved = JSON.parse(new TextDecoder().decode(bytes));
        return json({ found: true, answers: saved.answers, submittedAt: saved.meta?.submittedAt }, 200, headers);
      }
      if (route === "/media") {
        const id = String(body.id || "");
        if (!/^[a-z0-9]{6,32}$/.test(id) || typeof body.data !== "string") return json({ error: "Bad request" }, 400, headers);
        if (body.data.length > MAX_PHOTO_B64) return json({ error: "That photo is too large. Try a smaller one." }, 413, headers);
        if (!/^[A-Za-z0-9+/=]+$/.test(body.data.slice(0, 2000))) return json({ error: "Bad image data" }, 400, headers);
        const path = `${base}media/${slug(me)}/${id}.jpg`;
        await putFile(env, path, body.data, `${base ? "Pilot photo" : "Photo"}: ${me}`);
        return json({ ok: true, path }, 200, headers);
      }
      return json({ error: "Not found" }, 404, headers);
    } catch (e) {
      return json({ error: "Couldn't save right now. Try again in a minute." , detail: String(e.message || e) }, 502, headers);
    }
  },
};
