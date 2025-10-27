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

### 核心上下文(目前可用)
1. **[01_platform_overview.md](01_platform_overview.md)** - Show Easy Group 生態系統、平台使命、商業模式和價值主張
2. **[02_membership_program.md](02_membership_program.md)** - 會員優惠、定價、推廣策略以及如何支持香港創作者
3. **[03_event_categories.md](03_event_categories.md)** - 活動類型、類別、香港原創內容優先和表演主題場地
4. **[04_customer_service.md](04_customer_service.md)** - 與 Show Easy Group 使命一致的服務理念、語調、聲音和原則
5. **[05_contact_information.md](05_contact_information.md)** - 聯絡詳情、回應時間、升級指南以及何時提供聯絡資訊

### 計劃中的上下文(待建立)
6. **[06_business_scope.md](06_business_scope.md)** - 範圍內 vs 範圍外的界限
7. **[07_response_guidelines.md](07_response_guidelines.md)** - 回應範本、格式和範例
8. **[08_security_compliance.md](08_security_compliance.md)** - 安全政策、合規性和防護欄
9. **[09_user_journeys.md](09_user_journeys.md)** - 常見使用者流程和場景
10. **[10_brand_voice.md](10_brand_voice.md)** - 品牌聲音範例、應做和不應做的事

## 使用方式

這些上下文檔案由 `GetPlatformContext` 工具載入,根據以下內容向 AI 代理提供相關背景資訊:
- 使用者意圖
- 對話主題
- 當前任務

模組化方法允許:
- **選擇性載入** - 僅載入相關上下文,減少令牌使用量
- **易於維護** - 更新特定部分而不影響其他部分
- **快取** - 經常存取的上下文被快取以提高效能
- **可擴展性** - 在不重組結構的情況下新增新的上下文類型

## 對開發者

新增新上下文:
1. 建立一個具有描述性名稱的新 markdown 檔案(例如 `10_refund_policies.md`)
2. 使用描述更新此 README
3. 如有需要,更新 `src/app/utils/context_loader.py` 主題映射
4. 上下文將自動提供給代理

## 版本
- **最後更新**: 2025-10-19
- **版本**: 1.1
- **變更**: 新增 05_contact_information.md,包含完整的聯絡詳情和升級指南
