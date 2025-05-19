# Epic Games Freebie Auto-Claimer Bot

A Python-based bot that automatically claims free games from the Epic Games Store and sends notifications via Telegram and/or Discord.

## Features

- **Automatic Login**: Logs into your Epic Games account, with full support for 2FA (Two-Factor Authentication)
- **Free Game Detection**: Automatically checks for newly released free games from the Epic Games Store
- **Automatic Claiming**: Claims free games by simulating the required API calls
- **Persistent Storage**: Keeps track of which games have already been claimed to avoid duplicates
- **Notifications**: Sends notifications via Telegram and/or Discord when games are successfully claimed
- **Interactive Telegram Bot**: Control the auto-claimer and input 2FA codes directly through Telegram
- **Cloud Deployment**: Designed to run on cloud platforms like Railway, Render, or a VPS

## Installation

### Prerequisites

- Python 3.11 or higher
- Epic Games account
- Telegram bot token (for interactive Telegram bot)
- Telegram chat ID(s) (for authorized users)
- (Optional) Discord webhook URL

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/epic-games-freebie-claimer.git
   cd epic-games-freebie-claimer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your credentials:
   ```
   EPIC_USERNAME=gamerhh2019@gmail.com
   EPIC_PASSWORD=G@merhh1012006.$@!m@99914061977#&140619772006%
   
   # For Telegram bot and notifications
   TELEGRAM_BOT_TOKEN=7645066620:AAFxCco0oORUXM99cW4T_l--ZYa1BPX1txs
   TELEGRAM_CHAT_ID=903253229
   # For multiple authorized users, separate chat IDs with commas
   # TELEGRAM_CHAT_ID=123456789,987654321
   
   # Optional: For Discord notifications
   DISCORD_WEBHOOK_URL=your_discord_webhook_url
   
   # Optional: Customize check time (hour in 24-hour format, UTC timezone)
   CHECK_HOUR=12
   CHECK_MINUTE=0
   ```

## Usage

### Interactive Telegram Bot

The bot includes an interactive Telegram bot that allows you to control the auto-claimer directly from Telegram. To use it:

1. Create a Telegram bot using [@BotFather](https://t.me/botfather) and get your bot token
2. Find your Telegram chat ID (you can use [@userinfobot](https://t.me/userinfobot))
3. Add these to your `.env` file as shown above
4. Start the bot and send `/start` to your Telegram bot

Available Telegram commands:
- `/start` - Start the bot
- `/help` - Show help message
- `/status` - Check bot status
- `/check` - Check for new free games
- `/claim` - Manually claim all available free games
- `/tfa` - Enter 2FA code when prompted
- `/cancel` - Cancel current operation

When 2FA is required, the bot will prompt you to use the `/tfa` command to enter your 2FA code directly through Telegram.

### Running Locally

To run the bot locally:

```
python -m epic_games_bot.app
```

### Handling 2FA

If your Epic Games account has 2FA enabled, you'll need to provide the 2FA code when prompted. You can do this by running:

```
python -m epic_games_bot.app --2fa-code YOUR_2FA_CODE
```

### Cloud Deployment

#### Railway

1. Create a new project on [Railway](https://railway.app/)
2. Connect your GitHub repository
3. Add the environment variables from the `.env` file
4. Deploy the application

#### Render

1. Create a new Web Service on [Render](https://render.com/)
2. Connect your GitHub repository
3. Set the build command to `pip install -r requirements.txt`
4. Set the start command to `python -m epic_games_bot.app`
5. Add the environment variables from the `.env` file
6. Deploy the application

## Project Structure

```
epic_games_bot/
├── epic_games_bot/
│   ├── __init__.py
│   ├── app.py          # Main application
│   ├── epic.py         # Epic Games API client
│   ├── notifier.py     # Notification system
│   └── scheduler.py    # Task scheduler
├── data/               # Data storage directory
├── .env                # Environment variables (create this)
├── Procfile            # For cloud deployment
└── requirements.txt    # Python dependencies
```

## Important Notes

### About Scheduled Tasks

Please note that when deploying this bot, you'll need to ensure your hosting platform supports running scheduled tasks. Some platforms may have limitations:

- **Railway**: Supports scheduled tasks through their cron service
- **Render**: Free tier has limitations on background processes
- **Heroku**: Free tier puts dynos to sleep after 30 minutes of inactivity

For fully automated operation, consider:
1. Using a paid tier on your hosting platform
2. Setting up a separate cron service to ping your application
3. Running on a VPS or dedicated server

### About 2FA

If your Epic Games account has 2FA enabled, you have several options:

1. **Manual Input**: Run the bot with the `--2fa-code` parameter when needed
2. **App Password**: Some accounts may support app passwords that bypass 2FA
3. **Session Reuse**: The bot will store session data and only require 2FA when the session expires

For the most secure setup, consider using method #1 and implementing a way to input the 2FA code via your notification channel (Telegram/Discord).

## Customization

### Notification Timing

By default, the bot checks for free games once daily at 12:00 UTC. You can modify this in `app.py`:

```python
self.scheduler.add_daily_job(
    self.check_and_claim_free_games,
    hour=12,  # Change this to your preferred hour (0-23)
    minute=0,  # Change this to your preferred minute (0-59)
    name="daily_free_games_check"
)
```

### Adding More Notification Channels

To add more notification channels, extend the `NotificationManager` class in `notifier.py`.

## Troubleshooting

### Login Issues

- Ensure your Epic Games credentials are correct
- If using 2FA, make sure you're providing the correct code
- Check if Epic Games has changed their API or login flow

### Deployment Issues

- Verify all environment variables are set correctly
- Ensure your hosting platform supports background processes
- Check the logs for any specific error messages

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This project is not affiliated with, maintained, authorized, endorsed, or sponsored by Epic Games or any of its affiliates.
