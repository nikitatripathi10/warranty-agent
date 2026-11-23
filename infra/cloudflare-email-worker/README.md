# Warranty Agent — Forward-to-Email Worker

Receives every email sent to your domain (via Cloudflare Email Routing), parses it with
[`postal-mime`](https://github.com/postalsys/postal-mime) and POSTs it to the backend at
`/ingestion/inbound-email`. Free tier: 100,000 requests/day.

## Deploy (about 5 minutes)

1. Add your domain to a free Cloudflare account and enable **Email → Email Routing**
   (Cloudflare adds the MX/SPF records for you).
2. From this folder:
   ```bash
   npm install
   npx wrangler login
   npx wrangler deploy
   npx wrangler secret put WEBHOOK_URL           # https://<your-backend>/ingestion/inbound-email
   npx wrangler secret put INBOUND_EMAIL_SECRET  # a long random string
   ```
3. Cloudflare dashboard → **Email Routing → Routing rules → Catch-all address** →
   action **Send to a Worker** → choose `warranty-agent-email`.
4. On the backend (Render → Environment) set the same secret plus your domain:
   ```env
   INBOUND_EMAIL_DOMAIN=warrantyagent.in
   INBOUND_EMAIL_SECRET=<same long random string>
   ```

Each user then sees their own `bills+<token>@warrantyagent.in` address under
**Upload → Forward bills by email**.

## Notes
- Unknown or rotated addresses are accepted by the backend and silently ignored, so nothing leaks
  about which addresses exist.
- If the backend is down or returns an error, the worker rejects the message so the sending
  server retries later.

