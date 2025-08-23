#!/usr/bin/env python3
# main.py
import logging
import json
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters, CallbackQueryHandler
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
        user_id = update.callback_query.from_user.id if update.callback_query else update.message.from_user.id
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ This command is for administrators only.")
            else:
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
    
    if update.callback_query:
        await update.callback_query.message.reply_text(stats_message)
    else:
        await update.message.reply_text(stats_message)

@admin_required
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message to all users (admin only)"""
    if not context.args:
        if update.callback_query:
            await update.callback_query.message.reply_text("Usage: /broadcast <message>")
        else:
            await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    
    # In a real implementation, you would iterate through your user database
    # For now, we'll just confirm the command works
    response_text = (
        f"📢 Broadcast message prepared:\n\n{message}\n\n"
        f"(In a full implementation, this would be sent to all {len(user_data_store)} users)"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(response_text)
    else:
        await update.message.reply_text(response_text)

@admin_required
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get information about a specific user (admin only)"""
    if not context.args:
        if update.callback_query:
            await update.callback_query.message.reply_text("Usage: /userinfo <user_id>")
        else:
            await update.message.reply_text("Usage: /userinfo <user_id>")
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        if update.callback_query:
            await update.callback_query.message.reply_text("Please provide a valid user ID.")
        else:
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
    
    if update.callback_query:
        await update.callback_query.message.reply_text(user_info_msg)
    else:
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
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text)
    else:
        await update.message.reply_text(help_text)

