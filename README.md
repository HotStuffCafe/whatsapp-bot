# WhatsApp Bot

This service supports order capture, Razorpay payment links, and Google Sheets logging.

## Required Render environment variables

Set these keys in **Render → Service → Environment**:

- `ENABLE_PAYMENT` (`false`, `payonly`, or `paycod`)
- `GOOGLE_CREDS_JSON`
- `ORDER_SHEET_ID` (recommended) **or** `ORDER_SHEET_NAME`
- `ORDER_WORKSHEET` (use `ORDER`)
- `PAYLOAD_WORKSHEET` (use `PAYLOAD`)
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_CALLBACK_URL`

Optional:

- `OPENAI_API_KEY`
- `GOOGLE_CREDS_FILE`
- `GOOGLE_APPLICATION_CREDENTIALS`

## GitHub files to keep updated

If you want environment setup to be visible in GitHub and auto-applied for new Render deployments, update:

1. `render.yaml` (Render Blueprint env declarations)
2. `.env.example` (developer template for local setup)

## Quick checklist

1. Share your Google Sheet with the service account email from `GOOGLE_CREDS_JSON` as **Editor**.
2. Ensure `ORDER_WORKSHEET=ORDER` and `PAYLOAD_WORKSHEET=PAYLOAD`.
3. Use `ORDER_SHEET_ID` from your sheet URL (`/d/<sheet_id>/edit`).
4. Redeploy after env changes.
