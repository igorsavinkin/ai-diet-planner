# main.py
import logging
import json
import os
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters
)

# Import configuration
try:
    from config import HTTP_API_BOT_TOKEN, DEEPSEEK_API_KEY, BOT_ADMINS
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

# Case-insensitive mappings for activity levels and goals
ACTIVITY_MAPPING = {}
for key in ACTIVITY_LEVELS.keys():
    ACTIVITY_MAPPING[key.lower()] = key

GOAL_MAPPING = {
    "lose weight": "Lose weight",
    "maintain weight": "Maintain weight",
    "gain weight": "Gain weight"
}

# Simple in-memory user data storage (in a real app, use a database)
user_data_store = {}

# Initialize DeepSeek client if API key is available
if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "your_deepseek_api_key_here":
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
else:
    client = None
    logger.warning("DeepSeek API key not configured. AI menu generation will be disabled.")

# Admin functionality
def is_admin(user_id: int) -> bool:
    """Check if a user is in the admin list"""
    try:
        from config import BOT_ADMINS
        return user_id in BOT_ADMINS
    except (ImportError, AttributeError):
        return False

def admin_required(func):
    """Decorator to check if user is admin before executing command"""
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.message.from_user.id
        if not is_admin(user_id):
            await update.message.reply_text("❌ This command is for administrators only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@admin_required
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display bot usage statistics (admin only)"""
    # Example statistics - in a real implementation, you would track these
    stats_message = (
        "📊 Bot Statistics:\n\n"
        f"Total Users: {len(user_data_store)}\n"
        "Active Today: 23\n"
        "Menus Generated: 287\n"
        "Most Popular Goal: Weight Loss (65%)\n"
        "Average Calories: 1950 kcal"
    )
    
    await update.message.reply_text(stats_message)

@admin_required
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message to all users (admin only)"""
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    
    # In a real implementation, you would iterate through your user database
    # For now, we'll just confirm the command works
    await update.message.reply_text(
        f"📢 Broadcast message prepared:\n\n{message}\n\n"
        f"(In a full implementation, this would be sent to all {len(user_data_store)} users)"
    )

@admin_required
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get information about a specific user (admin only)"""
    if not context.args:
        await update.message.reply_text("Usage: /userinfo <user_id>")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid user ID.")
        return
    
    # Check if user exists in our data store
    if target_user_id in user_data_store:
        user_data = user_data_store[target_user_id]
        user_info_msg = (
            f"👤 User Information for ID {target_user_id}:\n\n"
            f"Gender: {user_data.get('gender', 'N/A')}\n"
            f"Age: {user_data.get('age', 'N/A')}\n"
            f"Weight: {user_data.get('weight', 'N/A')} kg\n"
            f"Height: {user_data.get('height', 'N/A')} cm\n"
            f"Activity: {user_data.get('activity', 'N/A')}\n"
            f"Goal: {user_data.get('goal', 'N/A')}\n"
            f"Calories: {user_data.get('calories', 'N/A')} kcal\n"
            f"BMR: {user_data.get('bmr', 'N/A')}\n"
            f"TDEE: {user_data.get('tdee', 'N/A')}"
        )
    else:
        user_info_msg = f"User with ID {target_user_id} not found in the database."
    
    await update.message.reply_text(user_info_msg)

@admin_required
async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin commands help"""
    help_text = """
    🤖 Admin Commands:
    
    /stats - Show bot usage statistics
    /broadcast <message> - Send message to all users
    /userinfo <user_id> - Get information about a user
    /admin_help - Show this help message
    """
    await update.message.reply_text(help_text)

def format_menu_as_plain_text(menu_text):
    """
    Convert markdown-formatted menu to plain text with proper formatting for Telegram.
    Removes markdown syntax while preserving structure.
    """
    if not menu_text:
        return menu_text
    
    # Remove markdown headers
    menu_text = re.sub(r'#+\s*', '', menu_text)
    
    # Convert bullet points to dashes
    menu_text = re.sub(r'[*\-]\s+', '- ', menu_text)
    
    # Remove bold and italic formatting
    menu_text = re.sub(r'\*\*(.*?)\*\*', r'\1', menu_text)
    menu_text = re.sub(r'\*(.*?)\*', r'\1', menu_text)
    menu_text = re.sub(r'_(.*?)_', r'\1', menu_text)
    
    # Ensure proper line breaks
    menu_text = re.sub(r'\n\s*\n', '\n\n', menu_text)
    
    # Add emojis for better visual structure
    menu_text = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', 
                      r'🗓️ \1', menu_text, flags=re.IGNORECASE)
    menu_text = re.sub(r'(Breakfast|Lunch|Dinner|Snack)', 
                      r'🍽️ \1', menu_text, flags=re.IGNORECASE)
    
    return menu_text

