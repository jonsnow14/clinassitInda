export const dynamic = "force-dynamic";
export const maxDuration = 180;

const API = process.env.API_INTERNAL_URL || "http://127.0.0.1:8001";

export async function POST(req: Request) {
  const body = await req.text();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 170_000);
  try {
    const res = await fetch(`${API}/v1/clinical/consult`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: controller.signal,
      cache: "no-store",
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "proxy failed";
    return Response.json(
      { detail: `Clinical proxy failed: ${message}. Is the API up on ${API}?` },
      { status: 502 },
    );
  } finally {
    clearTimeout(timer);
  }
}
