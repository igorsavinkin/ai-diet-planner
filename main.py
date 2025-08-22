import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ConversationHandler, ContextTypes, filters
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
GENDER, AGE, WEIGHT, HEIGHT, ACTIVITY, GOAL = range(6)

# Activity levels with multipliers
ACTIVITY_LEVELS = {
    "No activity": 1.2,
    "Minimal activity": 1.375,
    "Medium activity": 1.55,
    "Above average activity": 1.725,
    "High activity": 1.9
}

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

# Gender handler
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

# Age handler
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

# Weight handler
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

# Height handler
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
            f'If you don\'t see buttons, please type one of these options:\n{activity_instructions}',
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

# Activity level handler
async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    activity_input = update.message.text.strip()
    
    # Validate input
    if activity_input not in ACTIVITY_LEVELS:
        activity_options = list(ACTIVITY_LEVELS.keys())
        activity_instructions = "\n".join([f"- {option}" for option in activity_options])
        
        await update.message.reply_text(
            f'Please select a valid activity level from these options:\n{activity_instructions}'
        )
        return ACTIVITY
        
    context.user_data['activity'] = activity_input
    logger.info("Activity level of %s: %s", user.first_name, activity_input)
    
    # Ask for goal with both buttons and text instructions
    goal_options = ['Lose weight', 'Maintain weight', 'Gain weight']
    reply_keyboard = [goal_options]  # All buttons in one row
    
    await update.message.reply_text(
        'What is your goal?\n\n'
        'If you don\'t see buttons, please type one of these options:\n'
        '- Lose weight\n- Maintain weight\n- Gain weight',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, 
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return GOAL

# Goal handler and BMR calculation
async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    goal_input = update.message.text.strip()
    
    # Validate input
    valid_goals = ['Lose weight', 'Maintain weight', 'Gain weight']
    if goal_input not in valid_goals:
        await update.message.reply_text(
            'Please select a valid goal. Type one of these options:\n'
            '- Lose weight\n- Maintain weight\n- Gain weight'
        )
        return GOAL
        
    context.user_data['goal'] = goal_input
    logger.info("Goal of %s: %s", user.first_name, goal_input)
    
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
    if goal_input == 'Lose weight':
        calories = tdee - 500  # Create deficit for weight loss
    elif goal_input == 'Gain weight':
        calories = tdee + 500  # Create surplus for weight gain
    else:
        calories = tdee  # Maintain weight
    
    context.user_data['bmr'] = bmr
    context.user_data['tdee'] = tdee
    context.user_data['calories'] = calories
    
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
        "Type /diet to generate your personalized meal plan!",
        reply_markup=ReplyKeyboardRemove(),
    )
    
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        'Bye! I hope we can talk again some day.', 
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# Generate diet plan
async def generate_diet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'calories' not in context.user_data:
        await update.message.reply_text(
            "Please provide your body data first using /start"
        )
        return
    
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
        "Remember to adjust based on your preferences and consult with a healthcare professional for personalized advice."
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

# Main function
def main() -> None:
    # Create the Application using ApplicationBuilder
    application = ApplicationBuilder().token("8230736258:AAGlpKkZzW2qgMTfJA4KzNCCgfjagSaIA7g").build()

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
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('diet', generate_diet))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()