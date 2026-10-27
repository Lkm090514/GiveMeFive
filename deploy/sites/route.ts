// Install as app/api/v4/[...path]/route.ts in the retained Vinext Sites checkout.
// This adapter is server-only; existing static assets belong in public/.
import { env } from 'cloudflare:workers';
import { proxyAssessment } from './api-proxy.mjs';
export const GET = (request: Request) => proxyAssessment(request, env);
export const POST = GET;
export const PUT = GET;
export const PATCH = GET;
export const DELETE = GET;
export const HEAD = GET;
export const OPTIONS = GET;
