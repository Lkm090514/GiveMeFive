import { proxyAssessment } from './api-proxy.mjs';
export default {
 async fetch(request: Request, env: Cloudflare.Env) {
  const api = await proxyAssessment(request, env);
  if (api) return api;
  return env.ASSETS.fetch(request);
 }
};
