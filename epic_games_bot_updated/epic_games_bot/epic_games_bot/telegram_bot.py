"""
Telegram bot module for Epic Games Freebie Auto-Claimer Bot.
Handles interactive commands and 2FA input via Telegram.
Updated for python-telegram-bot v20+
"""

import os
import logging
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_2FA = 1

class TelegramBot:
    """Interactive Telegram bot for Epic Games Freebie Auto-Claimer."""
    
    def __init__(self, token: str, authorized_chat_ids: List[str], epic_client=None, notifier=None):
        """Initialize Telegram bot.
        
        Args:
            token: Telegram bot token
            authorized_chat_ids: List of authorized chat IDs
            epic_client: Epic Games client instance
            notifier: Notification manager instance
        """
        self.token = token
        self.authorized_chat_ids = [str(chat_id) for chat_id in authorized_chat_ids]
        self.epic_client = epic_client
        self.notifier = notifier
        
        # For storing 2FA callbacks
        self.tfa_callback = None
        
        # Initialize bot
        self.application = Application.builder().token(token).build()
        
        # Register handlers
        self._register_handlers()
        
        # For running the bot in a separate thread
        self.bot_thread = None
        
        logger.info("Telegram bot initialized")
    
    def _register_handlers(self):
        """Register command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("status", self._status_command))
        self.application.add_handler(CommandHandler("check", self._check_command))
        self.application.add_handler(CommandHandler("claim", self._claim_command))
        
        # 2FA conversation handler
        tfa_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("tfa", self._tfa_command)],
            states={
                AWAITING_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._process_2fa_code)],
            },
            fallbacks=[CommandHandler("cancel", self._cancel_command)],
        )
        self.application.add_handler(tfa_conv_handler)
        
        # Error handler
        self.application.add_error_handler(self._error_handler)
    
    def _is_authorized(self, update: Update) -> bool:
        """Check if the user is authorized to use the bot.
        
        Args:
            update: Telegram update object
            
        Returns:
            bool: True if user is authorized
        """
        chat_id = str(update.effective_chat.id)
        return chat_id in self.authorized_chat_ids
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        await update.message.reply_text(
            "🎮 *Epic Games Freebie Auto-Claimer Bot* 🎮\n\n"
            "Welcome! This bot helps you claim free games from the Epic Games Store.\n\n"
            "Use /help to see available commands.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        await update.message.reply_text(
            "🎮 *Epic Games Freebie Auto-Claimer Bot Commands* 🎮\n\n"
            "*Available Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check bot status\n"
            "/check - Check for new free games\n"
            "/claim - Manually claim all available free games\n"
            "/tfa - Enter 2FA code when prompted\n"
            "/cancel - Cancel current operation",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        if not self.epic_client:
            await update.message.reply_text("Epic Games client not connected to bot.")
            return
        
        # Check authentication status
        is_authenticated = self.epic_client.ensure_authenticated()
        
        status_message = "🎮 *Epic Games Freebie Auto-Claimer Status* 🎮\n\n"
        
        if is_authenticated:
            status_message += "✅ *Authentication:* Logged in\n"
        else:
            status_message += "❌ *Authentication:* Not logged in\n"
        
        # Add claimed games count
        claimed_count = len(self.epic_client.claimed_games)
        status_message += f"🎯 *Claimed Games:* {claimed_count}\n"
        
        await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
    
    async def _check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        if not self.epic_client:
            await update.message.reply_text("Epic Games client not connected to bot.")
            return
        
        await update.message.reply_text("🔍 Checking for free games... This may take a moment.")
        
        # Run in a separate thread to avoid blocking
        threading.Thread(target=self._check_free_games_thread, args=(update.effective_chat.id,)).start()
    
    def _check_free_games_thread(self, chat_id: int):
        """Check for free games in a separate thread.
        
        Args:
            chat_id: Telegram chat ID to send results to
        """
        try:
            # Ensure authenticated
            if not self.epic_client.ensure_authenticated():
                asyncio.run(self._send_message(
                    chat_id=chat_id,
                    text="❌ Not authenticated. Please log in first."
                ))
                return
            
            # Get free games
            free_games = self.epic_client.get_free_games()
            
            if not free_games:
                asyncio.run(self._send_message(
                    chat_id=chat_id,
                    text="✅ No new free games available to claim."
                ))
                return
            
            # Send list of free games
            message = f"🎮 *Found {len(free_games)} new free game(s):*\n\n"
            
            for i, game in enumerate(free_games, 1):
                title = game.get('title', 'Unknown Game')
                message += f"{i}. *{title}*\n"
            
            message += "\nUse /claim to claim these games."
            
            asyncio.run(self._send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            ))
        except Exception as e:
            logger.error(f"Error checking free games: {e}")
            asyncio.run(self._send_message(
                chat_id=chat_id,
                text=f"❌ Error checking free games: {str(e)}"
            ))
    
    async def _claim_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /claim command.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        if not self.epic_client:
            await update.message.reply_text("Epic Games client not connected to bot.")
            return
        
        await update.message.reply_text("🎮 Claiming free games... This may take a moment.")
        
        # Run in a separate thread to avoid blocking
        threading.Thread(target=self._claim_free_games_thread, args=(update.effective_chat.id,)).start()
    
    def _claim_free_games_thread(self, chat_id: int):
        """Claim free games in a separate thread.
        
        Args:
            chat_id: Telegram chat ID to send results to
        """
        try:
            # Ensure authenticated
            if not self.epic_client.ensure_authenticated():
                asyncio.run(self._send_message(
                    chat_id=chat_id,
                    text="❌ Not authenticated. Please log in first."
                ))
                return
            
            # Get free games
            free_games = self.epic_client.get_free_games()
            
            if not free_games:
                asyncio.run(self._send_message(
                    chat_id=chat_id,
                    text="✅ No new free games available to claim."
                ))
                return
            
            # Claim each free game
            claimed_games = []
            failed_games = []
            
            for game in free_games:
                title = game.get('title', 'Unknown Game')
                
                if self.epic_client.claim_game(game):
                    claimed_games.append(title)
                else:
                    failed_games.append(title)
            
            # Send results
            message = "🎮 *Claim Results:*\n\n"
            
            if claimed_games:
                message += "✅ *Successfully claimed:*\n"
                for i, title in enumerate(claimed_games, 1):
                    message += f"{i}. {title}\n"
                message += "\n"
            
            if failed_games:
                message += "❌ *Failed to claim:*\n"
                for i, title in enumerate(failed_games, 1):
                    message += f"{i}. {title}\n"
            
            asyncio.run(self._send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            ))
        except Exception as e:
            logger.error(f"Error claiming free games: {e}")
            asyncio.run(self._send_message(
                chat_id=chat_id,
                text=f"❌ Error claiming free games: {str(e)}"
            ))
    
    async def _tfa_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tfa command.
        
        Args:
            update: Telegram update object
            context: Callback context
            
        Returns:
            int: Conversation state
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return ConversationHandler.END
        
        if not self.epic_client:
            await update.message.reply_text("Epic Games client not connected to bot.")
            return ConversationHandler.END
        
        if not self.tfa_callback:
            await update.message.reply_text("No 2FA request pending.")
            return ConversationHandler.END
        
        keyboard = [[InlineKeyboardButton("Cancel", callback_data="cancel_2fa")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Please enter your 2FA code from your authenticator app or email:",
            reply_markup=reply_markup
        )
        
        return AWAITING_2FA
    
    async def _process_2fa_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process 2FA code input.
        
        Args:
            update: Telegram update object
            context: Callback context
            
        Returns:
            int: Conversation state
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return ConversationHandler.END
        
        code = update.message.text.strip()
        
        await update.message.reply_text(f"Received 2FA code: {code}. Processing...")
        
        # Call the 2FA callback if available
        if self.tfa_callback:
            success = self.tfa_callback(code)
            
            if success:
                await update.message.reply_text("✅ 2FA authentication successful!")
            else:
                await update.message.reply_text("❌ 2FA authentication failed. Please try again.")
            
            # Reset callback
            self.tfa_callback = None
        else:
            await update.message.reply_text("No 2FA request pending.")
        
        return ConversationHandler.END
    
    async def _cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command.
        
        Args:
            update: Telegram update object
            context: Callback context
            
        Returns:
            int: Conversation state
        """
        if not self._is_authorized(update):
            await update.message.reply_text("You are not authorized to use this bot.")
            return ConversationHandler.END
        
        await update.message.reply_text("Operation cancelled.")
        
        # Reset 2FA callback
        self.tfa_callback = None
        
        return ConversationHandler.END
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        logger.error(f"Update {update} caused error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text("An error occurred. Please try again later.")
    
    def register_2fa_callback(self, callback: Callable[[str], bool]):
        """Register a callback for 2FA code processing.
        
        Args:
            callback: Function to call with 2FA code
        """
        self.tfa_callback = callback
    
    async def _send_message(self, chat_id: str, text: str, parse_mode: str = None):
        """Send a message to a specific chat.
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (None, ParseMode.MARKDOWN, or ParseMode.HTML)
        """
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_message(self, chat_id: str, message: str, parse_mode: str = None) -> bool:
        """Send a message to a specific chat (synchronous wrapper).
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            parse_mode: Parse mode (None, 'Markdown', or 'HTML')
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            # Run the async function in a new event loop
            return asyncio.run(self._send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode
            ))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def broadcast_message(self, message: str, parse_mode: str = None) -> bool:
        """Send a message to all authorized chats.
        
        Args:
            message: Message text
            parse_mode: Parse mode (None, 'Markdown', or 'HTML')
            
        Returns:
            bool: True if at least one message was sent successfully
        """
        success = False
        
        for chat_id in self.authorized_chat_ids:
            result = self.send_message(chat_id, message, parse_mode)
            success = success or result
        
        return success
    
    def _run_bot(self):
        """Run the bot in a separate thread."""
        asyncio.run(self.application.run_polling())
    
    def start(self):
        """Start the bot."""
        self.bot_thread = threading.Thread(target=self._run_bot)
        self.bot_thread.daemon = True
        self.bot_thread.start()
        logger.info("Telegram bot started")
    
    def stop(self):
        """Stop the bot."""
        if self.application.running:
            asyncio.run(self.application.stop())
        logger.info("Telegram bot stopped")