# Define all handler functions first
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    user_id = user.id
    
    # Check if user already has stored data
    has_previous_data = user_id in user_data_store and user_data_store[user_id].get('calories')
    
    if has_previous_data:
        # User has previous data - show options to generate menu or update info
        reply_keyboard = [['Generate New Menu', 'Update My Information']]
        await update.message.reply_text(
            f"Welcome back {user.first_name}! 👋\n\n"
            "I see you've already provided your information before.\n\n"
            "Would you like to generate a new menu with your existing data "
            "or update your information?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, 
                one_time_keyboard=True,
                resize_keyboard=True
            ),
        )
        return MENU_CONFIRM
    else:
        # New user or no previous data
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

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    gender_input = update.message.text.strip().lower()
    
    # Validate input
    if gender_input not in ['male', 'female']:
        await update.message.reply_text(
            'Please enter a valid gender. Type "Male" or "Female":'
        )
        return GENDER
    
    context.user_data['gender'] = gender_input.capitalize()
    logger.info("Gender of %s: %s", user.first_name, context.user_data['gender'])
    
    await update.message.reply_text(
        'Great! Now please enter your age:',
        reply_markup=ReplyKeyboardRemove(),
    )
    return AGE

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    try:
        age = int(update.message.text)
        if age < 1 or age > 120:
            await update.message.reply_text('Please enter a valid age between 1 and 120:')
            return AGE
        context.user_data['age'] = age
        logger.info("Age of %s: %s", user.first_name, age)
        
        await update.message.reply_text('Now please enter your weight in kg:')
        return WEIGHT
    except ValueError:
        await update.message.reply_text('Please enter a valid number for your age:')
        return AGE

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    try:
        weight = float(update.message.text)
        if weight < 1 or weight > 300:
            await update.message.reply_text('Please enter a valid weight between 1 and 300 kg:')
            return WEIGHT
        context.user_data['weight'] = weight
        logger.info("Weight of %s: %s kg", user.first_name, weight)
        
        await update.message.reply_text('Now please enter your height in cm:')
        return HEIGHT
    except ValueError:
        await update.message.reply_text('Please enter a valid number for your weight:')
        return WEIGHT

async def height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    try:
        height = float(update.message.text)
        if height < 30 or height > 250:
            await update.message.reply_text('Please enter a valid height between 30 and 250 cm:')
            return HEIGHT
        context.user_data['height'] = height
        logger.info("Height of %s: %s cm", user.first_name, height)
        
        # Ask for activity level with both buttons and text instructions
        activity_options = list(ACTIVITY_LEVELS.keys())
        reply_keyboard = [[option] for option in activity_options]  # One button per row
        
        activity_instructions = "\n".join([f"- {option}" for option in activity_options])
        
        await update.message.reply_text(
            f'Please select your activity level:\n\n'
            f'If you don\'t see buttons, please type one of these options (case insensitive):\n{activity_instructions}',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, 
                one_time_keyboard=True,
                resize_keyboard=True
            ),
        )
        return ACTIVITY
    except ValueError:
        await update.message.reply_text('Please enter a valid number for your height:')
        return HEIGHT

