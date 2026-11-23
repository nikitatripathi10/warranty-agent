/**
 * Cloudflare Email Worker for Warranty Agent "forward-to-email".
 *
 * Cloudflare Email Routing hands every email sent to your domain to this worker.
 * It parses the message and POSTs it (as JSON, with a shared-secret header) to
 *   <WEBHOOK_URL>  e.g. https://warranty-agent.onrender.com/ingestion/inbound-email
 *
 * Secrets / variables (set with `wrangler secret put` or the dashboard):
 *   WEBHOOK_URL           the backend endpoint above
 *   INBOUND_EMAIL_SECRET  must equal INBOUND_EMAIL_SECRET on the backend
 */
import PostalMime from "postal-mime";

const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024;
const WANTED_TYPE = /^(application\/pdf|image\/)/i;

function toBase64(bytes) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export default {
  async email(message, env) {
    const raw = await new Response(message.raw).arrayBuffer();
    const parsed = await PostalMime.parse(raw);

    const attachments = [];
    for (const att of parsed.attachments || []) {
      if (attachments.length >= MAX_ATTACHMENTS) break;
      if (!WANTED_TYPE.test(att.mimeType || "")) continue;
      const bytes = new Uint8Array(att.content);
      if (bytes.length === 0 || bytes.length > MAX_ATTACHMENT_BYTES) continue;
      attachments.push({
        filename: att.filename || "attachment",
        content_type: att.mimeType,
        content_base64: toBase64(bytes),
      });
    }

    const response = await fetch(env.WEBHOOK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Inbound-Email-Secret": env.INBOUND_EMAIL_SECRET,
      },
      body: JSON.stringify({
        // message.to is the envelope recipient, so catch-all and "+token" addressing both work.
        to: message.to,
        from: message.from,
        subject: parsed.subject || "",
        text: parsed.text || "",
        html: parsed.html || "",
        message_id: parsed.messageId || "",
        attachments,
      }),
    });

    if (!response.ok) {
      // Ask the sending server to retry later instead of silently losing the bill.
      message.setReject(`Warranty Agent could not process this email (HTTP ${response.status}).`);
    }
  },
};

