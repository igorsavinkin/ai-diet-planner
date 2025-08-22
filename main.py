# main.py
import logging
import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters
)

# Import configuration
try:
    from config import HTTP_API_BOT_TOKEN, DEEPSEEK_API_KEY
except ImportError:
    logging.error("Config file not found. Please create config.py with your bot token.")
    exit(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
GENDER, AGE, WEIGHT, HEIGHT, ACTIVITY, GOAL, MENU_CONFIRM = range(7)

# Activity levels with multipliers
ACTIVITY_LEVELS = {
    "No activity": 1.2,
    "Minimal activity": 1.375,
    "Medium activity": 1.55,
    "Above average activity": 1.725,
    "High activity": 1.9
}

# Initialize DeepSeek client if API key is available
if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here":
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
else:
    client = None
    logger.warning("DeepSeek API key not configured. AI menu generation will be disabled.")

async def generate_weekly_menu(user_data):
    """Generate a weekly menu using DeepSeek AI"""
    if not client:
        return "AI menu generation is currently unavailable. Please configure the DeepSeek API key."
    
    prompt = f"""
    Create a personalized weekly meal plan for a {user_data['age']}-year-old {user_data['gender'].lower()} 
    with the following characteristics:
    - Weight: {user_data['weight']} kg
    - Height: {user_data['height']} cm
    - Activity level: {user_data['activity']}
    - Goal: {user_data['goal']}
    - Daily calorie target: {user_data['calories']:.0f} calories
    - BMR: {user_data['bmr']:.0f} calories
    - TDEE: {user_data['tdee']:.0f} calories
    
    Please create a simple, practical weekly menu with breakfast, lunch, dinner, and optional snacks for each day.
    Focus on common, affordable ingredients. Include portion sizes in grams or common measurements.
    Format the response with clear day-by-day sections.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a nutritionist expert specializing in creating practical meal plans."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating menu with DeepSeek: {e}")
        return "I apologize, but I'm having trouble generating your menu at the moment. Please try again later."

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    await update.message.reply_text(
        f"Welcome {user.first_name} to the Nutrition Bot! 🍎\n\n"
        "I will help you calculate your daily caloric needs and generate a personalized diet plan.\n\n"
        "To get started, please provide some basic information about yourself.\n\n"
        "Type /cancel at any time to stop our conversation."
    )
    
    # Ask for gender with both buttons and text instructions
    reply_keyboard = [['Male', 'Female']]
    await update.message.reply_text(
        'Please select your gender:\n\n'
        'If you don\'t see buttons, please type: "Male" or "Female"',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return GENDER

# [Rest of your functions remain the same as in the previous implementation]
# ...

# Main function
def main() -> None:
    # Create the Application using ApplicationBuilder with token from config
    application = ApplicationBuilder().token(HTTP_API_BOT_TOKEN).build()

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity)],
            GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal)],
            MENU_CONFIRM: [MessageHandler(filters.Regex('^(Yes|No)$'), menu_confirmation)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('diet', generate_diet))
    application.add_handler(CommandHandler('weekly_menu', weekly_menu))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()