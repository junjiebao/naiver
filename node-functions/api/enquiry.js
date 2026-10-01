/**
 * NAVIER YACHTS — Build Enquiry API
 * EdgeOne Pages Node Function. Route: POST /api/enquiry
 *
 * Receives the website enquiry form (and newsletter signup) and forwards it to a
 * Lark / Feishu group chat via a custom-bot webhook.
 *
 * SECURITY NOTE
 * The GitHub repository for this site is PUBLIC. The webhook URL and the signing
 * secret must therefore NEVER be written into this file. They are read at runtime
 * from EdgeOne Pages environment variables:
 *
 *   LARK_WEBHOOK_URL     e.g. https://open.larksuite.com/open-apis/bot/v2/hook/xxxx
 *   LARK_WEBHOOK_SECRET  the custom-bot signing secret
 *
 * If they are absent the endpoint fails loudly (503) instead of silently
 * swallowing enquiries.
 */

import { createHmac } from 'node:crypto';

/* ------------------------------------------------------------------ *
 * Configuration
 * ------------------------------------------------------------------ */

const ENQUIRY_HOSTS = ['www.navieryacht.com', 'navieryacht.com'];
const DEV_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]'];

const LIMITS = {
  name: 200,
  phone: 80,
  email: 254,
  message: 5000,
  company: 200,
  vesselType: 120,
  budget: 120,
  timeline: 120,
  quantity: 120,
  website: 200, // honeypot
};

const RATE_WINDOW_MS = 60_000;
const RATE_MAX = 5;
const UPSTREAM_TIMEOUT_MS = 8000;

/** Best-effort in-memory throttle. Edge instances are ephemeral, so this only
 *  raises the cost of casual abuse; it is not a hard guarantee. */
const rateBuckets = new Map();

/* ------------------------------------------------------------------ *
 * Helpers
 * ------------------------------------------------------------------ */

function jsonResponse(status, payload, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=UTF-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      ...extraHeaders,
    },
  });
}

/** Collapse whitespace, strip control characters, and cap the length. */
export function clean(value, max) {
  if (value === undefined || value === null) return '';
  const text = String(value)
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '')
    .replace(/\r\n?/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .trim();
  return text.length > max ? text.slice(0, max) : text;
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value);
}

/** At least 6 digits somewhere in the string — tolerant of +, spaces, dashes. */
export function looksLikePhone(value) {
  const digits = String(value).replace(/\D/g, '');
  return digits.length >= 6 && digits.length <= 20;
}

/**
 * Lark / Feishu custom-bot signature.
 * stringToSign = `${timestamp}\n${secret}` is used as the HMAC key, and the
 * signed payload is empty. Result is base64.
 * Ref: open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
 */
export function genSign(secret, timestamp) {
  const stringToSign = `${timestamp}\n${secret}`;
  return createHmac('sha256', Buffer.from(stringToSign, 'utf8'))
    .update(Buffer.alloc(0))
    .digest('base64');
}

function readEnv(context) {
  const env = (context && context.env) || process.env || {};
  return {
    url: env.LARK_WEBHOOK_URL || process.env.LARK_WEBHOOK_URL || '',
    secret: env.LARK_WEBHOOK_SECRET || process.env.LARK_WEBHOOK_SECRET || '',
  };
}

function isAllowedOrigin(request) {
  const origin = request.headers.get('origin');
  const referer = request.headers.get('referer');
  const source = origin || referer || '';
  if (!source) return true; // non-browser client (e.g. curl smoke test)

  try {
    const host = new URL(source).hostname.toLowerCase();
    return ENQUIRY_HOSTS.includes(host) || DEV_HOSTS.includes(host);
  } catch {
    return false;
  }
}

