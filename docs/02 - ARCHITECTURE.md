# 02 - ARCHITECTURE.md

# Technical Architecture — FaCoderTerminal

## 1. نمای کلی معماری

FaCoderTerminal یک برنامه Python-first برای ویندوز است که سه لایه اصلی دارد:

1. **User Interface Layer**: رابط فارسی، راست‌چین، با امکان ورود درخواست فارسی و نمایش وضعیت اجرای دستور.
2. **Intelligence & Control Layer**: تشخیص intent با LLM، اعتبارسنجی خروجی، نگاشت به command catalog، کنترل امنیتی و ساخت دستور نهایی.
3. **Execution Layer**: اتصال به PowerShell / shell ویندوز و اجرای فقط دستورهای مجاز.

اصل معماری پروژه:

> LLM فقط مجاز است intent و `command_id` پیشنهاد کند؛ اجرای دستور واقعی فقط توسط هسته امن برنامه انجام می‌شود.

## 2. دیاگرام متنی ساده

```text
[Persian User Input]
        |
        v
[UI Layer - RTL Persian Interface]
        |
        v
[Request Normalizer]
        |
        v
[Local Command Matcher] ---- found high confidence? ----> [Security Engine]
        |
        no
        v
[LLM Intent Parser]
        |
        v
[JSON Schema Validator]
        |
        v
[Command Catalog Resolver]
        |
        v
[Security Engine / Policy Check]
        |
        v
[User Confirmation for Sensitive Actions]
        |
        v
[Command Renderer]
        |
        v
[PowerShell Runner]
        |
        v
[Output Capture + Logs + History]
```

## 3. Tech Stack پیشنهادی

| بخش | انتخاب پیشنهادی | دلیل فنی / محصولی |
|---|---|---|
| Core Language | Python 3.11+ | سریع برای توسعه، مناسب ابزارسازی، خوانا برای ایجنت‌ها |
| UI | TODO: Need Owner Decision | انتخاب بین pywebview، PySide6 یا CLI-first باقی است |
| API داخلی | FastAPI در صورت انتخاب UI وبی | ارتباط تمیز بین UI و backend |
| Terminal Bridge | pywinpty یا subprocess کنترل‌شده | اتصال به shell ویندوز و گرفتن خروجی |
| Storage | SQLite | سبک، local، بدون نیاز به سرویس جدا |
| Config | Pydantic Settings یا فایل JSON/YAML validate شده | جلوگیری از تنظیمات نامعتبر |
| LLM Client | OpenAI-compatible HTTP client | پشتیبانی از Base URL، API Key، Model متغیر |
| Validation | Pydantic Models / JSON Schema | اجبار خروجی ساخت‌یافته از LLM |
| Logging | Python logging + فایل‌های session log | قابل بررسی برای debug و audit |
| Packaging | PyInstaller در فاز انتشار | خروجی exe برای Windows |

## 4. ساختار پوشه‌ها و ماژول‌ها

این ساختار پیشنهادی است و تا تأیید docs نباید پیاده‌سازی شود:

```text
FaCoderTerminal/
├── docs/
│   ├── 01 - PRD.md
│   ├── 02 - ARCHITECTURE.md
│   ├── 03 - GUIDELINES.md
│   ├── 04 - ROADMAP.md
│   └── 05 - DEBUG_LOG.md
│
├── app/
│   ├── main.py
│   ├── config/
│   │   ├── settings.py
│   │   └── secrets.py
│   ├── core/
│   │   ├── models.py
│   │   ├── errors.py
│   │   └── constants.py
│   ├── llm/
│   │   ├── client.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── parser.py
│   ├── commands/
│   │   ├── catalog_loader.py
│   │   ├── matcher.py
│   │   ├── renderer.py
│   │   └── validator.py
│   ├── security/
│   │   ├── policy_engine.py
│   │   ├── risk_levels.py
│   │   └── confirmation.py
│   ├── terminal/
│   │   ├── runner.py
│   │   ├── session.py
│   │   └── output.py
│   ├── storage/
│   │   ├── db.py
│   │   ├── repositories.py
│   │   └── migrations.py
│   └── ui/
│       └── TODO_based_on_UI_decision
│
├── knowledge_base/
│   ├── commands.git.json
│   ├── commands.github.json
│   ├── commands.codex.json
│   ├── commands.claude.json
│   ├── commands.ruflo.json
│   ├── commands.docker.json
│   ├── commands.laravel.json
│   └── commands.nextjs.json
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── logs/
└── README.md
```

