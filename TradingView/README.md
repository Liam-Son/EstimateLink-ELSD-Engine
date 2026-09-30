# TradingView Integration Guide — ELSD v3 Engine

This directory contains the Pine Script (v5) implementation of the **Estimate-Link (ELSD) v3** quantitative alpha engine.

---

## 1. Quick Setup in TradingView

1. Open [TradingView Chart](https://www.tradingview.com/chart/).
2. Click the **Pine Editor** tab at the bottom.
3. Open [`TradingView/ELSD_EstimateLink_Strategy.pine`](ELSD_EstimateLink_Strategy.pine), copy the entire code, and paste it into the editor.
4. Click **Save** and then **Add to Chart**.
5. Backtest results across US equities (e.g. AAPL, NVDA, MSFT, TSLA) will automatically appear in the **Strategy Tester** tab.

---

## 2. Automated Webhook Alerts (TradingView ↔ QuantConnect / Broker)

The script comes pre-configured with JSON payloads for automated order routing via TradingView Webhooks:

- **Long Entry Payload**:
  ```json
  {"action":"BUY", "symbol":"{{ticker}}", "qty": 100, "engine":"ELSD_v3"}
  ```
- **Short Entry Payload**:
  ```json
  {"action":"SELL", "symbol":"{{ticker}}", "qty": 100, "engine":"ELSD_v3"}
  ```
- **Exit Payload**:
  ```json
  {"action":"CLOSE", "symbol":"{{ticker}}"}
  ```

### Setting Up the Webhook Alert:
1. In TradingView, right-click the chart and select **Add Alert on ELSD v3...**.
2. Condition: Select `ELSD v3 - Estimate-Link & Skew Disconnect Strategy`.
3. Alert Action: Check **Webhook URL**.
4. Enter your execution endpoint (e.g. your cloud server, AWS Lambda, or broker webhook listener).
5. In the message box, enter `{{strategy.order.alert_message}}`.

---

## 3. Connecting TradingView with GitHub

TradingView uses Pine Script, which is stored and version-controlled here in Git.

### Recommended Local Sync Workflow:
- **VS Code Extension**: Install the official `Pine Script (v5)` extension in VS Code.
- Edit your `.pine` files in this repository.
- Commit and push to GitHub:
  ```bash
  git add TradingView/
  git commit -m "feat(tradingview): tune liquidity gate and trailing stop parameters"
  git push origin main
  ```
- Keep your production Pine Script synced directly with the rest of your QuantConnect and WorldQuant BRAIN research stack!
