# TW_Stock_Report

台股多角色團隊深度研究報告存放庫。

**📊 報告索引首頁：** https://tyler0563214.github.io/TW_Stock_Report/

## 內容

- **個股深度報告** — `{代號}_report_{YYYYMMDD}.html`
  14 區塊結構：核心結論 / KPI / 財務趨勢圖 / 公司概覽 / 基本面 / 籌碼面 / 技術面 /
  融資融券 / 研究員辯論 / 風控六維評分 / 三段式策略 / 名詞小教室 / 免責聲明
- **大盤盤勢報告** — `premarket-` 早盤、`intraday-` 盤中、`postmarket-` / `eod-` 盤後

## 更新索引

新增報告後執行，會自動從各報告的 `<title>` 取出公司名稱重建索引：

```bash
python build_index.py
```

## 資料來源

富果 Fugle API（即時報價）· FinMind（K線 / 月營收 / 財報 / 融資融券）·
台灣證交所 T86（三大法人）· WebSearch（法人評等與產業資訊）

> ⚠️ 所有報告僅供研究與資訊參考，**不構成投資建議**。投資有風險，請自行判斷並承擔盈虧。