## 5. اجزای اصلی سیستم

### 5.1 UI Layer

وظایف:

- دریافت درخواست فارسی کاربر.
- نمایش command تشخیص‌داده‌شده.
- نمایش risk level و توضیح فارسی.
- گرفتن تأیید قبل از اجرای عملیات حساس.
- نمایش خروجی terminal.
- مدیریت تنظیمات LLM.

الزامات فارسی:

- کل UI باید راست‌چین باشد.
- ورودی فارسی باید بدون مشکل تایپ شود.
- ناحیه ترمینال باید LTR باقی بماند.
- فونت فارسی باید از تنظیمات قابل انتخاب باشد.

### 5.2 Request Normalizer

وظایف:

- حذف فاصله‌های اضافی.
- یکسان‌سازی نیم‌فاصله‌ها.
- تبدیل اعداد فارسی/عربی به فرم قابل پردازش در صورت نیاز.
- حفظ متن اصلی برای history.

### 5.3 Local Command Matcher

قبل از LLM اجرا می‌شود تا هزینه کاهش یابد.

رفتار:

- اگر درخواست کاربر دقیقاً یا تقریباً با aliasهای فارسی موجود در KB منطبق بود، همان command_id انتخاب شود.
- اگر confidence پایین بود، درخواست به LLM فرستاده شود.

دلیل فنی:

- کاهش هزینه LLM.
- افزایش سرعت برای دستورهای تکراری.
- کاهش وابستگی به اینترنت.

### 5.4 LLM Intent Parser

وظیفه:

- دریافت درخواست فارسی کاربر.
- دریافت لیست محدود commandهای مرتبط از KB.
- انتخاب بهترین command_id.
- تولید JSON استاندارد.

LLM نباید:

- دستور خام جدید بسازد.
- command_id خارج از catalog پیشنهاد دهد.
- تصمیم امنیتی نهایی بگیرد.
- عملیات سیستمی را مستقیم اجرا کند.

### 5.5 JSON Schema Validator

هر پاسخ LLM باید با schema معتبر شود.

فیلدهای پیشنهادی:

| فیلد | نوع | توضیح |
|---|---|---|
| type | string | مقدار ثابت `command_intent` |
| command_id | string | شناسه موجود در catalog |
| args | object | آرگومان‌های مجاز |
| confidence | number | عدد بین 0 و 1 |
| risk_hint | string | پیشنهاد مدل، نه تصمیم نهایی |
| explanation_fa | string | توضیح فارسی برای کاربر |
| needs_clarification | boolean | نیاز به سؤال تکمیلی |

اگر schema نامعتبر باشد، اجرای دستور ممنوع است.

### 5.6 Command Catalog Resolver

وظیفه:

- بررسی وجود command_id.
- خواندن command template.
- validate کردن args.
- ساخت یک plan قابل نمایش به کاربر.

### 5.7 Security Engine

وظیفه:

- تعیین risk نهایی از روی catalog، args، project context و policy.
- توقف عملیات blocklisted.
- الزام confirmation برای عملیات sensitive.
- جلوگیری از اجرای دستور خام خارج از catalog.

### 5.8 Command Renderer

وظیفه:

- تبدیل command template به دستور نهایی shell.
- escape کردن آرگومان‌ها.
- جلوگیری از injection.
- نمایش دستور نهایی قبل از اجرا.

### 5.9 Terminal Runner

وظیفه:

- اجرای دستور در PowerShell یا shell انتخابی.
- تعیین working directory.
- گرفتن stdout و stderr.
- مدیریت timeout.
- ذخیره session output.

## 6. جریان داده از ورودی کاربر تا اجرای دستور

