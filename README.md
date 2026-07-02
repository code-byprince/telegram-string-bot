# Telegram String Session Generator Bot

A production-ready Telegram bot that generates a **Pyrogram string session**
for a user's own Telegram account, entirely in-memory, with no persistent
storage of credentials or sessions. Built with **Pyrogram**, **TgCrypto**,
and **Flask** (for the Render health check), deployable in one click on
**Render**.

---

## ✨ Features

- `/start` — professional welcome message
- `/generate` — guided, step-by-step string session generation
  (API_ID → API_HASH → phone number → OTP → 2FA password if enabled)
- `/cancel` — cancel an in-progress generation at any time
- Full input validation with clear error messages
- Graceful handling of `FloodWait`, invalid/expired OTP, invalid phone
  numbers, and invalid 2FA passwords
- Session string delivered **only** to the requesting user, in their
  private chat
- **Nothing sensitive is ever persisted**: phone numbers, OTPs, passwords,
  and generated session strings live only in memory for the duration of the
  request and are explicitly wiped afterward
- Per-user conversation state with automatic timeout for inactive flows
- Prevents concurrent `/generate` flows per user
- Rate limiting (per-command and per-generation-attempt)
- Structured logging that never logs sensitive data
- Admin tools: `/stats`, `/broadcast`, `/users`

---

## 🗂️ Project Structure

```
telegram-session-generator-bot/
├── app/
│   ├── bot.py                # Pyrogram Client factory + handler registration
│   ├── config.py              # Environment-based configuration
│   ├── handlers/
│   │   ├── start.py           # /start, /help
│   │   ├── generate.py        # /generate, /cancel, conversation FSM
│   │   └── admin.py           # /stats, /broadcast, /users
│   ├── utils/
│   │   ├── logger.py          # Structured logging with redaction
│   │   ├── rate_limiter.py    # In-memory rate limiting
│   │   ├── state_manager.py   # In-memory conversation FSM + secure cleanup
│   │   ├── stats.py           # In-memory, non-sensitive analytics
│   │   └── validators.py      # Input validation
│   └── web/
│       └── health.py          # Flask health-check app
├── main.py                    # Entrypoint: Flask (thread) + Pyrogram (main)
├── requirements.txt
├── Procfile
├── runtime.txt
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔐 Security Model

- **No database.** The bot never stores generated session strings, OTP
  codes, 2FA passwords, or phone numbers on disk or in any external store.
- **In-memory Pyrogram clients.** Every temporary `Client` used during
  generation is created with `in_memory=True`, so no `.session` file ever
  touches disk.
- **Explicit wipes.** As soon as a flow completes (success, failure,
  cancellation, or timeout), all sensitive fields on the conversation state
  are set to `None` and the temporary client is disconnected.
- **Redacting logger.** The logging setup includes a safety-net filter that
  redacts phone-number-like sequences, and application code is written to
  never pass sensitive values to `log.*()` calls in the first place.
- **Rate limiting** on both commands and generation attempts helps prevent
  abuse of Telegram's login-code API from your bot.
- **Single active flow per user** prevents state confusion and abuse.

⚠️ A Pyrogram string session grants **full access** to the Telegram account
it was generated for. This bot only ever sends it to the user who requested
it, in a private chat — but users should be reminded (as the bot does) to
never share it with anyone else.

---

## 🚀 Getting Your Own API_ID / API_HASH / BOT_TOKEN

1. **BOT_TOKEN** — talk to [@BotFather](https://t.me/BotFather) on Telegram,
   create a new bot with `/newbot`, and copy the token it gives you.
2. **API_ID / API_HASH** (for the bot's own client, *not* for end users) —
   go to <https://my.telegram.org>, log in, open **API Development Tools**,
   and create an app to get your `API_ID` and `API_HASH`.
3. **ADMIN_IDS** — message [@userinfobot](https://t.me/userinfobot) to get
   your numeric Telegram user ID.

End users of `/generate` will provide **their own** API_ID/API_HASH/phone
during the conversation — those are never the same as the bot's own
credentials above.

---

## 🖥️ Local Development

```bash
git clone <your-repo-url>
cd telegram-session-generator-bot

python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env with your real values

python main.py
```

The Flask health server will be available at `http://localhost:8080/health`
and the bot will start polling Telegram for updates.

---

## ☁️ Deploying to Render

### Option A — One-click Blueprint deploy

1. Push this repository to your own GitHub account.
2. In Render, choose **New → Blueprint**, and point it at your repo.
   Render will read `render.yaml` automatically.
3. Fill in the required secret environment variables when prompted:
   `BOT_TOKEN`, `API_ID`, `API_HASH`, `ADMIN_IDS`.
4. Click **Apply** — Render will build and deploy the service.

### Option B — Manual Web Service

1. In Render, choose **New → Web Service** and connect your GitHub repo.
2. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Health Check Path**: `/health`
3. Add the environment variables listed below under **Environment
   Variables**.
4. Deploy.

Render automatically sets the `PORT` environment variable; `main.py` reads
it via `Config.PORT`, so no changes are needed.

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token from @BotFather for the bot itself |
| `API_ID` | ✅ | The bot's own numeric API ID from my.telegram.org |
| `API_HASH` | ✅ | The bot's own API hash from my.telegram.org |
| `ADMIN_IDS` | ✅ | Comma-separated numeric Telegram user IDs with admin access |
| `PORT` | ⛔ (set by Render) | Port for the Flask health check server (default `8080`) |
| `SESSION_TIMEOUT_SECONDS` | ⛔ | Inactivity timeout for an in-progress `/generate` flow (default `300`) |
| `RATE_LIMIT_SECONDS` | ⛔ | Cooldown between `/generate` attempts per user (default `60`) |
| `COMMAND_RATE_LIMIT_SECONDS` | ⛔ | Cooldown between any two messages per user (default `2`) |
| `MAX_OTP_ATTEMPTS` | ⛔ | Max invalid OTP attempts before auto-cancel (default `3`) |
| `MAX_PASSWORD_ATTEMPTS` | ⛔ | Max invalid 2FA password attempts before auto-cancel (default `3`) |
| `LOG_LEVEL` | ⛔ | `DEBUG` / `INFO` / `WARNING` / `ERROR` (default `INFO`) |
| `BOT_NAME` | ⛔ | Display name used in bot messages |
| `SUPPORT_USERNAME` | ⛔ | Optional support contact shown to users |

---

## 🤖 Commands

**Everyone**
- `/start` — welcome message
- `/help` — command reference
- `/generate` — start generating a string session
- `/cancel` — cancel an in-progress generation

**Admins only** (must be listed in `ADMIN_IDS`)
- `/stats` — total users, successful/failed generations, active flows, uptime
- `/users` — total unique user count
- `/broadcast <message>` — send a message to every known user (or reply to
  a message with `/broadcast` to forward its content)

---

## 🧪 Notes on Reliability

- If the process restarts (e.g. Render redeploy), all in-memory state
  (conversation flows, stats counters, rate-limit timers) resets. This is by
  design — it guarantees nothing sensitive survives a restart, at the cost
  of losing in-progress flows and cumulative stats across deploys.
- The bot runs as a single process; Flask runs on a background thread purely
  to satisfy Render's health check requirement for web services.

---

## 📜 License

Provided as-is for your own deployment and modification.
