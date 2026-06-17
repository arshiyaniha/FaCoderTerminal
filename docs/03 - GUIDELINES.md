# 03 - GUIDELINES.md

# Development Guidelines — FaCoderTerminal

## 1. هدف این سند

این سند قانون داخلی توسعه FaCoderTerminal است. هر توسعه‌دهنده یا ایجنتی که روی پروژه کار می‌کند باید قبل از تغییر کد، این سند را رعایت کند.

اصل اصلی پروژه:

> امنیت، کنترل کاربر و قابل پیش‌بینی بودن رفتار برنامه از سرعت توسعه مهم‌تر است.

تا زمانی که پنج سند اولیه تأیید نشده‌اند، پیاده‌سازی اصلی پروژه نباید شروع شود.

## 2. قوانین کدنویسی

- کد باید ساده، خوانا، قابل تست و قابل review باشد.
- هر ماژول باید فقط یک مسئولیت مشخص داشته باشد.
- هیچ بخش از برنامه نباید متن آزاد کاربر یا خروجی آزاد LLM را مستقیم به shell بدهد.
- تمام ورودی‌های کاربر، LLM، فایل‌های Knowledge Base و تنظیمات باید validate شوند.
- type hints برای کد Python الزامی است.
- منطق امنیتی باید مستقل از UI باشد.
- اگر بین سرعت و امنیت تعارض بود، امنیت اولویت دارد.

## 3. Naming Convention

