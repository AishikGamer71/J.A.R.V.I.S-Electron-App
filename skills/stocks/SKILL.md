---
name: stocks
version: 1.0.0
description: Real-time stock prices, intraday market charts, and ticker comparison using free financial data endpoints.
author: jarvis-ecosystem
license: MIT
allowed_tools: [web_search, execute_command]
tags: [stocks, market, finance, quotes, trading]
---

# Stock & Financial Market Intelligence Skill

This skill allows JARVIS to fetch real-time stock quotes, percent changes, historical intraday points, and compare multiple ticker symbols.

## Data Providers

1. **Finnhub / Alpha Vantage / Yahoo Finance free quotes**:
   - Query current price, open, high, low, previous close, and percentage delta.
   - Example endpoints:
     - `https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?interval=5m&range=1d`

## UI Event Emission

When the user asks for stock information (e.g. "How is NVDA doing?", "Compare AAPL vs MSFT"), fetch the data and emit a `show-stock` custom event for the JARVIS Stock Widget:

```json
{
  "symbol1": "NVDA",
  "currentPrice1": 130.50,
  "percentChange1": 3.42,
  "isPositive1": true,
  "currency": "$",
  "isComparison": false,
  "chartData": [
    { "time": "09:30", "price1": 126.80 },
    { "time": "11:00", "price1": 128.40 },
    { "time": "13:00", "price1": 130.50 }
  ]
}
```

For dual comparison (e.g. `symbol2: "MSFT"`):
- Set `isComparison: true`
- Provide `symbol2`, `currentPrice2`, `percentChange2`, `isPositive2`, and populate `price2` in each item of `chartData`.
