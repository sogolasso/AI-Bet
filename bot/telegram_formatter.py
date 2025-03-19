"""
Telegram Formatter for the AI Football Betting Advisor.

This module handles formatting betting tips and reports for display in the Telegram bot.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

def format_daily_tips(tips: List[Dict[str, Any]]) -> str:
    """Format daily tips for display in Telegram.
    
    Args:
        tips: List of betting tips
        
    Returns:
        Formatted message for Telegram
    """
    if not tips:
        return "🚫 No betting tips available for today."
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Header
    formatted_msg = "🔮 *TODAY'S BETTING TIPS* 🔮\n\n"
    
    # Date
    formatted_msg += f"📅 {datetime.now().strftime('%A, %d %B %Y')}\n"
    formatted_msg += f"⚽ {len(tips)} value bets identified\n\n"
    
    # Filter tips for today only
    today_tips = [tip for tip in tips if tip.get("match_date", today) == today]
    
    # If no today tips, add message
    if not today_tips:
        formatted_msg += "⚠️ *Note:* No matches found for today's date. Showing upcoming matches.\n\n"
    
    # Use filtered tips if available, otherwise use all
    display_tips = today_tips if today_tips else tips
    
    # Tips
    for i, tip in enumerate(display_tips, 1):
        match_date = tip.get("match_date", today)
        match_time = ""
        try:
            # Try to parse ISO format first
            if "T" in tip.get("match_time", ""):
                dt = datetime.fromisoformat(tip.get("match_time", ""))
                match_time = dt.strftime("%H:%M")
            else:
                # Try to parse from the format we set in betting_advisor.py
                # Expected format: "YYYY-MM-DD HH:MM"
                dt_str = tip.get("match_time", "")
                if " " in dt_str:
                    date_part, time_part = dt_str.split(" ", 1)
                    match_time = time_part
                else:
                    match_time = ""
        except (ValueError, TypeError):
            pass
        
        # Today or tomorrow label
        date_label = "Today" if match_date == today else "Tomorrow"
        
        # Confidence emoji
        confidence_emoji = {
            "Low": "🟡",
            "Medium": "🟢",
            "High": "🔵"
        }.get(tip.get("confidence", "Medium"), "🟢")
        
        formatted_msg += f"*TIP #{i}*: {confidence_emoji} {tip.get('confidence', 'Medium')} Confidence\n"
        formatted_msg += f"🏆 {tip.get('league', '')}\n"
        formatted_msg += f"⚽ {tip.get('match', '')}\n"
        formatted_msg += f"📅 {date_label}"
        if match_time:
            formatted_msg += f" 🕒 {match_time}"
        formatted_msg += "\n"
        formatted_msg += f"💰 *Bet*: {tip.get('tip', '')}\n"
        formatted_msg += f"📊 Odds: {tip.get('odds', '-')} ({tip.get('bookmaker', '')})\n"
        formatted_msg += f"💵 Stake: {tip.get('stake', 0):.2f} units\n\n"
    
    # Footer
    formatted_msg += "💡 _Recommendations are based on value betting analysis._\n"
    formatted_msg += "_Always bet responsibly and within your limits._"
    
    return formatted_msg

def format_performance_report(performance: Dict[str, Any]) -> str:
    """Format performance report for display in Telegram.
    
    Args:
        performance: Performance data dictionary
        
    Returns:
        Formatted message for Telegram
    """
    # Header
    days = performance.get("period_days", 30)
    formatted_msg = f"📊 *PERFORMANCE REPORT - LAST {days} DAYS* 📊\n\n"
    
    # Summary stats
    total_bets = performance.get("total_bets", 0)
    settled_bets = performance.get("settled_bets", 0)
    win_rate = performance.get("win_rate", 0)
    roi = performance.get("roi", 0)
    
    formatted_msg += f"📈 *Summary*:\n"
    formatted_msg += f"• Total Bets: {total_bets}\n"
    formatted_msg += f"• Settled Bets: {settled_bets}\n"
    formatted_msg += f"• Win Rate: {win_rate:.1f}%\n"
    formatted_msg += f"• ROI: {roi:.2f}%\n\n"
    
    # Bankroll
    initial = performance.get("initial_bankroll", 1000)
    current = performance.get("current_bankroll", initial)
    growth = performance.get("bankroll_growth", 0)
    
    growth_emoji = "📈" if growth >= 0 else "📉"
    formatted_msg += f"💰 *Bankroll*:\n"
    formatted_msg += f"• Initial: {initial:.2f} units\n"
    formatted_msg += f"• Current: {current:.2f} units\n"
    formatted_msg += f"• Growth: {growth_emoji} {growth:.2f}%\n\n"
    
    # Markets performance
    markets = performance.get("markets", {})
    if markets:
        formatted_msg += "🎯 *Performance by Market*:\n"
        for market, data in markets.items():
            market_roi = data.get("roi", 0)
            roi_sign = "+" if market_roi >= 0 else ""
            formatted_msg += f"• {market}: {data.get('wins', 0)}/{data.get('bets', 0)} wins, ROI: {roi_sign}{market_roi:.2f}%\n"
        formatted_msg += "\n"
    
    # Leagues performance (top 3)
    leagues = performance.get("leagues", {})
    if leagues:
        # Sort leagues by ROI
        sorted_leagues = sorted(
            [(league, data) for league, data in leagues.items() if data.get("bets", 0) >= 3],
            key=lambda x: x[1].get("roi", 0),
            reverse=True
        )
        
        if sorted_leagues:
            formatted_msg += "🌍 *Top Performing Leagues*:\n"
            for i, (league, data) in enumerate(sorted_leagues[:3], 1):
                league_roi = data.get("roi", 0)
                roi_sign = "+" if league_roi >= 0 else ""
                formatted_msg += f"{i}. {league}: {data.get('wins', 0)}/{data.get('bets', 0)} wins, ROI: {roi_sign}{league_roi:.2f}%\n"
            formatted_msg += "\n"
    
    # Footer
    formatted_msg += "_Generated on {}_".format(datetime.now().strftime("%d-%m-%Y %H:%M"))
    
    return formatted_msg

def format_system_status(status: Dict[str, Any]) -> str:
    """Format system status for display in Telegram.
    
    Args:
        status: System status dictionary
        
    Returns:
        Formatted message for Telegram
    """
    # Header
    formatted_msg = "🖥️ *SYSTEM STATUS* 🖥️\n\n"
    
    # Bankroll
    current = status.get("current_bankroll", 0)
    initial = status.get("initial_bankroll", 1000)
    growth = ((current / initial) - 1) * 100 if initial > 0 else 0
    
    growth_emoji = "📈" if growth >= 0 else "📉"
    formatted_msg += f"💰 *Bankroll*: {current:.2f} units ({growth_emoji} {growth:.2f}%)\n\n"
    
    # Model
    formatted_msg += f"🧠 *Model Version*: {status.get('model_version', 'Unknown')}\n\n"
    
    # Pending bets
    formatted_msg += f"⏳ *Pending Bets*: {status.get('pending_bets_count', 0)}\n\n"
    
    # Last updated
    last_updated = "Unknown"
    try:
        dt = datetime.fromisoformat(status.get("last_updated", ""))
        last_updated = dt.strftime("%d-%m-%Y %H:%M")
    except (ValueError, TypeError):
        pass
    
    formatted_msg += f"🔄 *Last Updated*: {last_updated}\n\n"
    
    # Footer
    formatted_msg += "_System is running normally._"
    
    return formatted_msg

def format_last_bets(bets: List[Dict[str, Any]], limit: int = 5) -> str:
    """Format last bets for display in Telegram.
    
    Args:
        bets: List of recent bets
        limit: Maximum number of bets to display
        
    Returns:
        Formatted message for Telegram
    """
    if not bets:
        return "🚫 No recent bets found."
    
    # Header
    formatted_msg = "📜 *RECENT BETS* 📜\n\n"
    
    # Sort bets by date (most recent first)
    sorted_bets = sorted(
        bets, 
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    
    # Limit number of bets
    display_bets = sorted_bets[:limit]
    
    # Bets
    for i, bet in enumerate(display_bets, 1):
        status = bet.get("status", "pending")
        
        # Status emoji
        status_emoji = {
            "won": "✅",
            "lost": "❌",
            "void": "⚪",
            "pending": "⏳"
        }.get(status, "⏳")
        
        formatted_msg += f"*BET #{i}*: {status_emoji} {status.upper()}\n"
        
        match_date = ""
        try:
            dt = datetime.fromisoformat(bet.get("match_time", ""))
            match_date = dt.strftime("%d-%m-%Y %H:%M")
        except (ValueError, TypeError):
            pass
        
        if match_date:
            formatted_msg += f"📅 {match_date}\n"
            
        formatted_msg += f"🏆 {bet.get('league', '')}\n"
        formatted_msg += f"⚽ {bet.get('home_team', '')} vs {bet.get('away_team', '')}\n"
        formatted_msg += f"💰 *Bet*: {bet.get('market', '')} - {bet.get('selection', '').upper()}\n"
        formatted_msg += f"📊 Odds: {bet.get('odds', '-')} ({bet.get('bookmaker', '')})\n"
        formatted_msg += f"💵 Stake: {bet.get('stake', 0):.2f} units\n"
        
        if status == "won":
            profit = bet.get("actual_profit", 0)
            formatted_msg += f"💸 Profit: +{profit:.2f} units\n"
        elif status == "lost":
            loss = bet.get("stake", 0)
            formatted_msg += f"💸 Loss: -{loss:.2f} units\n"
        
        formatted_msg += "\n"
    
    # Footer
    formatted_msg += f"_Showing {len(display_bets)} of {len(bets)} recent bets._"
    
    return formatted_msg

def format_help_message() -> str:
    """Format help message for Telegram bot.
    
    Returns:
        Formatted help message
    """
    formatted_msg = "🤖 *AI FOOTBALL BETTING ADVISOR - HELP* 🤖\n\n"
    
    formatted_msg += "Available commands:\n\n"
    
    formatted_msg += "*/start* - Start the bot and get welcome message\n"
    formatted_msg += "*/help* - Display this help message\n"
    formatted_msg += "*/tips* - Get today's betting tips\n"
    formatted_msg += "*/performance* - View performance report\n"
    formatted_msg += "*/status* - Check system status\n"
    formatted_msg += "*/roi* - View Return on Investment by market\n"
    formatted_msg += "*/lastbets* - View recent bets and results\n"
    formatted_msg += "*/restart* - Request system restart (admin only)\n\n"
    
    formatted_msg += "This bot uses advanced AI to identify value bets across multiple football leagues and markets. Tips are provided daily based on statistical analysis and value betting principles.\n\n"
    
    formatted_msg += "_Remember to bet responsibly and never stake more than you can afford to lose._"
    
    return formatted_msg 