from app.core.job_manager import log, job_manager
from app.core import config
import requests

class NotificationManager:
    @staticmethod
    def send_notification(message):
        conf = config.load_config()

        # Discord
        discord_url = conf.get('discord_webhook')
        if discord_url:
            try:
                requests.post(discord_url, json={"content": message})
            except Exception as e:
                log(f"Failed to send Discord notification: {e}")

        # Telegram
        tg_token = conf.get('telegram_token')
        tg_chat = conf.get('telegram_chat_id')
        if tg_token and tg_chat:
            try:
                url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                requests.post(url, json={"chat_id": tg_chat, "text": message})
            except Exception as e:
                log(f"Failed to send Telegram notification: {e}")
