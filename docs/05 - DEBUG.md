# 05 - DEBUG.md

> Note: The requested exact filename was `05 - DEBUG_LOG.md`. The GitHub write tool blocked that exact path. This file contains the required Debug Log content under a safe filename.

# Debug Log — FaCoderTerminal

## 1. هدف این فایل

این فایل برای ثبت خطاها، تصمیمات فنی، تغییرات مهم و تجربه‌های نصب و اجرا ساخته شده است. هر توسعه‌دهنده یا ایجنتی که روی پروژه کار می‌کند باید خطاهای مهم و تصمیمات قابل توجه را اینجا یا در GitHub Issues ثبت کند.

قانون اصلی:

> اگر خطایی باعث تغییر تصمیم فنی، تغییر معماری، تغییر policy یا تغییر روش اجرا شد، باید ثبت شود.

## 2. وضعیت اولیه پروژه

| مورد | وضعیت |
|---|---|
| نام پروژه | FaCoderTerminal |
| زبان اصلی | Python |
| سیستم‌عامل هدف MVP | Windows |
| shell هدف MVP | PowerShell |
| زبان UI | فارسی، راست‌چین |
| LLM | آنلاین، کم‌هزینه، قابل تنظیم |
| سیاست اجرا | فقط از طریق Command Catalog |
| وضعیت کدنویسی | تا تأیید docs شروع نشود |

## 3. قالب ثبت باگ

```md
## BUG-YYYYMMDD-001

- Date:
- Reporter:
- Area:
- Severity: Low / Medium / High / Critical
- Status: Open / Fixed / Ignored / Need Review
- Summary:
- Steps to Reproduce:
- Expected Result:
- Actual Result:
- Environment:
- Suspected Cause:
- Tested Fix:
- Result:
- Next Action:
```

## 4. قالب ثبت خطاهای نصب

```md
## INSTALL-YYYYMMDD-001

- Date:
- OS Version:
- Python Version:
- Install Method:
- Failed Step:
- Error Message:
- Suspected Cause:
- Fix Tried:
- Result:
- Status:
```

## 5. قالب ثبت خطاهای Runtime

```md
## RUNTIME-YYYYMMDD-001

- Date:
- Module:
- User Action:
- Request ID:
- Error Code:
- User Message FA:
- Technical Message:
- Safe Output Summary:
- Suspected Cause:
- Fix Tried:
- Result:
- Status:
```

## 6. قالب ثبت خطاهای LLM

```md
## LLM-YYYYMMDD-001

- Date:
- Provider Type:
- Base URL Host Only:
- Model:
- Request Type:
- Error Type:
- User Input Summary:
- Safe Response Summary:
- Validation Error:
- Fix Tried:
- Result:
- Status:
```

قانون: API Key یا token نباید در این فایل ثبت شود.

## 7. قالب ثبت خطاهای اتصال به Terminal

```md
## TERMINAL-YYYYMMDD-001

- Date:
- Shell:
- Working Directory:
- Command ID:
- Error Message:
- Output Summary:
- Suspected Cause:
- Fix Tried:
- Result:
- Status:
```

## 8. قالب ثبت تصمیمات فنی

```md
## DECISION-YYYYMMDD-001

- Date:
- Decision Title:
- Context:
- Options Considered:
- Final Decision:
- Reason:
- Product Impact:
- Technical Impact:
- Security Impact:
- Follow-up Tasks:
- Status:
```

## 9. قالب ثبت تغییرات مهم

```md
## CHANGE-YYYYMMDD-001

- Date:
- Area:
- Change Summary:
- Reason:
- Files Affected:
- Backward Compatibility:
- Migration Needed: Yes / No
- Tests Required:
- Status:
```

## 10. جدول خطاها

| تاریخ | بخش | شرح خطا | علت احتمالی | راه‌حل تست‌شده | نتیجه | وضعیت |
|---|---|---|---|---|---|---|
| 2026-06-18 | Docs | ساخت مستندات اولیه قبل از کدنویسی الزامی شد | نیاز به کنترل scope | ایجاد فایل‌های docs | در حال بررسی | Open |
| 2026-06-18 | Architecture | LLM فقط command_id بدهد | کاهش ریسک خروجی آزاد مدل | ثبت در PRD و Architecture | نیازمند تأیید Owner | Need Review |
| 2026-06-18 | Security | اجرای خارج از catalog در MVP مجاز نیست | نیاز به کنترل کامل عملیات | تعریف catalog-only policy | نیازمند تأیید Owner | Need Review |
| 2026-06-18 | Product | UI فارسی RTL و terminal LTR پیشنهاد شد | ترکیب زبان فارسی و commandهای فنی | ثبت در docs | تصمیم پیشنهادی | Need Review |

