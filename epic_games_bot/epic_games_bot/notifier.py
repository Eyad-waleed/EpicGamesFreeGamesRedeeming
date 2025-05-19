"""
Notification module for Epic Games Freebie Auto-Claimer Bot.
Handles sending notifications via Telegram and Discord.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram notification handler."""
    
    API_URL = "https://api.telegram.org/bot{token}/{method}"
    
    def __init__(self, token: str, chat_id: str):
        """Initialize Telegram notifier.
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.token = token
        self.chat_id = chat_id
        logger.info("Telegram notifier initialized")
    
    def send_message(self, message: str) -> bool:
        """Send a message via Telegram.
        
        Args:
            message: Message text to send
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            url = self.API_URL.format(token=self.token, method="sendMessage")
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_game_claimed_notification(self, game: Dict[str, Any]) -> bool:
        """Send notification about claimed game.
        
        Args:
            game: Game data dictionary
            
        Returns:
            bool: True if notification was sent successfully
        """
        title = game.get('title', 'Unknown Game')
        url = game.get('url', 'https://www.epicgames.com/store/')
        description = game.get('description', 'No description available')
        
        message = (
            f"🎮 <b>Free Game Claimed!</b>\n\n"
            f"<b>{title}</b>\n"
            f"{description[:100]}...\n\n"
            f"🔗 <a href='{url}'>View in Epic Games Store</a>"
        )
        
        return self.send_message(message)


class DiscordNotifier:
    """Discord notification handler."""
    
    def __init__(self, webhook_url: str):
        """Initialize Discord notifier.
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        logger.info("Discord notifier initialized")
    
    def send_message(self, content: str, embeds: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send a message via Discord webhook.
        
        Args:
            content: Message content
            embeds: Optional list of embeds
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            payload = {"content": content}
            if embeds:
                payload["embeds"] = embeds
            
            response = requests.post(self.webhook_url, json=payload)
            
            if response.status_code == 204:
                logger.info("Discord message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Discord message: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return False
    
    def send_game_claimed_notification(self, game: Dict[str, Any]) -> bool:
        """Send notification about claimed game.
        
        Args:
            game: Game data dictionary
            
        Returns:
            bool: True if notification was sent successfully
        """
        title = game.get('title', 'Unknown Game')
        url = game.get('url', 'https://www.epicgames.com/store/')
        description = game.get('description', 'No description available')
        
        embed = {
            "title": title,
            "description": description[:200] + "..." if len(description) > 200 else description,
            "url": url,
            "color": 5814783,  # Epic Games blue
            "footer": {
                "text": "Epic Games Freebie Auto-Claimer"
            },
            "timestamp": f"{__import__('datetime').datetime.utcnow().isoformat()}Z"
        }
        
        return self.send_message("🎮 **Free Game Claimed!**", [embed])


class NotificationManager:
    """Manages multiple notification channels."""
    
    def __init__(self):
        """Initialize notification manager."""
        self.telegram_notifier = None
        self.discord_notifier = None
        
        # Initialize Telegram notifier if credentials are available
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        if telegram_token and telegram_chat_id:
            self.telegram_notifier = TelegramNotifier(telegram_token, telegram_chat_id)
            logger.info("Telegram notifications enabled")
        
        # Initialize Discord notifier if webhook URL is available
        discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL')
        if discord_webhook:
            self.discord_notifier = DiscordNotifier(discord_webhook)
            logger.info("Discord notifications enabled")
        
        if not self.telegram_notifier and not self.discord_notifier:
            logger.warning("No notification channels configured")
    
    def send_game_claimed_notification(self, game: Dict[str, Any]) -> bool:
        """Send notification about claimed game to all configured channels.
        
        Args:
            game: Game data dictionary
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        success = False
        
        if self.telegram_notifier:
            telegram_success = self.telegram_notifier.send_game_claimed_notification(game)
            success = success or telegram_success
        
        if self.discord_notifier:
            discord_success = self.discord_notifier.send_game_claimed_notification(game)
            success = success or discord_success
        
        return success
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send error notification to all configured channels.
        
        Args:
            error_message: Error message to send
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        success = False
        
        message = f"❌ **Error**: {error_message}"
        
        if self.telegram_notifier:
            telegram_success = self.telegram_notifier.send_message(message)
            success = success or telegram_success
        
        if self.discord_notifier:
            discord_success = self.discord_notifier.send_message(message)
            success = success or discord_success
        
        return success
    
    def send_startup_notification(self) -> bool:
        """Send startup notification to all configured channels.
        
        Returns:
            bool: True if at least one notification was sent successfully
        """
        success = False
        
        message = "🚀 Epic Games Freebie Auto-Claimer Bot started!"
        
        if self.telegram_notifier:
            telegram_success = self.telegram_notifier.send_message(message)
            success = success or telegram_success
        
        if self.discord_notifier:
            discord_success = self.discord_notifier.send_message(message)
            success = success or discord_success
        
        return success
