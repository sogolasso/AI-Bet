# Deploying AI Football Betting Advisor

This document provides detailed instructions for deploying the AI Football Betting Advisor to different platforms.

## Deploying to Render

Render is a unified cloud platform for building and running apps and websites. It's an excellent choice for deploying the AI Football Betting Advisor due to its simple setup process, free tier availability, and built-in CI/CD.

### Prerequisites

- A [Render account](https://render.com/) (sign up is free)
- Your project code in a GitHub repository
- Your Telegram bot token (from BotFather)
- Your Telegram admin ID (use the @userinfobot on Telegram to get this)

### Files for Render Deployment

The repository includes the following files for Render deployment:

1. **Procfile**: Specifies the command to run the application
   ```
   web: python run_production.py
   ```

2. **runtime.txt**: Specifies the Python version
   ```
   python-3.11.6
   ```

3. **render.yaml**: Blueprint configuration for automatic deployment
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

     # Daily Tips Cron Job (Runs at 12:00 UTC)
     - type: cron
       name: daily-tips
       env: python
       buildCommand: pip install -r requirements.txt
       schedule: "0 12 * * *"
       startCommand: python run_daily_production.py --mode tips
       envVars:
         - key: TELEGRAM_BOT_TOKEN
           sync: false
         - key: TELEGRAM_ADMIN_IDS
           sync: false
         - key: INITIAL_BANKROLL
           value: 100

     # Daily Results Cron Job (Runs at 22:00 UTC)
     - type: cron
       name: daily-results
       env: python
       buildCommand: pip install -r requirements.txt
       schedule: "0 22 * * *"
       startCommand: python run_daily_production.py --mode results
       envVars:
         - key: TELEGRAM_BOT_TOKEN
           sync: false
         - key: TELEGRAM_ADMIN_IDS
           sync: false
         - key: INITIAL_BANKROLL
           value: 100
   ```

4. **run_daily_production.py**: Handles daily operations for cron jobs
   - Used by the cron jobs to generate tips and check results

### Deployment Options

#### Option 1: Continuous Web Service

This option keeps a web service running 24/7:

1. **Connect Your GitHub Repository**:
   - Log in to your Render account
   - Go to Dashboard → New → Blueprint
   - Connect your GitHub account if you haven't already
   - Select the repository containing your AI Football Betting Advisor code

2. **Configure the Blueprint**:
   - Render will automatically detect the `render.yaml` file
   - Review the settings and click "Apply"
   - This will create both the web service and cron jobs

3. **Set Secret Environment Variables**:
   - After the services are created, you need to set the secret environment variables
   - Go to each service → Environment → Add Environment Variable
   - Add the following:
     - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
     - `TELEGRAM_ADMIN_IDS`: Your Telegram user ID (comma-separated for multiple admins)

4. **Deploy**:
   - Click "Manual Deploy" → "Deploy latest commit"
   - Wait for the build and deployment to complete

#### Option 2: Cron Jobs Only (Alternative Approach)

If you prefer not to have a continuously running service:

1. Follow steps 1-3 from Option 1 above
2. After deployment, you can suspend the web service
3. Keep only the cron jobs active
4. This approach conserves resources while still delivering daily tips and results

### Verifying Deployment

1. **Check Logs**:
   - Go to your service in the Render dashboard
   - Click on "Logs" to see the application output
   - Look for confirmation that the bot has started successfully

2. **Test the Bot**:
   - Open Telegram and search for your bot
   - Send `/start` to your bot
   - You should receive a welcome message

3. **Monitor Cron Jobs**:
   - Check the cron job logs after their scheduled run times
   - You should see successful execution and message sending

### Troubleshooting

#### Bot Not Responding
- Check if environment variables are set correctly
- Verify the bot token is valid
- Ensure your Telegram ID is correctly added to `TELEGRAM_ADMIN_IDS`
- Check logs for any errors

#### Cron Jobs Not Running
- Verify the cron job status in the Render dashboard
- Check if the schedule is correct in `render.yaml`
- Look at the job logs for execution errors

#### Service Stops Unexpectedly
- Check if you're exceeding free tier limits
- Look for timeout errors in logs
- Consider upgrading to a paid plan if needed

### Best Practices

1. **Testing**: Test your deployment locally before pushing to Render
2. **Logs**: Regularly check logs for errors or issues
3. **Updates**: Update your code in GitHub, and Render will automatically redeploy
4. **Backups**: Regularly backup your performance data and betting history
5. **Monitoring**: Set up alerts for service failures

## Alternative Deployment Options

- **Heroku**: Similar to Render, but has different pricing tiers
- **AWS**: More complex setup but offers more control and scalability
- **Digital Ocean**: Good balance of simplicity and features
- **Self-hosted**: Run on your own server for complete control

For detailed instructions on these alternatives, please open an issue requesting documentation.

## Support

If you encounter any issues with deployment, please open an issue on the GitHub repository with:
- The platform you're trying to deploy to
- Detailed error messages
- Steps you've taken so far 