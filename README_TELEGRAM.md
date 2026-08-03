*** Telegram integration notes

- Add to config.ini under [telegram]:
  bot_token=<your_bot_token>
  review_chat_id=<your_telegram_chat_id>

- Set your Telegram bot webhook to point to: https://<host>/telegram_webhook
  Use:
    https://api.telegram.org/bot<token>/setWebhook?url=https://<host>/telegram_webhook

- Dependencies:
    pip install flask requests

- Workflow:
  - When the orchestrator creates a draft, it will call the telegram.send_review_message
    function (if telegram config is present) and send the draft to the configured chat.
  - The message contains two buttons: Confirm and Rerun.
  - Confirm publishes the draft on Shopify (using the article id stored in the Post.external_id)
  - Rerun regenerates a new draft for the same topic and sends it again for review.

- Security: ensure your webhook endpoint is protected (TLS, secret path) in production.
