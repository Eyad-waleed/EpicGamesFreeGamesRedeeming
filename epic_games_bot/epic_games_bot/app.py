"""
Main application module for Epic Games Freebie Auto-Claimer Bot.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

from epic_games_bot.epic import EpicGamesClient
from epic_games_bot.notifier import NotificationManager
from epic_games_bot.scheduler import Scheduler
from epic_games_bot.telegram_bot import TelegramBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('epic_games_bot.log')
    ]
)

logger = logging.getLogger(__name__)

class EpicGamesFreebieClaimer:
    """Main application class for Epic Games Freebie Auto-Claimer Bot."""
    
    def __init__(self, data_dir="./data"):
        """Initialize the application.
        
        Args:
            data_dir: Directory to store data files
        """
        # Load environment variables
        load_dotenv()
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.epic_client = EpicGamesClient(data_dir=data_dir)
        self.notifier = NotificationManager()
        self.scheduler = Scheduler()
        
        # Get credentials from environment
        self.username = os.environ.get('EPIC_USERNAME')
        self.password = os.environ.get('EPIC_PASSWORD')
        
        if not self.username or not self.password:
            logger.error("Epic Games credentials not found in environment variables")
            raise ValueError("EPIC_USERNAME and EPIC_PASSWORD environment variables are required")
        
        # Initialize Telegram bot if token is available
        self.telegram_bot = None
        telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        telegram_chat_ids = os.environ.get('TELEGRAM_CHAT_ID', '').split(',')
        
        if telegram_token and telegram_chat_ids:
            self.telegram_bot = TelegramBot(
                token=telegram_token,
                authorized_chat_ids=telegram_chat_ids,
                epic_client=self.epic_client,
                notifier=self.notifier
            )
            logger.info("Telegram bot initialized")
        
        logger.info("Epic Games Freebie Auto-Claimer initialized")
    
    def start(self):
        """Start the application."""
        logger.info("Starting Epic Games Freebie Auto-Claimer")
        
        # Send startup notification
        self.notifier.send_startup_notification()
        
        # Start scheduler
        self.scheduler.start()
        
        # Schedule daily check for free games
        self.scheduler.add_daily_job(
            self.check_and_claim_free_games,
            hour=12,  # Check at noon UTC
            minute=0,
            name="daily_free_games_check"
        )
        
        # Run immediately on startup
        self.scheduler.add_immediate_job(
            self.check_and_claim_free_games,
            name="startup_free_games_check"
        )
        
        # Start Telegram bot if available
        if self.telegram_bot:
            self.telegram_bot.start()
        
        logger.info("Epic Games Freebie Auto-Claimer started")
    
    def stop(self):
        """Stop the application."""
        logger.info("Stopping Epic Games Freebie Auto-Claimer")
        
        # Stop Telegram bot if available
        if self.telegram_bot:
            self.telegram_bot.stop()
        
        # Stop scheduler
        self.scheduler.shutdown()
        
        logger.info("Epic Games Freebie Auto-Claimer stopped")
    
    def check_and_claim_free_games(self):
        """Check for and claim free games."""
        logger.info("Checking for free games")
        
        # Ensure authenticated
        if not self.epic_client.ensure_authenticated():
            logger.info("Not authenticated, attempting login")
            success, tfa_method = self.epic_client.login(self.username, self.password)
            
            if not success:
                if tfa_method:
                    logger.error(f"2FA required ({tfa_method}). Please implement 2FA handling.")
                    self.notifier.send_error_notification(
                        f"2FA authentication required ({tfa_method}). Please check logs and provide 2FA code."
                    )
                    
                    # Register 2FA callback with Telegram bot if available
                    if self.telegram_bot:
                        self.telegram_bot.register_2fa_callback(self.handle_2fa)
                        self.telegram_bot.broadcast_message(
                            "🔐 *2FA Authentication Required*\n\n"
                            f"Please use /tfa command to enter your {tfa_method} code.",
                            parse_mode="Markdown"
                        )
                    
                    return
                else:
                    logger.error("Login failed")
                    self.notifier.send_error_notification("Failed to log in to Epic Games account")
                    return
        
        # Get free games
        free_games = self.epic_client.get_free_games()
        
        if not free_games:
            logger.info("No new free games found")
            return
        
        logger.info(f"Found {len(free_games)} new free games")
        
        # Claim each free game
        for game in free_games:
            title = game.get('title', 'Unknown Game')
            logger.info(f"Attempting to claim: {title}")
            
            if self.epic_client.claim_game(game):
                logger.info(f"Successfully claimed: {title}")
                self.notifier.send_game_claimed_notification(game)
            else:
                logger.error(f"Failed to claim: {title}")
                self.notifier.send_error_notification(f"Failed to claim free game: {title}")
    
    def handle_2fa(self, code):
        """Handle 2FA authentication.
        
        Args:
            code: 2FA code from email or authenticator app
            
        Returns:
            bool: True if 2FA was successful
        """
        logger.info("Handling 2FA authentication")
        
        if self.epic_client.complete_2fa(code):
            logger.info("2FA authentication successful")
            self.notifier.send_message("2FA authentication successful")
            
            # Check for free games after successful 2FA
            self.scheduler.add_immediate_job(
                self.check_and_claim_free_games,
                name="post_2fa_free_games_check"
            )
            
            return True
        else:
            logger.error("2FA authentication failed")
            self.notifier.send_error_notification("2FA authentication failed")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Epic Games Freebie Auto-Claimer Bot')
    parser.add_argument('--data-dir', default='./data', help='Directory to store data files')
    parser.add_argument('--2fa-code', dest='tfa_code', help='Provide 2FA code for authentication')
    args = parser.parse_args()
    
    try:
        app = EpicGamesFreebieClaimer(data_dir=args.data_dir)
        
        if args.tfa_code:
            # Handle 2FA if code provided
            app.handle_2fa(args.tfa_code)
        else:
            # Normal startup
            app.start()
            
            # Keep the main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
            finally:
                app.stop()
    
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