# *************** Utility functions *****************
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
        keyboard = [
            [InlineKeyboardButton("Generate New Menu", callback_data="generate_menu")],
            [InlineKeyboardButton("Update My Information", callback_data="update_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Welcome back {user.first_name}! 👋\n\n"
            "I see you've already provided your information before.\n\n"
            "Would you like to generate a new menu with your existing data "
            "or update your information?",
            reply_markup=reply_markup
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
        
        # Ask for gender with inline buttons
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="gender_male")],
            [InlineKeyboardButton("Female", callback_data="gender_female")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            'Please select your gender:',
            reply_markup=reply_markup
        )
        return GENDER

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    gender_input = query.data.replace("gender_", "")
    
    # Validate input
    if gender_input not in ['male', 'female']:
        await query.edit_message_text(
            'Please select a valid gender:'
        )
        return GENDER
    
    context.user_data['gender'] = gender_input.capitalize()
    logger.info("Gender of %s: %s", user.first_name, context.user_data['gender'])
    
    # Edit the message to remove buttons
    await query.edit_message_text(
        'Great! Now please enter your age:'
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
        
        # Ask for activity level with inline buttons
        activity_options = list(ACTIVITY_LEVELS.keys())
        keyboard = [[InlineKeyboardButton(option, callback_data=f"activity_{i}")] 
                   for i, option in enumerate(activity_options)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            'Please select your activity level:',
            reply_markup=reply_markup
        )
        return ACTIVITY
    except ValueError:
        await update.message.reply_text('Please enter a valid number for your height:')
        return HEIGHT

async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    activity_idx = int(query.data.replace("activity_", ""))
    activity_options = list(ACTIVITY_LEVELS.keys())
    
    if activity_idx < 0 or activity_idx >= len(activity_options):
        await query.edit_message_text('Please select a valid activity level:')
        return ACTIVITY
        
    # Set the activity level
    context.user_data['activity'] = activity_options[activity_idx]
    logger.info("Activity level of %s: %s", user.first_name, context.user_data['activity'])
    
    # Ask for goal with inline buttons
    goal_options = ['Lose weight', 'Maintain weight', 'Gain weight']
    keyboard = [[InlineKeyboardButton(option, callback_data=f"goal_{i}")] 
               for i, option in enumerate(goal_options)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        'What is your goal?',
        reply_markup=reply_markup
    )
    return GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    goal_idx = int(query.data.replace("goal_", ""))
    goal_options = ['Lose weight', 'Maintain weight', 'Gain weight']
    
    if goal_idx < 0 or goal_idx >= len(goal_options):
        await query.edit_message_text('Please select a valid goal:')
        return GOAL
        
    # Set the goal
    context.user_data['goal'] = goal_options[goal_idx]
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
    keyboard = [
        [InlineKeyboardButton("Yes, generate menu! 🍽️", callback_data="menu_yes")],
        [InlineKeyboardButton("No, update my information", callback_data="menu_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
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
        "Would you like me to generate a personalized menu for a week?",
        reply_markup=reply_markup
    )
    
    return MENU_CONFIRM

async def menu_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    response = query.data.replace("menu_", "")
    
    # Handle different response types
    if response == 'yes':
        await query.edit_message_text(
            "Great! I'm generating your personalized menu for a week. 🥗 🍱 🌮 This may take a moment...🙂🙂🙂"
        )
        
        # Generate weekly menu using AI
        weekly_menu = await generate_weekly_menu(context.user_data)
        
        if weekly_menu:
            # Split long message into parts if needed (Telegram has a message length limit)
            if len(weekly_menu) > 4000:
                parts = [weekly_menu[i:i+4000] for i in range(0, len(weekly_menu), 4000)]
                for part in parts:
                    await query.message.reply_text(part)
            else:
                await query.message.reply_text(weekly_menu)
            
            # Ask for tip after successful menu generation
            return await ask_for_tip(query.message, context)
        else:
            await query.message.reply_text(
                "I apologize, but I'm having trouble generating your menu at the moment. "
                "Please try again later or contact support if the issue persists."
            )
            # Show navigation options even if menu generation failed
            await show_navigation_options(query.message, context)
            return ConversationHandler.END
            
    elif response == 'no':
        # Ask for gender to start the update process
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="gender_male")],
            [InlineKeyboardButton("Female", callback_data="gender_female")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            'No problem! Let\'s update your information. Please select your gender:',
            reply_markup=reply_markup
        )
        return GENDER
    else:
        keyboard = [
            [InlineKeyboardButton("Yes, generate menu! 🍽️", callback_data="menu_yes")],
            [InlineKeyboardButton("No, update my information", callback_data="menu_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Please select an option:",
            reply_markup=reply_markup
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
    Focus on common, affordable preferrably European ingredients. Include portion sizes in grams or common measurements.
    
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
    
    Add no more than 3 notes
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
        'Bye! I hope we can talk again some day.'
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
    keyboard = [
        [InlineKeyboardButton("Yes, generate menu! 🍽️", callback_data="menu_yes")],
        [InlineKeyboardButton("No, thanks", callback_data="menu_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
        "Would you like me to generate a detailed weekly menu?",
        reply_markup=reply_markup
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
        "I'm generating your personalized weekly menu. 🥗 🍱 🌮 This may take a moment...🙂🙂"
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
        keyboard = [
            [InlineKeyboardButton("Generate Another Menu", callback_data="generate_menu")],
            [InlineKeyboardButton("Update My Information", callback_data="update_info")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "What would you like to do next?",
            reply_markup=reply_markup
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

## PAYMENT 
# Add this to your conversation states
TIP_AMOUNT, TIP_CONFIRM = range(8, 10)  # Extend the conversation states

async def ask_for_tip(message, context: ContextTypes.DEFAULT_TYPE):
    """Ask user if they want to leave a tip after menu generation"""
    try:
        from config import TIP_AMOUNTS
    except ImportError:
        return  # Tipping not configured
    
    keyboard = [
        [InlineKeyboardButton(f"{TIP_AMOUNTS['2']['emoji']} $2", callback_data="tip_2")],
        [InlineKeyboardButton(f"{TIP_AMOUNTS['5']['emoji']} $5", callback_data="tip_5")],
        [InlineKeyboardButton(f"{TIP_AMOUNTS['10']['emoji']} $10", callback_data="tip_10")],
        [InlineKeyboardButton("Custom Amount", callback_data="tip_custom")],
        [InlineKeyboardButton("No, thank you", callback_data="tip_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "🎉 Your menu is ready! \n\n"
        "Would you like to leave a tip 🪙 to support the development of this bot?\n"
        "Your support helps keep this service free and improving!",
        reply_markup=reply_markup
    )
    return TIP_AMOUNT

async def handle_tip_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the tip amount selection"""
    query = update.callback_query
    await query.answer()
    
    try:
        from config import TIP_AMOUNTS, PAYPAL_ME_USERNAME
    except ImportError:
        await query.edit_message_text("Thank you for using the bot! 😊")
        # Show navigation options
        await show_navigation_options(query.message, context)
        return ConversationHandler.END
    
    tip_data = query.data.replace("tip_", "")
    
    if tip_data == "no":
        await query.edit_message_text(
            "Thank you for using the bot! 😊\n\n"
            "You can always generate a new menu with /weekly_menu"
        )
        # Show navigation options
        await show_navigation_options(query.message, context)
        return ConversationHandler.END
    elif tip_data == "custom":
        await query.edit_message_text(
            "Please enter your custom tip amount in USD:"
        )
        return TIP_CONFIRM
    else:
        # Parse the selected amount
        amount = tip_data
        if amount in TIP_AMOUNTS:
            paypal_link = f"https://paypal.me/{PAYPAL_ME_USERNAME}/{amount}USD"
            message = (
                f"Thank you for your ${amount} tip! 💖\n\n"
                f"Please complete your payment using this link:\n{paypal_link}\n\n"
                "Your support is greatly appreciated and helps improve this service!"
            )
            
            await query.edit_message_text(
                message,
                disable_web_page_preview=True
            )
            
            # Show navigation options after payment message
            await show_navigation_options(query.message, context)
        else:
            await query.edit_message_text(
                "Thank you for using the bot!",
            )
            # Show navigation options
            await show_navigation_options(query.message, context)
        
        return ConversationHandler.END

async def handle_custom_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom tip amount"""
    try:
        from config import PAYPAL_ME_USERNAME
    except ImportError:
        await update.message.reply_text("Thank you for using the bot!")
        return ConversationHandler.END
    
    try:
        custom_amount = float(update.message.text)
        if custom_amount < 1:
            await update.message.reply_text("Minimum tip amount is $1. Please enter a valid amount:")
            return TIP_CONFIRM
        
        paypal_link = f"https://paypal.me/{PAYPAL_ME_USERNAME}/{custom_amount}USD"
        message = (
            f"Thank you for your ${custom_amount} tip! 💖\n\n"
            f"Please complete your payment using this link:\n{paypal_link}\n\n"
            "Your support is greatly appreciated and helps improve this service!"
        )
        
        await update.message.reply_text(
            message,
            disable_web_page_preview=True
        )
        
        # Show navigation options after payment message
        await show_navigation_options(update.message, context)
        
    except ValueError:
        await update.message.reply_text("Please enter a valid number for your tip amount:")
        return TIP_CONFIRM
    
    return ConversationHandler.END

async def show_navigation_options(message, context: ContextTypes.DEFAULT_TYPE):
    """Show navigation options to continue using the bot"""
    keyboard = [
        [InlineKeyboardButton("📋 Generate New Menu", callback_data="generate_menu")],
        [InlineKeyboardButton("🔄 Update My Info", callback_data="update_info")],
        [InlineKeyboardButton("📊 View My Stats", callback_data="view_stats")],
        [InlineKeyboardButton("❌ Clear My Data", callback_data="clear_data")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "What would you like to do next?",
        reply_markup=reply_markup
    )

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle navigation menu selections with the new structure"""
    query = update.callback_query
    await query.answer()
    
    user_choice = query.data
    user_id = query.from_user.id
    has_data = user_id in user_data_store and user_data_store[user_id].get('calories')
    is_user_admin = is_admin(user_id)
    
    if user_choice == "generate_menu":
        # Check if user has existing data
        if not has_data:
            await query.edit_message_text(
                "Please provide your body data first to generate a menu."
            )
            # Show the main menu again
            return await show_main_menu(query.message, user_id, has_data, is_user_admin)
        
        # Use stored data
        context.user_data.update(user_data_store[user_id])
        await query.edit_message_text(
            "I'm generating your personalized weekly menu.  🥗 🍱 🌮  This may take a moment...🙂"
        )
        
        # Generate weekly menu using AI
        weekly_menu = await generate_weekly_menu(context.user_data)
        
        if weekly_menu:
            # Split long message into parts if needed
            if len(weekly_menu) > 4000:
                parts = [weekly_menu[i:i+4000] for i in range(0, len(weekly_menu), 4000)]
                for part in parts:
                    await context.bot.send_message(chat_id=query.message.chat_id, text=part)
            else:
                await context.bot.send_message(chat_id=query.message.chat_id, text=weekly_menu)
            
            # Ask for tip after successful menu generation
            await ask_for_tip(query.message, context)
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="I apologize, but I'm having trouble generating your menu at the moment. "
                     "Please try again later or contact support if the issue persists."
            )
            # Show main menu again
            await show_main_menu(query.message, user_id, has_data, is_user_admin)
        
    elif user_choice == "enter_body_data" or user_choice == "update_info":
        await query.edit_message_text(
            "Let's collect your body data!"
        )
        # Create a fake update object with message for the start function
        fake_update = Update(update.update_id + 1, message=query.message)
        return await start(fake_update, context)
        
    elif user_choice == "view_stats":
        if not is_user_admin:
            await query.edit_message_text(
                "❌ This option is for administrators only."
            )
            # Show main menu again
            return await show_main_menu(query.message, user_id, has_data, is_user_admin)
        
        if user_id not in user_data_store:
            await query.edit_message_text(
                "No data found. Please set up your information first."
            )
        else:
            user_data = user_data_store[user_id]
            stats_message = (
                "📊 Your Nutrition Stats:\n\n"
                f"Gender: {user_data.get('gender', 'N/A')}\n"
                f"Age: {user_data.get('age', 'N/A')}\n"
                f"Weight: {user_data.get('weight', 'N/A')} kg\n"
                f"Height: {user_data.get('height', 'N/A')} cm\n"
                f"Activity: {user_data.get('activity', 'N/A')}\n"
                f"Goal: {user_data.get('goal', 'N/A')}\n"
                f"Daily Calories: {user_data.get('calories', 'N/A')} kcal\n"
                f"BMR: {user_data.get('bmr', 'N/A')}\n"
                f"TDEE: {user_data.get('tdee', 'N/A')}"
            )
            await query.edit_message_text(stats_message)
        
        # Show main menu again
        await show_main_menu(query.message, user_id, has_data, is_user_admin)
            
    elif user_choice == "clear_data":
        if user_id in user_data_store:
            del user_data_store[user_id]
            await query.edit_message_text(
                "Your data has been cleared successfully!"
            )
            has_data = False  # Update the flag
        else:
            await query.edit_message_text(
                "No data found to clear."
            )
        
        # Show main menu again
        await show_main_menu(query.message, user_id, has_data, is_user_admin)
        
    elif user_choice == "main_menu":
        await query.edit_message_text(
            "Returning to main menu..."
        )
        # Show the main menu
        await show_main_menu(query.message, user_id, has_data, is_user_admin)
    
    return ConversationHandler.END


async def show_main_menu(message, user_id, has_data=False, is_admin=False):
    """Show the main menu with conditional options"""
    keyboard = []
    
    # 1. Enter/Update body data
    if has_data:
        keyboard.append([InlineKeyboardButton("👌Update My Info", callback_data="update_info")])
    else:
        keyboard.append([InlineKeyboardButton("💪Enter My Body Data", callback_data="enter_body_data")])
    
    # 2. Generate menu (only if has data)
    if has_data:
        keyboard.append([InlineKeyboardButton("🍽️ Generate New Menu", callback_data="generate_menu")])
    
    # 3. View stats (only if admin)
    if is_admin:
        keyboard.append([InlineKeyboardButton("📊 View My Stats", callback_data="view_stats")])
    
    # 4. Clear data (only if has data)
    if has_data:
        keyboard.append([InlineKeyboardButton("❌ Clear My Data", callback_data="clear_data")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "🏠 Main Menu - Please choose an option:",
        reply_markup=reply_markup
    )


# Main function
def main() -> None:
    # Create the Application using ApplicationBuilder with token from config
    application = ApplicationBuilder().token(HTTP_API_BOT_TOKEN).build()

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [CallbackQueryHandler(gender)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
            ACTIVITY: [CallbackQueryHandler(activity)],
            GOAL: [CallbackQueryHandler(goal)],
            MENU_CONFIRM: [CallbackQueryHandler(menu_confirmation)],
            TIP_AMOUNT: [CallbackQueryHandler(handle_tip_amount)],
            TIP_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_tip)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True,  # Add this line to fix the warning
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('diet', generate_diet))
    application.add_handler(CommandHandler('weekly_menu', weekly_menu))
    application.add_handler(CommandHandler('clear_data', clear_data))
    
    # Add navigation handler
    application.add_handler(CallbackQueryHandler(
        handle_navigation, 
        pattern="^(generate_menu|update_info|enter_body_data|view_stats|clear_data|main_menu)$"
    ))
    
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