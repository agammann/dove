declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    OPENAI_API_KEY?: string;
    OPENAI_MODEL?: string;
    DOVE_ADMIN_TOKEN?: string;
    RESEND_API_KEY?: string;
    RESEND_WEBHOOK_SECRET?: string;
    EMAIL_FROM?: string;
    REPLY_DOMAIN?: string;
    BUCKET?: R2Bucket;
  }
}
