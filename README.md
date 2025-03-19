# AI Football Betting Advisor

A data-driven football betting advisory system that provides daily betting tips with a focus on value bets across various football markets.

![Football Betting](https://img.shields.io/badge/Football-Betting-green)
![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)

## Quick Start

Get started with the AI Football Betting Advisor in just a few steps:

### Windows Users
- For testing without real money: Double-click `run_telegram_shadow.bat`
- For real betting recommendations: Double-click `run_production.bat`

### Linux/macOS Users
- For testing without real money: `./run_telegram_shadow.sh`
- For real betting recommendations: `./run_production.sh`

### First-time Setup
When you run either script for the first time, it will:
1. Set up your environment and install dependencies
2. Guide you through Telegram bot configuration
3. Help you get your Telegram user ID for notifications
4. Launch the selected mode (shadow or production)

### All-in-One Script
For advanced users, the `all_in_one.py` script provides all functionality in one place:
```
python all_in_one.py --help       # Show help information
python all_in_one.py --setup      # Run just the setup process
python all_in_one.py --get-id     # Get your Telegram user ID
python all_in_one.py --shadow     # Run in shadow mode
python all_in_one.py --production # Run in production mode
```

Or just run `python all_in_one.py` for an interactive menu.

## Overview

This advanced AI Football Betting Advisor is designed to identify valuable betting opportunities across football matches worldwide. The system:

- Dynamically selects the best betting markets (match winner, over/under, BTTS, etc.)
- Prioritizes high-value odds over low-risk bets
- Makes decisions based on data-driven analysis using team form, injuries, trends, and odds movements
- Tracks ROI and analyzes betting patterns to learn and improve over time
- Delivers 5 daily betting recommendations via Telegram with confidence levels
- Implements various bankroll management strategies (Kelly Criterion, flat betting, etc.)

## Features

- **Multi-Source Data Collection**: Scrapes football data from various sources to obtain comprehensive match information, historical statistics, and odds from multiple bookmakers.

- **AI-Powered Predictions**: Uses statistical models to predict match outcomes and identify discrepancies between predicted probabilities and bookmaker odds.

- **Value Bet Identification**: Focuses on finding betting opportunities where the expected value is positive, rather than simply predicting winners.

- **Dynamic Market Selection**: Analyzes various betting markets for each match to find the most valuable opportunities.

- **Bankroll Management**: Implements various staking strategies to optimize returns and manage risk.

- **Telegram Bot Interface**: Delivers daily betting tips and performance reports through a user-friendly Telegram bot.

- **Performance Tracking**: Maintains detailed records of all recommendations and outcomes to analyze performance by league, market type, confidence level, and more.

- **Shadow Mode**: Allows users to run the system without risking real money to validate performance before committing funds.

## Telegram Shadow Mode

The Telegram Shadow Mode allows you to run the advisor in simulation mode while receiving updates via Telegram. This is useful for testing the system's performance before committing real money.

### Prerequisites

- Python 3.8 or later
- Telegram bot token (obtain from BotFather on Telegram)
- Admin Telegram user ID (your Telegram user ID)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/football-betting-advisor.git
   cd football-betting-advisor
   ```

2. Run the setup script:
   ```
   python setup.py
   ```
   This script will:
   - Check your Python version
   - Create required directories
   - Install dependencies
   - Set up your .env file
   - Guide you through the Telegram bot setup

3. Or manually install required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Telegram credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_ADMIN_IDS=your_telegram_id_here,another_id_here
   ```

### Getting Your Telegram User ID

To get your Telegram user ID (required for receiving notifications):

1. Run the helper script:
   ```
   python get_telegram_id.py
   ```

2. Message your bot on Telegram, and it will reply with your user ID.

3. Add this ID to your .env file as `TELEGRAM_ADMIN_IDS`.

### Running Shadow Mode

You can run the Telegram Shadow Mode using one of the following methods:

#### Using Python

```bash
python run_telegram_shadow.py --duration 14 --bankroll 100 --quick
```

Options:
- `--duration` or `-d`: Duration in days for shadow mode (default: 14)
- `--bankroll` or `-b`: Initial bankroll amount (default: 100)
- `--quick` or `-q`: Run in quick mode for faster simulation
- `--config` or `-c`: Path to custom configuration file

#### Using Batch Script (Windows)

```bash
run_telegram_shadow.bat -d 14 -b 100 -q
```

#### Using Shell Script (Linux/macOS)

```bash
./run_telegram_shadow.sh -d 14 -b 100 -q
```

### Output Files

The shadow mode generates several output files in the `data/shadow` directory:

- `shadow_bets.csv`: Record of all simulated bets
- `shadow_daily.csv`: Daily performance summaries
- `telegram_shadow_mode.log`: Log file with detailed information

## Production Mode

The Production Mode runs the AI Football Betting Advisor in full operational mode, providing daily betting tips and results updates via Telegram. Unlike Shadow Mode, Production Mode is designed for continuous operation.

### Prerequisites

- Python 3.8 or later
- Telegram bot token (obtain from BotFather on Telegram)
- Admin Telegram user ID (your Telegram user ID)
- Properly configured .env file (see Setup section)

### Running Production Mode

You can run the Production Mode using one of the following methods:

#### Using Python

```bash
python run_production.py
```

#### Using Batch Script (Windows)

```bash
run_production.bat
```

#### Using Shell Script (Linux/macOS)

```bash
./run_production.sh
```

### Functionality

When running in Production Mode, the system will:

1. **Generate daily betting tips** around noon (12:00)
2. **Check and report results** of pending bets in the evening (22:00)
3. **Send periodic status updates** (every 6 hours) to confirm the system is running
4. **Track performance metrics** including ROI, win rate, and profit/loss

### Continuous Operation

For 24/7 operation without keeping your PC on:

1. **Cloud Hosting**:
   - AWS EC2 (t2.micro instances are often free tier eligible)
   - Google Cloud Platform
   - Digital Ocean Droplets

2. **Dedicated Low-Power Device**:
   - Raspberry Pi or similar single-board computer

3. **Setting up as a System Service**:

   On Linux (using systemd):
   ```bash
   # Create a service file
   sudo nano /etc/systemd/system/betting-advisor.service
   
   # Add these contents
   [Unit]
   Description=AI Football Betting Advisor
   After=network.target
   
   [Service]
   User=yourusername
   WorkingDirectory=/path/to/football-betting-advisor
   ExecStart=/path/to/python /path/to/football-betting-advisor/run_production.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   
   # Enable and start the service
   sudo systemctl enable betting-advisor.service
   sudo systemctl start betting-advisor.service
   ```

   On Windows (using Task Scheduler):
   ```
   # Create a scheduled task that runs at system startup
   schtasks /create /tn "Football Advisor" /tr "cmd /c start /min python C:\path\to\run_production.py" /sc onstart
   ```

### Output Files

The production mode generates several output files in the `data/production` directory:

- `bets.csv`: Record of all betting recommendations
- `results.csv`: Results and outcomes of placed bets
- `daily.csv`: Daily performance summaries
- `production_mode.log`: Log file with detailed information

## Utilities

The system includes several utility modules that enhance functionality:

### Emoji Utilities

Located in `utils/emoji_utils.py`, these utilities handle emoji characters in logs and messages:

- `sanitize_for_console`: Converts emoji to plain text for console output
- `emoji_to_html`: Converts emoji to HTML entities for Telegram messages
- `remove_emojis`: Removes all emoji characters from text
- `get_safe_emoji`: Returns a safe version of an emoji for the current environment

### Logging Configuration

Located in `utils/logging_config.py`, this module provides:

- Custom formatter that handles emoji in log messages
- Configuration for both console and file logging
- Proper encoding settings for wide character support

## Architecture

The system consists of several key components:

- **Data Collection**: `MatchCollector` and `ScrapingUtils` handle fetching and parsing data from multiple sources.

- **Prediction Model**: `PredictionModel` processes match data and generates outcome probabilities.

- **Odds Evaluation**: `OddsEvaluator` compares predicted probabilities with bookmaker odds to identify value bets.

- **Staking Strategy**: `StakingStrategy` calculates optimal stake sizes based on various methods.

- **Telegram Bot**: `TelegramBot` delivers betting tips and reports directly to users.

## Installation

### Prerequisites
- Python 3.11+
- Redis database
- Telegram Bot API token

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/your-username/football-betting-advisor.git
cd football-betting-advisor
```

2. Create and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

3. Build and run the Docker container:
```bash
docker build -t football-betting-advisor .
docker run -d --name betting-advisor --env-file .env -v $(pwd)/data:/app/data football-betting-advisor
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/football-betting-advisor.git
cd football-betting-advisor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

5. Run the deployment checklist:
```bash
python tests/deployment_checklist.py
```

## Usage

### Starting the Advisor

Run the main application:
```bash
python main.py
```

### Shadow Mode

To run the system without placing real bets (recommended for testing):
```bash
python shadow_mode.py --days 14 --bankroll 1000.0
```

Options:
- `--days`: How many days to run shadow mode (default: 14)
- `--bankroll`: Virtual bankroll to simulate with (default: 1000.0)
- `--no-telegram`: Disable Telegram notifications
- `--data-dir`: Directory to store shadow mode data
- `--fast-mode`: Run in fast mode for testing (1 minute intervals)

### Telegram Commands

Once the bot is running, you can interact with it using these commands:
- `/start` - Welcome message and information
- `/help` - Display available commands
- `/tips` - Get today's betting tips
- `/performance` - View overall performance metrics
- `/roi` - Check return on investment
- `/history` - View betting history

## Configuration

The system is configured through environment variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BANKROLL` | Total bankroll for betting (in currency units) | Yes | - |
| `MAX_STAKE_PERCENT` | Maximum stake per bet (% of bankroll) | Yes | 5.0 |
| `MIN_STAKE_PERCENT` | Minimum stake per bet (% of bankroll) | Yes | 0.5 |
| `DAYS_AHEAD` | Number of days ahead to look for matches | Yes | 1 |
| `MIN_ODDS` | Minimum odds to consider | Yes | 1.5 |
| `MAX_ODDS` | Maximum odds to consider | Yes | 10.0 |
| `MIN_EV_THRESHOLD` | Minimum expected value threshold | Yes | 0.05 |
| `TELEGRAM_TOKEN` | Telegram Bot API token | Yes | - |
| `TELEGRAM_CHAT_ID` | Telegram chat ID to send tips to | Yes | - |
| `REDIS_HOST` | Redis host address | No | localhost |
| `REDIS_PORT` | Redis port | No | 6379 |
| `DRY_RUN` | Run in shadow mode without real money | No | false |

## Testing

### Running Tests

Run the test suite with:
```bash
pytest
```

Run specific test files:
```bash
pytest tests/test_telegram.py
pytest tests/test_performance.py
```

### Load Testing

To test system performance under load:
```bash
python tests/test_load.py --users 50 --duration 300
```

## Deployment

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Deployment to Render

The AI Football Betting Advisor can be deployed to Render for 24/7 operation in the cloud. There are two deployment options:

### Option 1: Continuous Service (Free Tier)

This option keeps the application running continuously:

1. **Prerequisites**:
   - Create a [Render account](https://render.com/)
   - Push your code to a GitHub repository
   - Have your Telegram bot token and admin ID ready

2. **Deploy using render.yaml**:
   - Fork/clone this repository
   - Connect your GitHub account to Render
   - Create a new "Blueprint" instance on Render pointing to your repo
   - Render will automatically detect the `render.yaml` configuration
   - Set the required environment variables:
     - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
     - `TELEGRAM_ADMIN_IDS`: Your Telegram user ID (comma-separated for multiple admins)

3. **Verify Deployment**:
   - Once deployed, send `/start` to your bot on Telegram
   - Check the logs in the Render dashboard for any issues

### Option 2: Daily Cron Jobs (Recommended)

This option uses scheduled jobs to run the advisor at specific times:

1. **Prerequisites**:
   - Same as Option 1

2. **Deploy using render.yaml**:
   - Same steps as Option 1, but Render will automatically set up:
     - A daily job at 12:00 UTC to generate and send betting tips
     - A daily job at 22:00 UTC to check results and send updates

3. **Customize Schedule** (optional):
   - Edit the `render.yaml` file to change the cron schedules if needed
   - Default schedule:
     ```yaml
     # For tips generation
     schedule: "0 12 * * *"  # Runs at 12:00 UTC daily
     
     # For results checking
     schedule: "0 22 * * *"  # Runs at 22:00 UTC daily
     ```

### Monitoring and Maintenance

- **Logs**: View logs in the Render dashboard for debugging
- **Updates**: Push changes to your GitHub repo and Render will automatically redeploy
- **Performance**: Monitor CPU/memory usage in the Render dashboard

### Troubleshooting Render Deployment

- **Bot Not Responding**: Check Render logs for errors, ensure environment variables are set correctly
- **Missing Tips**: Verify the cron job is running on schedule, check logs for errors
- **Out of Resources**: Consider upgrading your Render plan if you hit free tier limits

## Development

### Project Structure

```
football-betting-advisor/
├── data/                      # Data collection components
│   ├── match_collector.py     # Fetches match data
│   └── scraping_utils.py      # Web scraping utilities
├── models/                    # Prediction models
│   └── prediction.py          # Match outcome prediction
├── betting/                   # Betting components
│   ├── odds_evaluator.py      # Evaluates odds for value
│   └── staking.py             # Bankroll management
├── bot/                       # Telegram bot
│   └── telegram_bot.py        # Bot implementation
├── utils/                     # Utility modules
│   ├── emoji_utils.py         # Emoji handling utilities
│   └── logging_config.py      # Custom logging configuration
├── tests/                     # Test suites
├── setup.py                   # Setup script for easy installation
├── get_telegram_id.py         # Helper to get your Telegram ID
├── run_telegram_shadow.py     # Python launcher for shadow mode
├── run_telegram_shadow.bat    # Windows batch script
├── run_telegram_shadow.sh     # Linux/macOS shell script
├── .env.example               # Example environment variables
├── Dockerfile                 # Docker configuration
├── requirements.txt           # Python dependencies
└── main.py                    # Main entry point
```

### Quick Setup Scripts

For convenience, the following scripts are provided:

- `setup.py`: Interactive setup script for configuration
- `get_telegram_id.py`: Helper to get your Telegram user ID
- `run_telegram_shadow.py`: Python launcher for Telegram Shadow Mode
- `run_telegram_shadow.bat`: Windows batch launcher (supports command line options)
- `run_telegram_shadow.sh`: Linux/macOS shell launcher (supports command line options)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Betting involves risk and you should never bet more than you can afford to lose. 