1. کاربر درخواست فارسی وارد می‌کند.
2. UI متن را به backend می‌فرستد.
3. Normalizer متن را آماده می‌کند.
4. Local matcher در aliases فارسی جست‌وجو می‌کند.
5. اگر match کافی نبود، LLM فراخوانی می‌شود.
6. خروجی LLM با schema validate می‌شود.
7. command_id در catalog پیدا می‌شود.
8. Security Engine ریسک را محاسبه می‌کند.
9. اگر عملیات sensitive بود، UI تأیید می‌گیرد.
10. Renderer دستور نهایی را می‌سازد.
11. Runner دستور را در PowerShell اجرا می‌کند.
12. خروجی در UI، history و logs ذخیره می‌شود.

## 7. نحوه اتصال به Terminal / PowerShell

### 7.1 حالت MVP

برای MVP، اجرای دستورها می‌تواند non-interactive باشد:

- اجرای یک command مشخص.
- گرفتن خروجی.
- ذخیره نتیجه.
- نمایش stdout/stderr.

مزیت:

- ساده‌تر و امن‌تر.
- برای commandهای catalog کافی است.
- کنترل timeout و log آسان‌تر است.

### 7.2 حالت پیشرفته

برای نسخه بعدی، terminal session تعاملی لازم است:

- session زنده PowerShell.
- نمایش لحظه‌ای خروجی.
- امکان چند tab.
- history هر session.

گزینه‌های فنی:

| گزینه | مزیت | ریسک |
|---|---|---|
| subprocess کنترل‌شده | ساده برای MVP | تعامل کامل ندارد |
| pywinpty | مناسب terminal تعاملی ویندوز | پیچیدگی بیشتر |
| ConPTY wrapper | نزدیک‌تر به terminal واقعی | توسعه پیچیده‌تر |

تصمیم پیشنهادی:

- MVP: runner کنترل‌شده و ساده.
- بعد از MVP: terminal تعاملی با pywinpty/ConPTY.

## 8. نحوه ارتباط با LLM

### 8.1 تنظیمات مورد نیاز

| تنظیم | توضیح |
|---|---|
| provider_type | مثل openai_compatible |
| base_url | آدرس API provider |
| api_key | کلید محرمانه |
| model | نام مدل |
| temperature | برای intent parsing بهتر است 0 باشد |
| max_tokens | محدود برای کاهش هزینه |
| timeout_seconds | جلوگیری از معطل شدن UI |
| json_mode | در صورت پشتیبانی provider فعال شود |

### 8.2 Prompt Strategy

Prompt باید:

- فارسی کاربر را دریافت کند.
- فقط commandهای candidate را ببیند.
- فقط JSON برگرداند.
- در صورت ابهام `needs_clarification = true` بدهد.
- command_id خارج از catalog نسازد.

### 8.3 کاهش هزینه

- ابتدا local matching.
- ارسال فقط candidate commandها، نه کل KB.
- caching نتیجه درخواست‌های پرتکرار.
- مدل سبک برای intent parsing.
- مدل جدا برای تحلیل خروجی، در صورت نیاز.

## 9. ساختار تنظیمات

تنظیمات باید به دو دسته تقسیم شوند:

### 9.1 تنظیمات غیرمحرمانه

نمونه فیلدها:

- selected_provider
- base_url
- model
- temperature
- max_tokens
- default_shell
- ui_language
- font_family
- terminal_font
- default_project_path

محل ذخیره پیشنهادی:

- فایل local settings یا SQLite.

### 9.2 تنظیمات محرمانه

- api_key
- tokenها
- future provider secrets

قانون:

- در لاگ چاپ نشوند.
- در UI mask شوند.
- در MVP محل ذخیره نیاز به تصمیم مالک دارد.

TODO: Need Owner Decision: ذخیره API Key در Windows Credential Manager، فایل encrypted local یا روش ساده موقت برای MVP.

## 10. طراحی Command Parser

Command Parser شامل دو مسیر است:

### 10.1 مسیر Local

- استفاده از title_fa و aliases_fa.
- محاسبه شباهت متن.
- اگر confidence بالا بود، command_id انتخاب می‌شود.

### 10.2 مسیر LLM

- دریافت request normalized.
- دریافت candidate commands از retriever.
- گرفتن JSON.
- validate کردن خروجی.

قانون:

- Parser هیچ‌وقت command خام را اجرا نمی‌کند.
- Parser فقط plan تولید می‌کند.