async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    activity_input = update.message.text.strip().lower()
    
    # Validate input using case-insensitive mapping
    if activity_input not in ACTIVITY_MAPPING:
        activity_options = list(ACTIVITY_LEVELS.keys())
        activity_instructions = "\n".join([f"- {option}" for option in activity_options])
        
        await update.message.reply_text(
            f'Please select a valid activity level from these options (case insensitive):\n{activity_instructions}'
        )
        return ACTIVITY
        
    # Map to the correct case version
    context.user_data['activity'] = ACTIVITY_MAPPING[activity_input]
    logger.info("Activity level of %s: %s", user.first_name, context.user_data['activity'])
    
    # Ask for goal with both buttons and text instructions
    goal_options = ['Lose weight', 'Maintain weight', 'Gain weight']
    reply_keyboard = [goal_options]  # All buttons in one row
    
    await update.message.reply_text(
        'What is your goal?\n\n'
        'If you don\'t see buttons, please type one of these options (case insensitive):\n'
        '- Lose weight\n- Maintain weight\n- Gain weight',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    goal_input = update.message.text.strip().lower()
    
    # Validate input using case-insensitive mapping
    if goal_input not in GOAL_MAPPING:
        await update.message.reply_text(
            'Please select a valid goal. Type one of these options (case insensitive):\n'
            '- Lose weight\n- Maintain weight\n- Gain weight'
        )
        return GOAL
        
    # Map to the correct case version
    context.user_data['goal'] = GOAL_MAPPING[goal_input]
    logger.info("Goal of %s: %s", user.first_name, context.user_data['goal'])
    
    # Calculate BMR
    weight = context.user_data['weight']
    height = context.user_data['height']
    age = context.user_data['age']
    
    if context.user_data['gender'] == 'Male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Apply activity multiplier
    activity_multiplier = ACTIVITY_LEVELS[context.user_data['activity']]
    tdee = bmr * activity_multiplier
    
    # Adjust based on goal
    if context.user_data['goal'] == 'Lose weight':
        calories = tdee - 500  # Create deficit for weight loss
    elif context.user_data['goal'] == 'Gain weight':
        calories = tdee + 500  # Create surplus for weight gain
    else:
        calories = tdee  # Maintain weight
    
    context.user_data['bmr'] = bmr
    context.user_data['tdee'] = tdee
    context.user_data['calories'] = calories
    
    # Store user data for future use
    user_id = user.id
    user_data_store[user_id] = context.user_data.copy()
    
    # Display results
    await update.message.reply_text(
        f"✅ Your data has been recorded:\n\n"
        f"Gender: {context.user_data['gender']}\n"
        f"Age: {context.user_data['age']} years\n"
        f"Weight: {context.user_data['weight']} kg\n"
        f"Height: {context.user_data['height']} cm\n"
        f"Activity level: {context.user_data['activity']}\n"
        f"Goal: {context.user_data['goal']}\n\n"
        f"📊 Calculation Results:\n"
        f"BMR (Basal Metabolic Rate): {bmr:.0f} calories\n"
        f"TDEE (Total Daily Energy Expenditure): {tdee:.0f} calories\n"
        f"Recommended daily intake: {calories:.0f} calories\n\n"
        "Would you like me to generate a personalized weekly menu? (Yes/No - case insensitive)",
        reply_markup=ReplyKeyboardMarkup(
            [['Yes', 'No']],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    
    return MENU_CONFIRM

async def menu_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    response = update.message.text.strip().lower()
    
    # Handle different response types
    if response in ['yes', 'y', 'generate new menu']:
        await update.message.reply_text(
            "Great! I'm generating your personalized weekly menu. This may take a moment...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Generate weekly menu using AI
        weekly_menu = await generate_weekly_menu(context.user_data)
        
        if weekly_menu:
            # Split long message into parts if needed (Telegram has a message length limit)
            if len(weekly_menu) > 4000:
                parts = [weekly_menu[i:i+4000] for i in range(0, len(weekly_menu), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(weekly_menu)
            
            # Offer to generate another menu or update information
            reply_keyboard = [['Generate Another Menu', 'Update My Information']]
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, 
                    one_time_keyboard=True,
                    resize_keyboard=True
                ),
            )
            return MENU_CONFIRM
        else:
            await update.message.reply_text(
                "I apologize, but I'm having trouble generating your menu at the moment. "
                "Please try again later or contact support if the issue persists.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
            
    elif response in ['no', 'n', 'update my information']:
        await update.message.reply_text(
            "No problem! Let's update your information.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Ask for gender to start the update process
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
    else:
        await update.message.reply_text(
            "Please respond with 'Yes' or 'No' (case insensitive):",
            reply_markup=ReplyKeyboardMarkup(
                [['Yes', 'No']],
                one_time_keyboard=True,
                resize_keyboard=True
            ),
        )
        return MENU_CONFIRM

async def generate_weekly_menu(user_data):
    """Generate a weekly menu using DeepSeek AI with plain text formatting"""
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
    
    IMPORTANT: Format the response as plain text (no markdown). Use clear section headers like:
    
    Monday
    Breakfast: 
    - Oatmeal: 200g
    - Cheese: 50g
    - Rye bread: 30g (1-2 pieces)
    - Cup of juice
    
    Lunch:
    - Grilled chicken: 150g
    - Brown rice: 100g
    - Steamed vegetables: 200g
    
    And so on for each day of the week.
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a nutritionist expert specializing in creating practical meal plans. Always respond with plain text formatting (no markdown)."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        # Format the menu as plain text
        menu_text = response.choices[0].message.content
        return format_menu_as_plain_text(menu_text)
        
    except Exception as e:
        logger.error(f"Error generating menu with DeepSeek: {e}")
        return "I apologize, but I'm having trouble generating your menu at the moment. Please try again later."

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        'Bye! I hope we can talk again some day.', 
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def generate_diet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Check if user has existing data
    if user_id not in user_data_store or 'calories' not in user_data_store[user_id]:
        await update.message.reply_text(
            "Please provide your body data first using /start"
        )
        return
    
    # Use stored data
    context.user_data.update(user_data_store[user_id])
    calories = context.user_data['calories']
    goal = context.user_data['goal']
    
    # Simple diet plan generation based on calories and goal
    protein_percentage = 0.3 if goal == 'Lose weight' else 0.25
    carb_percentage = 0.4 if goal == 'Gain weight' else 0.35
    fat_percentage = 0.3 if goal == 'Lose weight' else 0.4
    
    protein_cal = protein_percentage * calories
    carb_cal = carb_percentage * calories
    fat_cal = fat_percentage * calories
    
    protein_grams = protein_cal / 4
    carb_grams = carb_cal / 4
    fat_grams = fat_cal / 9
    
    # Sample meal plan
    await update.message.reply_text(
        f"🍽️ Your Personalized Diet Plan ({calories:.0f} calories)\n\n"
        f"Macronutrient Distribution:\n"
        f"Protein: {protein_grams:.0f}g ({protein_percentage*100:.0f}%)\n"
        f"Carbs: {carb_grams:.0f}g ({carb_percentage*100:.0f}%)\n"
        f"Fats: {fat_grams:.0f}g ({fat_percentage*100:.0f}%)\n\n"
        f"Sample Meal Plan:\n"
        f"Breakfast: {calories*0.25:.0f} calories\n"
        f"Lunch: {calories*0.35:.0f} calories\n"
        f"Dinner: {calories*0.30:.0f} calories\n"
        f"Snack: {calories*0.10:.0f} calories\n\n"
        "Would you like me to generate a detailed weekly menu? (Yes/No - case insensitive)",
        reply_markup=ReplyKeyboardMarkup(
            [['Yes', 'No']],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    
    return MENU_CONFIRM

async def weekly_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Check if user has existing data
    if user_id not in user_data_store or 'calories' not in user_data_store[user_id]:
        await update.message.reply_text(
            "Please provide your body data first using /start"
        )
        return
    
    # Use stored data
    context.user_data.update(user_data_store[user_id])
    
    await update.message.reply_text(
        "I'm generating your personalized weekly menu. This may take a moment...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Generate weekly menu using AI
    weekly_menu = await generate_weekly_menu(context.user_data)
    
    if weekly_menu:
        # Split long message into parts if needed
        if len(weekly_menu) > 4000:
            parts = [weekly_menu[i:i+4000] for i in range(0, len(weekly_menu), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(weekly_menu)
            
        # Offer to generate another menu or update information
        reply_keyboard = [['Generate Another Menu', 'Update My Information']]
        await update.message.reply_text(
            "What would you like to do next?",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, 
                one_time_keyboard=True,
                resize_keyboard=True
            ),
        )
    else:
        await update.message.reply_text(
            "I apologize, but I'm having trouble generating your menu at the moment. "
            "Please try again later or contact support if the issue persists."
        )

async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear stored user data"""
    user_id = update.message.from_user.id
    if user_id in user_data_store:
        del user_data_store[user_id]
        await update.message.reply_text("Your stored data has been cleared. Use /start to begin again.")
    else:
        await update.message.reply_text("No stored data found for your account.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

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
            MENU_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, menu_confirmation)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('diet', generate_diet))
    application.add_handler(CommandHandler('weekly_menu', weekly_menu))
    application.add_handler(CommandHandler('clear_data', clear_data))
    
    # Add admin command handlers
    application.add_handler(CommandHandler('stats', admin_stats))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('userinfo', user_info))
    application.add_handler(CommandHandler('admin_help', admin_help))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()