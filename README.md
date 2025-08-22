# Nutrition Bot for Telegram

A comprehensive Telegram bot that helps users calculate their daily caloric needs and generate personalized diet plans using AI-powered menu generation. Now with enhanced user experience and administrative features.

## Features

- **Body Data Collection**: Collects user information including gender, age, weight, height, activity level, and fitness goals
- **BMR & TDEE Calculation**: Uses the Harris-Benedict equation to calculate Basal Metabolic Rate and Total Daily Energy Expenditure
- **Calorie Target Recommendation**: Provides personalized calorie targets based on user goals (weight loss, maintenance, or weight gain)
- **AI-Powered Menu Generation**: Integrates with DeepSeek AI to generate personalized weekly meal plans
- **Case-Insensitive Inputs**: Supports user inputs in any case for better usability
- **Web & Mobile Compatible**: Works seamlessly across Telegram web and mobile apps

## Extra Features & Improvements

### Enhanced User Experience
- **Persistent Data Storage**: Your nutritional information is now stored (inside bot memory), allowing you to generate new menus without re-entering your data
- **Smart Start Command**: The bot recognizes returning users and offers options to generate a new menu or update information
- **Multiple Menu Generation**: Generate as many menus as you want using your stored data
- **Data Management**: Clear your stored data at any time with the `/clear_data` command

### Admin Features
- **Access Control**: Restricted commands for bot administrators only
- **Usage Statistics**: View bot usage metrics with `/stats` command
- **User Management**: Get detailed information about specific users with `/userinfo <user_id>`
- **Broadcast Messages**: Prepare messages to be sent to all users with `/broadcast <message>`
- **Admin Help**: Access admin command documentation with `/admin_help`

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- (Optional) A DeepSeek API key from [DeepSeek Platform](https://platform.deepseek.com/) for AI menu generation

## Installation

1. Clone or download this project to your local machine
2. Install the required dependencies:

```bash
pip install python-telegram-bot openai
```

3. Create a `config.py` file in the project directory with your API tokens:

```python
# config.py
# Telegram Bot Token from @BotFather
HTTP_API_BOT_TOKEN = "your_telegram_bot_token_here"

# DeepSeek API Key (optional - for AI menu generation)
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"

# Other configuration settings (optional)
BOT_ADMINS = []  # Add Telegram user IDs of bot admins if needed
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

4. Ensure your `config.py` file is included in `.gitignore` to prevent accidental exposure of your API keys

## Usage

1. Run the bot:

```bash
python main.py
```

2. Open Telegram and search for your bot username
3. Start a conversation with `/start` command
4. Follow the bot's prompts to provide your information:
   - Gender (Male/Female)
   - Age
   - Weight (kg)
   - Height (cm)
   - Activity level (No activity, Minimal activity, Medium activity, etc.)
   - Goal (Lose weight, Maintain weight, Gain weight)

5. The bot will calculate your BMR, TDEE, and recommended daily calorie intake
6. Choose to generate a personalized weekly menu using AI

## Enhanced Usage Flow

### For New Users:
1. Start with `/start` command
2. Provide your body information (gender, age, weight, height)
3. Select your activity level and goal
4. Receive your calorie calculations
5. Generate your personalized weekly menu
6. Your data is automatically saved for future use

### For Returning Users:
1. Start with `/start` command
2. Choose to "Generate New Menu" with existing data or "Update My Information"
3. If generating a new menu, receive a fresh menu immediately
4. If updating information, go through the data collection process again


## Commands

- `/start` - Begin the conversation and provide your body data
- `/diet` - Generate a basic diet plan after providing your data
- `/weekly_menu` - Generate a detailed weekly menu after providing your data
- `/cancel` - Cancel the current operation at any time

## Project Structure

```
nutrition-bot/
├── main.py          # Main bot application
├── config.py        # Configuration file (API keys, not in repo)
├── .gitignore       # Git ignore file to exclude config.py
└── README.md        # This file
```

## Configuration Details

The bot uses a separate `config.py` file for security reasons:

- **HTTP_API_BOT_TOKEN**: Your Telegram bot token obtained from @BotFather
- **DEEPSEEK_API_KEY**: (Optional) API key for DeepSeek AI integration
- **BOT_ADMINS**: (Optional) List of Telegram user IDs who can access admin features
- **LOG_LEVEL**: (Optional) Logging level for debugging purposes

---

**Note**: Remember to keep your API keys secure and never commit them to version control systems. The provided `.gitignore` file helps prevent accidental exposure of your sensitive information.

---

## Admin Configuration

To use admin features, add administrator user IDs to your `config.py`:

```python
# config.py
HTTP_API_BOT_TOKEN = "your_telegram_bot_token_here"
DEEPSEEK_API_KEY = "your_deepseek_api_key_here"

# Add Telegram user IDs of administrators
BOT_ADMINS = [123456789, 987654321]  # Replace with actual user IDs

LOG_LEVEL = "INFO"
```

### Finding Your Telegram User ID
1. Start a conversation with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message to the bot
3. It will reply with your user ID

## Admin Commands

- `/stats` - View bot usage statistics and metrics
- `/broadcast <message>` - Prepare a message to be sent to all users
- `/userinfo <user_id>` - Get detailed information about a specific user
- `/admin_help` - Show help for all admin commands

---
**Note**: The admin features provide powerful tools for managing your bot. Use them responsibly and keep your admin user IDs secure. Always inform users about data collection practices and provide options to delete their data.
----

## Data Privacy

- User data is stored in memory and will be lost when the bot restarts
- Users can clear their data at any time with `/clear_data`
- Admin features only work for users whose IDs are in the `BOT_ADMINS` list
- For production use, consider implementing a proper database solution

## Customization

You can customize the bot by:

1. Modifying the activity levels and their multipliers in the `ACTIVITY_LEVELS` dictionary
2. Adjusting the calorie deficit/surplus values in the goal calculation
3. Changing the macronutrient distribution ratios in the diet plan
4. Customizing the AI prompt in the `generate_weekly_menu` function

## Future Enhancement Ideas

1. **Database Integration**: Replace in-memory storage with a proper database
2. **Menu History**: Keep a history of generated menus for each user
3. **Progress Tracking**: Allow users to track their progress over time
4. **Food Database**: Integrate with a food database for more accurate calorie counting
5. **Multi-language Support**: Add support for multiple languages


## Troubleshooting

### Common Issues

1. **Buttons not visible in Telegram Web**: 
   - The web version of Telegram has limited support for custom keyboards
   - The bot includes text instructions as a fallback for web users

2. **API errors**:
   - Ensure your DeepSeek API key is valid and has sufficient credits
   - Check your internet connection

3. **Message too long**:
   - The bot automatically splits long messages to comply with Telegram's limits

4. **Admin commands not working**:
   - Ensure your user ID is correctly added to the BOT_ADMINS list in config.py
   - Restart the bot after updating the configuration

5. **Data not persisting after bot restart**:
   - This is expected behavior with the current in-memory storage
   - Consider implementing a database for production use

6. **Menu generation taking too long**:
   - The AI processing time depends on the DeepSeek API response time
   - Large menus may take several seconds to generate

### Logs

The bot generates logs that can help with debugging. Check the console output for any error messages.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions about the bot, please check the troubleshooting section above or create an issue in the project repository.

## Disclaimer

This bot provides nutritional information for educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified health providers with questions about medical conditions.

---

Author: Igor Savinkin, [webscraping.pro](https://webscraping.pro)