## 11. طراحی Knowledge Base

هر ابزار باید فایل جدا داشته باشد.

ساختار پیشنهادی هر command:

```json
{
  "id": "git.status",
  "tool": "git",
  "title_fa": "بررسی وضعیت گیت",
  "aliases_fa": ["وضعیت گیت", "گیت را چک کن"],
  "description_fa": "وضعیت تغییرات ریپازیتوری فعلی را نمایش می‌دهد.",
  "command_template": "git status",
  "risk": "safe",
  "requires_confirmation": false,
  "category": "version_control",
  "args_schema": {},
  "platforms": ["windows"],
  "tags": ["git", "status"]
}
```

نکات:

- command_id باید یکتا باشد.
- risk الزامی است.
- command_template فقط از KB می‌آید.
- aliases_fa برای local matching استفاده می‌شود.
- args_schema برای جلوگیری از injection لازم است.

## 12. طراحی Plugin / Tool System

برای MVP، plugin system کامل لازم نیست. اما KB باید طوری طراحی شود که در آینده plugin شود.

پیشنهاد:

- هر tool یک فایل manifest داشته باشد.
- هر manifest شامل name، version، commands و requirements باشد.
- در آینده loader بتواند pluginها را فعال/غیرفعال کند.

نمونه ابزارهای اولیه:

| Tool | هدف |
|---|---|
| git | وضعیت، diff، branch، log |
| github | issue، pr، repo با CLI |
| codex | اجرای promptهای کدنویسی کنترل‌شده |
| claude | بررسی پروژه و تولید گزارش با محدودیت |
| ruflo | کار با MCP و orchestration |
| docker | وضعیت containerها و compose |
| laravel | cache، route، migrate با کنترل |
| nextjs | dev، build، lint |

## 13. طراحی Error Handling

خطاها باید دسته‌بندی شوند:

| کد خطا | دسته | نمونه وضعیت |
|---|---|---|
| CONFIG_ERROR | تنظیمات | Base URL خالی یا مدل نامعتبر |
| LLM_ERROR | LLM | timeout، پاسخ نامعتبر، JSON خراب |
| CATALOG_ERROR | KB | command_id ناموجود یا schema ناقص |
| SECURITY_BLOCK | امنیت | policy اجازه اجرا نمی‌دهد |
| TERMINAL_ERROR | اجرا | shell در دسترس نیست یا command fail شده |
| STORAGE_ERROR | ذخیره‌سازی | خطای SQLite یا فایل |
| UI_ERROR | رابط | مشکل نمایش یا ورودی |

هر خطا باید شامل این اطلاعات باشد:

- timestamp
- request_id
- module
- error_code
- message_fa
- technical_message
- safe_context
- suggested_action

## 14. طراحی Logging

### 14.1 چه چیزهایی log شود

- request_id
- متن کاربر، در صورت فعال بودن history
- command_id انتخاب‌شده
- risk level
- نتیجه confirmation
- وضعیت اجرا
- exit code
- خلاصه stdout/stderr
- خطاهای LLM

### 14.2 چه چیزهایی log نشود

- API Key
- tokenها
- secretها
- محتوای فایل‌های حساس
- مقدار کامل envهای محرمانه

### 14.3 سطوح log

| سطح | کاربرد |
|---|---|
| DEBUG | توسعه و عیب‌یابی |
| INFO | جریان طبیعی برنامه |
| WARNING | ریسک یا حالت قابل توجه |
| ERROR | خطای قابل بازیابی |
| CRITICAL | خطای جدی یا توقف برنامه |

## 15. طراحی Security Layer

### 15.1 Risk Levels

| سطح | توضیح | رفتار |
|---|---|---|
| safe | فقط خواندن یا بررسی وضعیت | اجرا بدون تأیید |
| medium | ممکن است تغییر محدود ایجاد کند | نمایش plan و تأیید سبک |
| dangerous | تغییر گسترده یا حساس | تأیید صریح و توضیح ریسک |
| blocked | ممنوع | هرگز اجرا نشود |

### 15.2 جلوگیری از اجرای دستورات خطرناک

قوانین:

