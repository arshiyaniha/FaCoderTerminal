# FaCoderTerminal

FaCoderTerminal یک برنامه Python-first برای ویندوز است که درخواست‌های فارسی کاربر را به دستورهای امن و تعریف‌شده در Knowledge Base تبدیل می‌کند. ظاهر نسخه اول شبیه Windows Terminal طراحی شده است: فضای تیره، تب‌های بالا، خروجی مونو، ورودی فارسی و پنل تنظیمات LLM.

## اصول طراحی

- LLM فقط `command_id` پیشنهاد می‌دهد، نه دستور آزاد.
- اجرای خارج از Command Catalog ممنوع است.
- عملیات حساس قبل از اجرا نیازمند تأیید کاربر هستند.
- UI فارسی و راست‌چین است؛ ناحیه خروجی فنی چپ‌به‌راست می‌ماند.
- Base URL، API Key و Model از تنظیمات قابل تغییر هستند.

## نصب و اجرا

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

## وضعیت نسخه فعلی

این نسخه یک MVP اولیه است و شامل موارد زیر می‌شود:

- رابط گرافیکی شبیه Windows Terminal با pywebview
- Command Catalog بر پایه JSON
- تشخیص فارسی محلی با aliases
- fallback به LLM آنلاین OpenAI-compatible
- اجرای کنترل‌شده با subprocess بدون shell آزاد
- Security Layer با risk و confirmation
- ذخیره history و settings در پوشه محلی کاربر

## مسیر تنظیمات محلی

تنظیمات و history در این مسیر ذخیره می‌شوند:

```text
%USERPROFILE%\.facoderterminal
```

## نکته امنیتی

نسخه MVP هنوز برای اجرای عملیات مهم روی پروژه‌های production مناسب نیست مگر بعد از review و تست. هیچ secret واقعی را در repo commit نکنید.
