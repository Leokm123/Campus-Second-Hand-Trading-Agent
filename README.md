# Campus Second-Hand Trading Agent

An agent that turns noisy campus second-hand group chats into "one sentence, find a reliable seller, and auto-send a WeChat message."

Starting from a single natural-language request (e.g. `looking for a bicycle, budget 300, on campus`), the agent runs an end-to-end pipeline: intent parsing → chat listing extraction → semantic matching → risk assessment → negotiation message generation → automatic WeChat send.

## Features

- **Chat data import**: built-in demo data, paste text, or upload `.txt/.json` files.
- **AI listing extraction**: identifies sell messages from messy group chat, filters out chatter / wanted / price comparisons, and structures them into product name, price, condition, seller, contact, location, and category.
- **Natural-language intent parsing**: understands colloquial requests, extracts item / budget / location, and asks follow-up questions when information is missing.
- **Semantic matching + scoring**: cross-language matching (e.g. `bicycle` matches `Giant ATX660` / `Flying Pigeon`) with a composite score based on price, condition, and description completeness.
- **Risk assessment**: each result gets a green / yellow / red level with reasons. High-risk items produce cautious inquiry messages (no price judgment, only asks for details and contact).
- **Negotiation message generation**: personalized WeChat messages based on item info and risk level.
- **Automatic WeChat send**: drives the WeChat desktop client via wxauto4 to actually deliver the message to the seller.
- **Multi-agent parallel collaboration**: an Orchestrator coordinates Matcher and RiskCheck running in parallel, with a visible task plan and risk summary panel.
- **Bilingual**: UI, API, risk reasons, and generated messages all switch by language.

## Tech Stack

- **Backend**: Python 3.10 + Flask + Flask-CORS
- **AI**: DeepSeek (OpenAI-compatible) powers intent parsing, extraction, semantic matching, risk assessment, and message generation; falls back to regex / rule engine / templates automatically when no API key is configured
- **WeChat automation**: wxauto4 + pywin32 (drives the WeChat desktop client)
- **Frontend**: vanilla HTML / CSS / JavaScript, Neobrutalism design
- **Deployment**: Flask serves the frontend from the same origin on a single port `localhost:5000`

## Project Structure

```
二手/
├── backend/
│   ├── app.py              # Flask API entry (import / match / negotiate / send / status)
│   ├── nlp_extractor.py   # Chat listing extraction (LLM + regex fallback)
│   ├── matcher.py         # Intent parsing + semantic match & scoring (LLM + regex fallback)
│   ├── risk_check.py      # Risk assessment (LLM + rule fallback)
│   ├── negotiator.py      # Negotiation message generation (LLM + template fallback)
│   ├── agents.py          # Multi-agent framework + Orchestrator parallel execution
│   ├── wxauto_sender.py   # WeChat auto send
│   ├── llm_config.py      # DeepSeek LLM client config
│   └── test_pipeline.py   # End-to-end integration test
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── data/
│   ├── mock_chats.json    # Demo chat data
│   └── demo_chat_text.txt # Plain-text chat log
├── wx_test.py             # Quick WeChat send test script
├── requirements.txt
├── .env.example           # DeepSeek API key template
└── README.md
```

## Prerequisites

1. **Windows** (wxauto4 depends on the WeChat desktop client).
2. **Python 3.10** (wxauto4 is installed in the system Python 3.10 environment; use this version to run the backend).
3. **WeChat desktop client logged in and online** (required for real message sending).
4. **DeepSeek API key (optional)**: enables full AI across the pipeline; without it the app still runs in rule/template fallback mode.

## Deployment

### 1. Install dependencies

From the project root, install the Python dependencies (including wxauto4 and pywin32):

```bash
python -m pip install -r requirements.txt
```

> If you have multiple Python versions, pin 3.10 with:
> `py -3.10 -m pip install -r requirements.txt`

wxauto4 is required for the WeChat send feature. If the line above fails to install it, install it directly:

```bash
python -m pip install wxauto4
```

> If wxauto4 is unavailable on PyPI, install from GitHub:
> `python -m pip install git+https://github.com/cluic/wxauto4.git`

### 2. Configure the DeepSeek API key (optional but recommended)

Copy `.env.example` to `.env` and fill in your key:

```
DEEPSEEK_API_KEY=sk-your-real-key
```

The app still works without it; agents fall back to the rule engine and template messages.

### 3. Start the backend

From the project root:

```bash
python backend/app.py
```

> With multiple Python versions, pin 3.10: `py -3.10 backend/app.py`

On success the console shows:

```
==================================================
校园二手交易 Agent — 后端服务
==================================================
 * Running on http://0.0.0.0:5000
```

### 4. Open the frontend

The backend serves the frontend from the same origin. Visit:

```
http://localhost:5000
```

### 5. Usage

1. Open the page, choose "Demo Data", and click "AI Extract Listings".
2. On the confirm page, select the listings to import and click "Confirm Import".
3. Type a request, for example:
   ```
   looking for a bicycle, budget 300, on campus
   ```
4. Watch the Agent Work Panel (task decomposition + parallel execution + risk summary), then wait for result cards.
5. Click any green / yellow / red card to generate a WeChat message tailored to its risk level.
6. Click "Send to <seller>" to send the message through the WeChat desktop client.

## Testing

### End-to-end integration test (no WeChat required)

```bash
python backend/test_pipeline.py
```

Covers 5 cases: complete need, iPhone, textbook, incomplete info, missing location.

### WeChat send single-point test

```bash
python wx_test.py "Ding Zihan" "Hello, this is a test message"
```

## Quick Demo

| Scenario | Input / Action | Expected |
|---|---|---|
| Complete need | `looking for a bicycle, budget 300, on campus` | Multiple green / yellow / red cards; Agent panel shows parallel execution |
| Incomplete info | `I want a guitar` | Agent asks for budget and location; multi-turn completion |
| High risk | Click a red card | Cautious inquiry message, no price judgment |
| WeChat send | `looking for headphones, budget 1000, East Area` → click a green card → Send to seller | Message is actually sent via WeChat |

## Notes

- WeChat sending requires Windows + a logged-in WeChat desktop client on the same machine.
- Configure `DEEPSEEK_API_KEY` via the `.env` file; never hardcode keys in source.
- If sending jumps to a "Search" page, make sure the target contact is already in the WeChat session list (the app prefers clicking it directly from the session list).
- Switching the UI language (EN / 中文) changes the display language of results and generated messages.