- اجرای دستور خارج از catalog ممنوع است.
- command_template باید از KB معتبر بیاید.
- args باید با schema معتبر شوند.
- عملیات حذف گسترده، reset، پاکسازی گسترده، تغییر دیتابیس، تغییر مجوزها و تغییر فایل‌های حساس باید policy جدا داشته باشند.
- اگر policy و catalog اختلاف داشتند، سطح ریسک بالاتر انتخاب شود.

### 15.3 تأیید کاربر

برای عملیات sensitive UI باید نشان دهد:

- عنوان فارسی عملیات.
- ابزار هدف.
- مسیر پروژه.
- دستور نهایی قابل نمایش.
- دلیل حساس بودن.
- دکمه اجرا / لغو.

در نسخه‌های بعدی برای عملیات dangerous می‌توان عبارت تأیید متنی اضافه کرد.

## 16. معماری ذخیره‌سازی داده‌ها

### 16.1 SQLite Tables پیشنهادی

| جدول | هدف |
|---|---|
| settings | تنظیمات غیرمحرمانه |
| projects | مسیرها و پروفایل پروژه‌ها |
| command_history | درخواست‌ها، command_id، زمان، خروجی |
| llm_requests | اطلاعات غیرمحرمانه درخواست‌های LLM |
| sessions | sessionهای terminal |
| kb_versions | نسخه KBهای بارگذاری‌شده |
| errors | خطاهای مهم برنامه |

### 16.2 نگهداری history

- history باید قابل پاک‌سازی باشد.
- ذخیره متن کامل خروجی باید قابل غیرفعال‌سازی باشد.
- خروجی‌های طولانی باید خلاصه شوند یا در فایل جدا ذخیره شوند.

## 17. معماری توسعه‌پذیری

اصول:

- ابزار جدید با KB جدید اضافه شود.
- هسته parser مستقل از ابزار باشد.
- Security Engine مستقل از UI باشد.
- LLM Client قابل تعویض باشد.
- Storage قابل migration باشد.
- UI بتواند بدون تغییر core تغییر کند.

## 18. تصمیمات فنی مهم و دلیل هر تصمیم

| تصمیم | دلیل فنی | دلیل محصولی |
|---|---|---|
| Python-first | توسعه سریع، ابزارسازی ساده | مناسب MVP و قابل فهم برای تیم |
| LLM فقط برای intent | کاهش ریسک hallucination | افزایش اعتماد کاربر |
| catalog-only execution | کنترل کامل دستورها | جلوگیری از عملیات اشتباه |
| PowerShell در MVP | هدف اصلی ویندوز است | شروع سریع و کاربردی |
| SQLite | ساده و local | بدون نیاز به نصب سرویس |
| UI فارسی RTL + terminal LTR | سازگاری با فارسی و commandها | تجربه کاربری بهتر |
| JSON Schema Validation | جلوگیری از خروجی مبهم LLM | قابل تست و قابل اطمینان |
| Risk-based confirmation | کنترل عملیات حساس | کاهش خطای انسانی |

## 19. Assumptions

- Assumption: نسخه اول فقط Windows را هدف می‌گیرد.
- Assumption: LLM provider با API سازگار با chat completion قابل استفاده است.
- Assumption: کاربر ابزارهای CLI خارجی را خودش نصب می‌کند.
- Assumption: در MVP اجرای interactive کامل terminal ضروری نیست.
- Assumption: owner تأیید خواهد کرد که اجرای خارج از catalog ممنوع باشد.

## 20. TODO: Need Owner Decision

- [ ] انتخاب UI: pywebview، PySide6 یا CLI-first.
- [ ] انتخاب روش ذخیره API Key.
- [ ] تعیین حداقل ابزارهای KB در MVP.
- [ ] تعیین سطح history: ذخیره کامل خروجی یا فقط خلاصه.
- [ ] تعیین اینکه آیا برنامه از ابتدا نصب‌کننده exe داشته باشد یا نه.

## 21. Next Actions

1. تأیید اصل معماری catalog-only execution.
2. تصمیم درباره UI framework.
3. نهایی‌کردن schema خروجی LLM.
4. نهایی‌کردن risk policy.
5. پس از تأیید پنج سند، ایجاد اسکلت پروژه بدون منطق اجرایی پیچیده.