## 11. نمونه ورودی فرضی: خطای LLM

```md
## LLM-20260618-001

- Date: 2026-06-18
- Provider Type: openai_compatible
- Base URL Host Only: example-provider.local
- Model: low-cost-intent-model
- Request Type: intent_parse
- Error Type: invalid_json
- User Input Summary: کاربر خواسته وضعیت پروژه بررسی شود.
- Safe Response Summary: مدل متن توضیحی برگرداند، نه JSON.
- Validation Error: response was not valid JSON object
- Fix Tried: سخت‌گیرتر کردن prompt و فعال‌سازی JSON mode در صورت پشتیبانی
- Result: نیازمند تست مجدد
- Status: Need Review
```

## 12. نمونه ورودی فرضی: خطای Terminal

```md
## TERMINAL-20260618-001

- Date: 2026-06-18
- Shell: PowerShell
- Working Directory: selected project path
- Command ID: git.status
- Error Message: ابزار لازم در سیستم پیدا نشد.
- Output Summary: اجرا شروع نشد.
- Suspected Cause: ابزار نصب نیست یا در PATH قرار ندارد.
- Fix Tried: نمایش پیام فارسی و پیشنهاد بررسی نصب ابزار
- Result: Pending implementation
- Status: Open
```

## 13. نمونه ورودی فرضی: تصمیم فنی

```md
## DECISION-20260618-001

- Date: 2026-06-18
- Decision Title: استفاده از catalog-only execution در MVP
- Context: محصول باید درخواست فارسی را به عملیات قابل کنترل تبدیل کند.
- Options Considered:
  - استفاده مستقیم از متن خروجی مدل
  - استفاده فقط از commandهای تعریف‌شده در catalog
- Final Decision: استفاده فقط از commandهای catalog در MVP
- Reason: کاهش خطای مدل، افزایش امنیت، تست‌پذیری بهتر
- Product Impact: اعتماد بیشتر کاربر
- Technical Impact: نیاز به Command Catalog و Validator
- Security Impact: کاهش ریسک عملیات ناخواسته
- Follow-up Tasks: تعریف schema نهایی KB و policy
- Status: Need Review
```

## 14. قوانین نگهداری Debug Log

- هر خطای تکرارشونده باید ثبت شود.
- هر تصمیم فنی مهم باید ثبت شود.
- هر تغییری که رفتار امنیتی یا معماری را تغییر دهد باید ثبت شود.
- اطلاعات محرمانه نباید ثبت شود.
- خروجی‌های طولانی باید خلاصه شوند.
- اگر خطا در GitHub issue ثبت شد، شناسه issue در این فایل درج شود.

## 15. وضعیت‌ها

| وضعیت | معنی |
|---|---|
| Open | هنوز حل نشده است |
| Fixed | حل شده و تست شده است |
| Ignored | آگاهانه نادیده گرفته شده است |
| Need Review | نیازمند بررسی یا تصمیم Owner/Tech Lead است |

## 16. Severity

| سطح | معنی |
|---|---|
| Low | مزاحمت جزئی یا بهبود کوچک |
| Medium | خطای قابل توجه اما بدون توقف کامل |
| High | مانع استفاده از قابلیت مهم |
| Critical | ریسک امنیتی یا توقف کامل برنامه |

## 17. Assumptions

- Assumption: در ابتدای پروژه، همین فایل برای ثبت خطاها کافی است.
- Assumption: در آینده ممکن است GitHub Issues جایگزین مدیریت کامل خطا شود.
- Assumption: اطلاعات محرمانه هرگز در Debug Log ذخیره نمی‌شوند.

## 18. TODO: Need Owner Decision

- [ ] آیا Debug Log در همین فایل Markdown ادامه پیدا کند یا بعداً به GitHub Issues منتقل شود؟
- [ ] آیا خروجی کامل sessionها ذخیره شود یا فقط خلاصه امن؟
- [ ] چه مدت history و logها نگهداری شوند؟

## 19. Next Actions

1. بعد از تأیید docs، اولین تصمیم‌های Owner در همین فایل ثبت شوند.
2. با شروع فاز MVP، هر خطای نصب، LLM، terminal و security اینجا ثبت شود.
3. اگر پروژه وارد مرحله تیمی شد، GitHub Issues برای خطاهای مهم ساخته شود.