function checkRate(ip) {
  if (!ip) return true;
  const now = Date.now();
  const bucket = rateBuckets.get(ip) || [];
  const recent = bucket.filter((t) => now - t < RATE_WINDOW_MS);
  if (recent.length >= RATE_MAX) {
    rateBuckets.set(ip, recent);
    return false;
  }
  recent.push(now);
  rateBuckets.set(ip, recent);

  if (rateBuckets.size > 5000) {
    for (const [key, times] of rateBuckets) {
      if (times.every((t) => now - t >= RATE_WINDOW_MS)) rateBuckets.delete(key);
    }
  }
  return true;
}

/* ------------------------------------------------------------------ *
 * Parsing
 * ------------------------------------------------------------------ */

async function parseBody(request) {
  const contentType = (request.headers.get('content-type') || '').toLowerCase();

  if (contentType.includes('application/json')) {
    const data = await request.json();
    return data && typeof data === 'object' ? data : {};
  }

  const raw = await request.text();
  if (contentType.includes('application/x-www-form-urlencoded') || raw.includes('=')) {
    return Object.fromEntries(new URLSearchParams(raw));
  }
  try {
    const data = JSON.parse(raw);
    return data && typeof data === 'object' ? data : {};
  } catch {
    return {};
  }
}

/* ------------------------------------------------------------------ *
 * Message rendering
 * ------------------------------------------------------------------ */

function trimOrDash(value) {
  return value && value.length ? value : '—';
}

function buildCard(payload, meta) {
  const isSubscribe = payload.kind === 'subscribe';

  const rows = isSubscribe
    ? [`**邮箱**：${trimOrDash(payload.email)}`]
    : [
        `**姓名 / 公司**：${trimOrDash(payload.name)}`,
        `**电话 / WhatsApp**：${trimOrDash(payload.phone)}`,
        `**邮箱**：${trimOrDash(payload.email)}`,
      ];

  const details = isSubscribe
    ? []
    : [
        `**船型 / 项目类型**：${trimOrDash(payload.vesselType)}`,
        `**数量**：${trimOrDash(payload.quantity)}`,
        `**预算区间**：${trimOrDash(payload.budget)}`,
        `**期望周期**：${trimOrDash(payload.timeline)}`,
      ];

  const lines = [
    rows.join('\n'),
    ...(details.length ? ['', details.join('\n')] : []),
    ...(!isSubscribe && payload.message
      ? ['', '**需求描述**', payload.message]
      : []),
    '',
    `**提交时间**：${meta.localTime} (GST)`,
    `**来源页面**：${meta.page}`,
    `**国家 / IP**：${meta.country} · ${meta.ip}`,
  ];

  return {
    msg_type: 'interactive',
    card: {
      schema: '2.0',
      config: { update_multi: true },
      header: {
        title: {
          tag: 'plain_text',
          content: isSubscribe ? 'New subscriber' : 'New build enquiry',
        },
        template: isSubscribe ? 'green' : 'blue',
      },
      body: {
        direction: 'vertical',
        padding: '12px 12px 12px 12px',
        elements: [
          {
            tag: 'markdown',
            content: lines.join('\n'),
            text_align: 'left',
            text_size: 'normal_v2',
            margin: '0px 0px 0px 0px',
          },
        ],
      },
    },
  };
}

