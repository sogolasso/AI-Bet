# Deploying AI Football Betting Advisor on Render (Production Mode)

This guide covers how to deploy the AI Football Betting Advisor to Render.com to run it 24/7 without keeping your computer on.

## Prerequisites

- A GitHub account
- Your AI Football Betting Advisor code in a GitHub repository
- Telegram bot token (from BotFather)
- Your Telegram user ID

## Preparation Steps

1. **Create a Procfile** in your project root directory:
   ```
   web: python run_production.py
   ```

2. **Create a runtime.txt** file to specify Python version:
   ```
   python-3.11.6
   ```

3. **Verify your requirements.txt** contains all dependencies:
   ```
   python-telegram-bot==13.7
   python-dotenv
   pandas
   numpy
   requests
   aiohttp
   beautifulsoup4
   lxml
   matplotlib
   ```

4. **Create a render.yaml** configuration file:
   ```yaml
   services:
     - type: web
       name: football-betting-advisor
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: python run_production.py
       envVars:
         - key: TELEGRAM_BOT_TOKEN
           sync: false
         - key: TELEGRAM_ADMIN_IDS
           sync: false
         - key: INITIAL_BANKROLL
           value: 100
       plan: free
   ```

5. **Push all changes to GitHub**:
   ```bash
   git add Procfile runtime.txt render.yaml
   git commit -m "Add Render deployment configuration"
   git push
   ```

## Deploying to Render

### Web Dashboard Method

1. Go to [Render.com](https://render.com/) and sign up/login
2. Click **"New +"** and select **"Web Service"**
3. Connect your GitHub repository
4. Configure your web service:
   - **Name**: football-betting-advisor
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_production.py`

5. Add the following environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather
   - `TELEGRAM_ADMIN_IDS`: Your Telegram user ID
   - `INITIAL_BANKROLL`: 100

6. Select the **"Free"** plan
7. Click **"Create Web Service"**

## Post-Deployment

1. **Check logs** in the Render dashboard for any errors
2. **Test your bot** by sending a message on Telegram
3. **Verify 24/7 operation**:
   - The Render free plan includes 750 hours/month
   - Services on the free plan spin down after 15 minutes of inactivity
   - To keep your service running, consider using a service like UptimeRobot to ping your app URL every 10 minutes

## Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check Render logs for errors
   - Verify environment variables are set correctly
   - Ensure your bot token is valid

2. **Service stopping**:
   - Render free tier apps stop after 15 minutes of inactivity
   - Set up a monitoring service like UptimeRobot

3. **Environment variables not working**:
   - Environment variables may need to be surrounded by quotes in Render
   - Verify the format of TELEGRAM_ADMIN_IDS (should be a comma-separated list without spaces)

### Optimizing for Free Tier

1. **Set up minimal logging** to reduce disk usage
2. **Use background workers** for intensive tasks
3. **Keep API calls optimized** to avoid exceeding rate limits

## Alternative Approach: Using Cron Jobs

Since the production mode needs to run continuously, an alternative approach is to use Render's cron jobs:

1. Create a separate script called `run_daily_production.py` that:
   - Fetches the latest betting data
   - Generates tips
   - Sends them via Telegram
   - Exits

2. Set up a cron job in Render to run this script daily at appropriate times:
   - One job at 12:00 for generating tips
   - One job at 22:00 for checking results

This way, you won't need a continuously running service.

## Conclusion

Your AI Football Betting Advisor should now be deployed on Render and running in production mode. The bot will send betting tips and results to your Telegram account without requiring your computer to be on 24/7.

For any issues, check the Render logs and ensure all environment variables are correctly set. 