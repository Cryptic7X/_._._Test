import requests

def send_telegram_message(bot_token, chat_id, message, parse_mode='HTML'):
    """
    Send message to Telegram chat
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID (can be channel @username or numeric ID)
        message: Message text
        parse_mode: 'HTML' or 'Markdown'
    """
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")
        return False