| نوع | قانون | مثال |
|---|---|---|
| فایل Python | snake_case | `command_parser.py` |
| کلاس | PascalCase | `CommandParser` |
| تابع | snake_case | `parse_user_request` |
| ثابت | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT_SECONDS` |
| command_id | tool.action | `git.status` |
| فایل KB | commands.tool.json | `commands.github.json` |
| جدول SQLite | snake_case plural | `command_history` |
| فیلد JSON | snake_case | `requires_confirmation` |

قانون محصولی:

- نام‌های داخلی و command_idها انگلیسی باشند.
- متن‌های نمایشی، خطاها و توضیحات کاربر فارسی باشند.

## 4. قوانین ساخت فایل و پوشه

- مستندات در `docs/` نگهداری شوند.
- Knowledge Base در پوشه جدا از core قرار بگیرد.
- فایل‌های runtime، لاگ‌ها و خروجی‌های موقت وارد repo نشوند.
- فایل‌های تنظیمات واقعی شامل کلیدهای محرمانه وارد repo نشوند.
- هر ابزار جدید باید فایل KB جدا یا manifest جدا داشته باشد.
- فایل‌های بزرگ و چندمنظوره ممنوع‌اند.

## 5. قوانین نوشتن کامنت

کامنت باید دلیل تصمیم را توضیح دهد، نه بدیهیات را.

مجاز:

- توضیح دلیل یک تصمیم امنیتی.
- توضیح محدودیت ویندوز یا PowerShell.
- توضیح دلیل reject کردن پاسخ LLM.
- توضیح edge case.

غیرمجاز:

- کامنت‌های بدیهی.
- کامنت‌های قدیمی و ناسازگار با کد.
- مستندسازی طولانی داخل کد به جای docs.

## 6. قوانین مدیریت خطا

خطاها باید دسته‌بندی شوند:

| دسته | کاربرد |
|---|---|
| CONFIG_ERROR | تنظیمات ناقص یا نامعتبر |
| LLM_ERROR | خطای provider، timeout یا پاسخ نامعتبر |
| CATALOG_ERROR | مشکل در Knowledge Base یا command_id |
| SECURITY_BLOCK | رد شدن عملیات توسط policy |
| TERMINAL_ERROR | خطای shell یا اجرای دستور |
| STORAGE_ERROR | خطای دیتابیس یا فایل |
| UI_ERROR | خطای رابط کاربری |

هر خطا باید دو پیام داشته باشد:

1. پیام فارسی کوتاه برای کاربر.
2. پیام فنی امن برای log.

هیچ پیام خطا نباید مقدار کامل API Key، token یا داده محرمانه را نشان دهد.

## 7. قوانین لاگ‌گیری

### 7.1 موارد مجاز برای log

- request_id
- زمان درخواست
- module اجراشده
- command_id انتخاب‌شده
- risk level
- نتیجه تأیید کاربر
- exit code
- خلاصه امن خروجی
- نسخه Knowledge Base

### 7.2 موارد ممنوع برای log

- API Key
- token
- اطلاعات احراز هویت
- محتوای محرمانه فایل‌ها
- مقدار کامل متغیرهای محیطی حساس

### 7.3 Masking

هر مقدار محرمانه قبل از نمایش یا ذخیره باید mask شود.

نمونه امن:

```text
sk-************abcd
```

## 8. قوانین امنیتی

- اجرای دستور خارج از Command Catalog ممنوع است.
- خروجی LLM فقط بعد از schema validation قابل استفاده است.
- هر command باید risk level داشته باشد.
- عملیات sensitive باید confirmation داشته باشند.
- عملیات blocklisted باید بدون امکان ادامه متوقف شوند.
- Security Engine باید مستقل از UI و LLM باشد.
- اگر catalog و policy اختلاف داشتند، policy سخت‌گیرانه‌تر ملاک است.

## 9. قوانین کار با LLM

LLM فقط مجاز است:

- intent کاربر را تشخیص دهد.
- از بین commandهای candidate یک command_id انتخاب کند.
- args محدود و validateپذیر تولید کند.
- توضیح فارسی کوتاه بدهد.
- در صورت ابهام اعلام کند clarification لازم است.

LLM مجاز نیست:

- دستور shell آزاد تولید کند.
- command_id جدید اختراع کند.
- تصمیم امنیتی نهایی بگیرد.
- secret درخواست کند.
- محتوای پروژه را بدون اجازه کاربر برای provider بفرستد.

تنظیمات پیشنهادی:

| گزینه | مقدار پیشنهادی MVP |
|---|---|
| temperature | 0 |
| max_tokens | محدود |
| timeout | فعال |
| response format | JSON |
| provider | قابل تغییر از Settings |

## 10. قوانین جلوگیری از Hallucination

- LLM فقط candidate commandها را دریافت می‌کند.
- command_id خارج از catalog رد می‌شود.
- JSON نامعتبر رد می‌شود.
- confidence پایین باعث اجرا نمی‌شود.
- args باید با schema سازگار باشند.
- توضیح LLM جایگزین policy یا catalog نمی‌شود.

Threshold پیشنهادی:

| confidence | رفتار |
|---|---|
| 0.85 به بالا | ادامه به security check |
| 0.60 تا 0.84 | نمایش پیشنهاد و گرفتن تأیید |
| کمتر از 0.60 | درخواست clarification |

## 11. قوانین اجرای دستورات سیستمی

- دستور نهایی فقط از command_template معتبر ساخته شود.
- args باید validate و escape شوند.
- working directory باید مشخص و قابل نمایش باشد.
- timeout باید تعریف شود.
- stdout و stderr باید جدا ذخیره شوند.
- قبل از عملیات sensitive، plan باید به کاربر نمایش داده شود.
- اجرای چندمرحله‌ای بدون plan ممنوع است.

## 12. قوانین تست‌نویسی

### 12.1 تست‌های الزامی

| بخش | نوع تست |
|---|---|
| Command Catalog Loader | unit test |
| JSON Schema Validator | unit test |
| Security Engine | unit test |
| LLM Parser | mock-based test |
| Command Renderer | unit test |
| Terminal Runner | integration test محدود |
| Persian Normalizer | unit test |

### 12.2 تست‌های امنیتی

- command_id ناموجود باید رد شود.
- JSON نامعتبر باید رد شود.
- عملیات sensitive بدون confirmation اجرا نشود.
- args غیرمجاز رد شود.
- مقدار محرمانه در log دیده نشود.
- policy باید از catalog سخت‌گیرانه‌تر باشد.

### 12.3 Test Fixtures فارسی

برای تست فارسی باید fixtureهای زیر ساخته شود:

- درخواست ساده.
- درخواست مبهم.
- درخواست حساس.
- درخواست خارج از scope.
- درخواست با غلط املایی.
- درخواست ترکیبی فارسی/انگلیسی.

## 13. قوانین مستندسازی

- هر feature جدید باید در docs مربوطه ثبت شود.
- هر command جدید باید description_fa داشته باشد.
- هر risk policy جدید باید دلیل داشته باشد.
- هر تغییر معماری باید در Architecture و Debug Log ثبت شود.
- README فقط خلاصه پروژه است و جایگزین docs اصلی نیست.

## 14. قوانین Commit Message

فرمت:

```text
<type>: <short description>
```

Typeهای مجاز:

| Type | کاربرد |
|---|---|
| docs | مستندات |
| feat | قابلیت جدید |
| fix | رفع باگ |
| refactor | بازآرایی بدون تغییر رفتار |
| test | تست |
| chore | نگهداری |
| security | تغییرات امنیتی |
| kb | تغییر Knowledge Base |

نمونه:

```text
docs: add development guidelines
kb: add git command catalog
security: enforce catalog-only execution
```

## 15. قوانین Pull Request / Review

هر PR باید شامل این موارد باشد:

- خلاصه تغییر.
- دلیل تغییر.
- تست‌های انجام‌شده.
- اثر امنیتی.
- اثر روی LLM یا KB، اگر وجود دارد.
- screenshot برای تغییر UI.
- آپدیت docs، اگر لازم است.

هیچ PR مربوط به اجرای command نباید بدون review امنیتی merge شود.

## 16. قوانین اضافه کردن Feature جدید

قبل از اضافه کردن feature:

1. هدف feature مشخص شود.
2. User Story نوشته شود.
3. Acceptance Criteria تعریف شود.
4. اثر امنیتی بررسی شود.
5. اثر روی LLM و KB بررسی شود.
6. تست‌ها اضافه شوند.
7. مستندات به‌روزرسانی شوند.

## 17. قوانین تغییر معماری

تغییر معماری فقط وقتی مجاز است که:

- مشکل واقعی حل کند.
- سیستم را ساده‌تر، امن‌تر یا قابل نگهداری‌تر کند.
- در `02 - ARCHITECTURE.md` ثبت شود.
- در `05 - DEBUG_LOG.md` به‌عنوان Technical Decision ثبت شود.
- در تغییرات پرریسک، Owner تأیید کند.

## 18. قوانین مدیریت Secret ها

- secret واقعی نباید commit شود.
- API Key نباید در log دیده شود.
- tokenها باید mask شوند.
- export/import تنظیمات نباید secret خام منتقل کند.
- در نسخه پایدار باید ذخیره امن مبتنی بر سیستم‌عامل بررسی شود.

TODO: Need Owner Decision: انتخاب روش نهایی ذخیره API Key در MVP.

## 19. قوانین سازگاری با ویندوز

- مسیرها باید با فاصله در نام پوشه سازگار باشند.
- encoding فایل‌ها باید UTF-8 باشد.
- PowerShell shell پیش‌فرض MVP است.
- مسیر پروژه قبل از اجرا validate شود.
- نصب نبودن ابزارهای خارجی باید پیام فارسی واضح داشته باشد.
- برنامه نباید به مسیر خاص یک دستگاه وابسته باشد.

## 20. قوانین فارسی، RTL و فونت فارسی

- UI فارسی باید RTL باشد.
- ناحیه terminal باید LTR باشد.
- فونت فارسی باید خوانا و قابل تعویض باشد.
- متن‌های ثابت UI در localization layer نگهداری شوند.
- ترکیب فارسی و انگلیسی باید تست شود.
- commandها و pathها نباید راست‌چین شوند.
- پیام‌های confirmation باید فارسی، کوتاه و دقیق باشند.

فونت‌های پیشنهادی:

| بخش | فونت پیشنهادی |
|---|---|
| UI فارسی | Vazirmatn، Estedad، IRANSans در صورت مجوز |
| Terminal | Cascadia Mono، Consolas، JetBrains Mono |
| Code blocks | JetBrains Mono یا Cascadia Mono |

هیچ فایل فونت اختصاصی یا غیرمجاز نباید بدون مجوز روشن وارد repo شود.

## 21. قوانین Knowledge Base

هر command باید شامل این موارد باشد:

- id
- tool
- title_fa
- aliases_fa
- description_fa
- command_template
- risk
- requires_confirmation
- category
- args_schema
- platforms

قوانین:

- command_id تکراری ممنوع است.
- command بدون aliases_fa پذیرفته نشود.
- command بدون risk پذیرفته نشود.
- commandهایی که تغییر ایجاد می‌کنند نباید safe باشند.
- KB باید version داشته باشد.
- تغییر KB باید با تست loader همراه باشد.

## 22. قوانین AI Coding Tools

برای ابزارهایی مثل Codex، Claude Code و Ruflo:

- promptهای اجرایی باید نوع عملیات را واضح مشخص کنند.
- عملیات write باید confirmation جدا داشته باشد.
- اجرای agent طولانی باید timeout یا stop button داشته باشد.
- خروجی agent باید در session history ذخیره شود.
- ارسال context پروژه به provider باید با اطلاع کاربر باشد.
- اگر ابزار نصب نیست، برنامه پیام فارسی واضح بدهد.

## 23. Assumptions

- Assumption: در MVP یک تیم کوچک روی پروژه کار می‌کند، اما قوانین باید برای ایجنت‌های آینده هم کافی باشد.
- Assumption: زبان مستندات فارسی است، اما نام ماژول‌ها و command_idها انگلیسی می‌مانند.
- Assumption: ابزارهای external CLI ممکن است نصب نباشند، پس detection لازم است.

## 24. TODO: Need Owner Decision

- [ ] انتخاب UI نهایی.
- [ ] انتخاب محل ذخیره امن API Key.
- [ ] تعیین اینکه history به‌صورت پیش‌فرض فعال باشد یا نه.
- [ ] تعیین سطح سخت‌گیری confirmation برای عملیات medium.
- [ ] تعیین اینکه commandهای read-only مربوط به AI tools بدون confirmation اجرا شوند یا نه.

## 25. Next Actions

1. این سند باید قبل از شروع کدنویسی تأیید شود.
2. هر PR باید با این قوانین بررسی شود.
3. بعد از انتخاب UI و secret storage، این سند به‌روزرسانی شود.
4. تست‌های امنیتی باید قبل از Terminal Runner نوشته شوند.
