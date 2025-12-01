# ShowEasy.ai 平台上下文文件

此目錄包含 ShowEasy.ai 活動平台客戶服務代理的模組化上下文檔案。

## 關於 Show Easy Group

**ShowEasy.ai** 是 **Show Easy Group** 的 AI 驅動售票及會員平台,這是一家總部位於香港的公司,致力於支持表演藝術生態系統。

### Show Easy Group 的三大核心業務

1. **DDC 創意內容**: 從概念到舞台支持香港原創表演 IP 開發
2. **表演主題場地**: 結合餐飲與原創表演體驗的餐廳
3. **Show Easy 會員及售票 AI 平台** (ShowEasy.ai): 連接觀眾與創作者的科技驅動平台

### 使命
幫助香港所有的夢想家——無論是在台前還是幕後——找到屬於自己的舞台,同時創造在國際文化舞台上代表香港的標誌性表演。

## 上下文檔案概覽

### 核心上下文(已重構優化)
1. **[01_mission_and_vision.md](01_mission_and_vision.md)** - ShowEasy 的核心使命、願景、對香港原創的支持和未來目標
2. **[02_business_model.md](02_business_model.md)** - 商業模式、收入來源、商戶合作和價值主張
3. **[03_platform_features.md](03_platform_features.md)** - 平台功能、活動探索、票務管理、AI 助手和用戶體驗
4. **[04_values_and_culture.md](04_values_and_culture.md)** - 核心價值觀、企業文化和 Show Easy Group 簡介
5. **[05_tech_infrastructure.md](05_tech_infrastructure.md)** - 技術架構、AI 系統、雲端平台、安全保障和 OMO 整合
6. **[06_membership_program.md](06_membership_program.md)** - 會員等級、優惠、定價、推廣策略和價值計算
7. **[07_event_categories.md](07_event_categories.md)** - 活動類別、香港原創內容、Meta Stages 和 AI 推薦
8. **[08_customer_service.md](08_customer_service.md)** - 客戶服務理念、語氣風格、應對策略和多語言支援
9. **[09_contact_information.md](09_contact_information.md)** - 聯絡方式、辦公室位置、升級處理和範例回覆

### 文件結構
所有文件採用統一的 **Summary + Details** 結構:
- **## Summary** - 簡要概述文件內容、何時使用
- **## Details** - 完整的詳細信息

這種結構支持 AI 的多跳文檔檢索 (multi-hop retrieval)，提高效率和準確性。

## 使用方式

這些上下文檔案由 `DocumentSummary` 和 `DocumentDetail` 工具載入，採用多跳檢索 (multi-hop retrieval) 策略:

### 兩階段檢索流程:
1. **DocumentSummary** - 首先獲取所有文件的摘要
2. **DocumentDetail** - 根據需求獲取特定文件的詳細內容

### 優勢:
- **高效檢索** - 僅載入相關文件，減少令牌使用量 (50-70%)
- **易於維護** - 更新特定文件不影響其他部分
- **智能快取** - 文件內容被快取以提高效能
- **高度可擴展** - 新增文件只需更新 DOC_ID_MAP
- **透明推理** - AI 明確顯示查閱了哪些文件

## 對開發者

新增新文檔:
1. 建立新 markdown 檔案，使用序號命名 (例如 `10_refund_policies.md`)
2. **必須**包含 `## Summary` 和 `## Details` 兩個部分
3. 在 Summary 中包含:
   - Document ID
   - 主題說明
   - 核心內容列表
   - 何時使用本文件
4. 更新 `src/app/llm/tools/DocumentDetail.py` 的 `DOC_ID_MAP`
5. 更新此 README 的文件列表
6. 工具將自動發現並使用新文檔

## 版本
- **最後更新**: 2025-12-01
- **版本**: 2.0
- **重大變更**:
  - 重構為 9 個模塊化文件 (原 5 個)
  - 所有文件採用 Summary + Details 結構
  - 支持多跳文檔檢索 (multi-hop retrieval)
  - 優化 token 使用效率 (減少 50-70%)