async function postToLark(webhookUrl, secret, body) {
  const timestamp = String(Math.floor(Date.now() / 1000));
  const outbound = secret
    ? { timestamp, sign: genSign(secret, timestamp), ...body }
    : body;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  try {
    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=UTF-8' },
      body: JSON.stringify(outbound),
      signal: controller.signal,
    });

    const text = await res.text();
    let parsed = null;
    try {
      parsed = JSON.parse(text);
    } catch {
      /* non-JSON upstream response */
    }

    const ok = res.ok && (!parsed || parsed.code === 0 || parsed.StatusCode === 0);
    return {
      ok,
      status: res.status,
      code: parsed ? parsed.code : null,
      message: parsed ? parsed.msg || parsed.StatusMessage : text.slice(0, 300),
    };
  } catch (error) {
    const aborted = error && error.name === 'AbortError';
    return {
      ok: false,
      status: 0,
      code: null,
      message: aborted ? 'upstream timeout' : String(error && error.message),
    };
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ *
 * Handler
 * ------------------------------------------------------------------ */

export async function onRequest(context) {
  const { request } = context;
  const method = request.method.toUpperCase();

  if (method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: { Allow: 'POST, OPTIONS', 'Cache-Control': 'no-store' },
    });
  }

  // Health probe: confirms env wiring without revealing any secret material.
  if (method === 'GET') {
    const { url, secret } = readEnv(context);
    const configured = Boolean(url && secret);
    return jsonResponse(configured ? 200 : 503, {
      ok: configured,
      endpoint: '/api/enquiry',
      webhookConfigured: Boolean(url),
      secretConfigured: Boolean(secret),
      ready: configured,
    });
  }

  if (method !== 'POST') {
    return jsonResponse(405, { ok: false, error: 'Method not allowed' }, { Allow: 'POST, OPTIONS' });
  }

  const { url: webhookUrl, secret } = readEnv(context);
  if (!webhookUrl || !secret) {
    // Loud failure: an unconfigured deployment must never look like a success.
    return jsonResponse(503, {
      ok: false,
      error: 'Enquiry endpoint is not configured on the server.',
      hint: 'Set LARK_WEBHOOK_URL and LARK_WEBHOOK_SECRET in EdgeOne Pages environment variables.',
    });
  }

  if (!isAllowedOrigin(request)) {
    return jsonResponse(403, { ok: false, error: 'Origin not allowed' });
  }

  const ip =
    context.clientIp ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    '';

  if (!checkRate(ip)) {
    return jsonResponse(429, {
      ok: false,
      error: 'Too many submissions. Please try again in a minute.',
    });
  }

  let body;
  try {
    body = await parseBody(request);
  } catch {
    return jsonResponse(400, { ok: false, error: 'Malformed request body' });
  }

  const kind = clean(body.kind, 20) === 'subscribe' ? 'subscribe' : 'enquiry';

  // Honeypot: real users never fill a field they cannot see.
  if (clean(body.website, LIMITS.website)) {
    return jsonResponse(200, { ok: true, message: 'Received' });
  }

  const payload = {
    kind,
    name: clean(body.name, LIMITS.name),
    phone: clean(body.phone, LIMITS.phone),
    email: clean(body.email, LIMITS.email),
    company: clean(body.company, LIMITS.company),
    vesselType: clean(body.vesselType, LIMITS.vesselType),
    budget: clean(body.budget, LIMITS.budget),
    timeline: clean(body.timeline, LIMITS.timeline),
    quantity: clean(body.quantity, LIMITS.quantity),
    message: clean(body.message, LIMITS.message),
  };

  if (kind === 'subscribe') {
    if (!isValidEmail(payload.email)) {
      return jsonResponse(400, { ok: false, error: 'Please enter a valid email address.' });
    }
  } else {
    const errors = [];
    if (payload.name.length < 2) errors.push('name');
    if (!looksLikePhone(payload.phone)) errors.push('phone');
    if (!isValidEmail(payload.email)) errors.push('email');
    if (payload.message.length < 5) errors.push('message');
    if (errors.length) {
      return jsonResponse(400, {
        ok: false,
        error: 'Please check the highlighted fields.',
        fields: errors,
      });
    }
  }

  const geo = context.geo || {};
  const now = new Date();
  const meta = {
    localTime: new Date(now.getTime() + 4 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' '),
    page: clean(body.page, 200) || '—',
    country: clean(geo.countryName || geo.country || '', 60) || '—',
    ip: ip || '—',
  };

  const result = await postToLark(webhookUrl, secret, buildCard(payload, meta));

  if (!result.ok) {
    console.error('[enquiry] lark delivery failed', JSON.stringify(result));
    return jsonResponse(502, {
      ok: false,
      error: 'We could not deliver your enquiry right now.',
      fallback: 'Please email info@navieryacht.com or call +971 58 508 8518.',
    });
  }

  return jsonResponse(200, { ok: true, message: 'Enquiry delivered' });
}

export default onRequest;
