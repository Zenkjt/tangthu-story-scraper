const REPO = "Zenkjt/tangthu-opds";
const STORY_REPO = "Zenkjt/tangthu-story-scraper";
const DEFAULT_ALLOWED_ORIGIN = "https://tangthu.pages.dev";
const STORY_ROOT = "cache/stories";

function headers(origin) {
  return {
    "Access-Control-Allow-Origin": origin || DEFAULT_ALLOWED_ORIGIN,
    "Vary": "Origin",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  };
}

function json(data, status = 200, origin = DEFAULT_ALLOWED_ORIGIN) {
  return new Response(JSON.stringify(data), { status, headers: headers(origin) });
}

function originFor(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = env.ALLOWED_ORIGIN || DEFAULT_ALLOWED_ORIGIN;
  if (origin && origin !== allowed) return null;
  return origin || allowed;
}

async function gh(env, path, options = {}) {
  if (!env.GITHUB_TOKEN) throw new Error("GITHUB_TOKEN chưa được cấu hình");
  const response = await fetch(`https://api.github.com${path}`, {
    ...options,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "TangThu-Story-Worker/1.0 (+https://tangthu.pages.dev)",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    const error = new Error(`GitHub API ${response.status}: ${body.slice(0, 500)}`);
    error.status = response.status;
    throw error;
  }
  return response;
}

function keyPart(value) {
  const text = String(value || "").trim();
  if (!text || !/^[A-Za-z0-9._~-]{1,120}$/.test(text)) {
    throw new Error("user_id/story_id không hợp lệ");
  }
  return text;
}

function storyPath(userId, storyId) {
  return `${STORY_ROOT}/${keyPart(userId)}/${keyPart(storyId)}.json`;
}

async function readStory(env, userId, storyId) {
  const path = storyPath(userId, storyId);
  try {
    const response = await gh(env, `/repos/${REPO}/contents/${path}?ref=main`);
    const meta = await response.json();
    const binary = atob(String(meta.content).replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
    return {
      sha: meta.sha,
      data: JSON.parse(new TextDecoder().decode(bytes)),
    };
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

async function dispatch(env, payload) {
  await gh(env, `/repos/${STORY_REPO}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_type: "story-request",
      client_payload: payload,
    }),
  });
}

async function handleCurrent(request, env, origin) {
  const url = new URL(request.url);
  const userId = url.searchParams.get("user_id");
  const storyId = url.searchParams.get("story_id");
  if (!userId || !storyId) throw new Error("Thiếu user_id hoặc story_id");

  const cached = await readStory(env, userId, storyId);
  if (!cached) return json({ ok: false, status: "not_registered" }, 404, origin);
  return json({ ok: true, ...cached.data }, 200, origin);
}

async function handleCommand(request, env, origin, action) {
  const body = await request.json();
  const userId = String(body.user_id || "").trim();
  const storyId = String(body.story_id || "").trim();

  if (!userId) throw new Error("Thiếu user_id");

  if (action === "register") {
    const url = String(body.url || "").trim();
    if (!url) throw new Error("Thiếu URL truyện");
    await dispatch(env, { action, user_id: userId, url });
    return json({ ok: true, status: "queued" }, 202, origin);
  }

  if (!storyId) throw new Error("Thiếu story_id");

  const payload = { action, user_id: userId, story_id: storyId };
  if (action === "jump") payload.chapter = Number(body.chapter);
  await dispatch(env, payload);
  return json({ ok: true, status: "queued", action }, 202, origin);
}

export default {
  async fetch(request, env) {
    const origin = originFor(request, env);
    if (!origin) return json({ ok: false, error: "Origin không được phép" }, 403);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: headers(origin) });
    }

    try {
      const url = new URL(request.url);
      if (request.method === "GET" && url.pathname === "/story/current") {
        return await handleCurrent(request, env, origin);
      }

      if (request.method === "POST") {
        const routes = {
          "/story/register": "register",
          "/story/next": "next",
          "/story/previous": "previous",
          "/story/jump": "jump",
        };
        const action = routes[url.pathname];
        if (action) return await handleCommand(request, env, origin, action);
      }

      return json({ ok: false, error: "Not found" }, 404, origin);
    } catch (error) {
      return json(
        { ok: false, error: error.message || String(error) },
        error.status || 400,
        origin,
      );
    }
  },
};
