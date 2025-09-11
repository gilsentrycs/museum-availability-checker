# Museum Availability Checker

Automated checker for Chichu Art Museum and Teshima Art Museum availability on Naoshima Island.

## Features
- Checks both museums for ticket availability
- Handles popup dismissal and iframe navigation
- Sends notifications when tickets become available
- Runs automatically every 20 minutes via GitHub Actions

## Museums Monitored
- **Chichu Art Museum**: https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/176695?language=eng
- **Teshima Art Museum**: https://benesse-artsite.eventos.tokyo/web/portal/797/event/8483/module/booth/239565/185773?language=eng

## Usage

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Check specific dates
python chichu_availability_checker.py --dates 2025-10-07

# Check both museums
python test_both_museums.py
```

### Environment Variables
Set these in GitHub Secrets for notifications:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- `EMAIL_FROM`: Sender email address
- `EMAIL_TO`: Recipient email address
- `SMTP_PASS`: Email password/app password

## Notification Types
- Desktop notifications (local only)
- Telegram messages
- Email alerts

## Current Status
Both museums are currently sold out for October 7th, 2025. The script will notify you when availability opens up.
# Museum Availability Checker - Active
