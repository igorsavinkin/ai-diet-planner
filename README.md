# Nutrition Bot for Telegram

A comprehensive Telegram bot that helps users calculate their daily caloric needs and generate personalized diet plans using AI-powered menu generation.

## Features

- **Body Data Collection**: Collects user information including gender, age, weight, height, activity level, and fitness goals
- **BMR & TDEE Calculation**: Uses the Harris-Benedict equation to calculate Basal Metabolic Rate and Total Daily Energy Expenditure
- **Calorie Target Recommendation**: Provides personalized calorie targets based on user goals (weight loss, maintenance, or weight gain)
- **AI-Powered Menu Generation**: Integrates with DeepSeek AI to generate personalized weekly meal plans
- **Case-Insensitive Inputs**: Supports user inputs in any case for better usability
- **Web & Mobile Compatible**: Works seamlessly across Telegram web and mobile apps

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

## Customization

You can customize the bot by:

1. Modifying the activity levels and their multipliers in the `ACTIVITY_LEVELS` dictionary
2. Adjusting the calorie deficit/surplus values in the goal calculation
3. Changing the macronutrient distribution ratios in the diet plan
4. Customizing the AI prompt in the `generate_weekly_menu` function

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

### Logs

The bot generates logs that can help with debugging. Check the console output for any error messages.

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues or have questions about the bot, please check the troubleshooting section above or create an issue in the project repository.

## Disclaimer

This bot provides nutritional information for educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified health providers with questions about medical conditions.

---

**Note**: Remember to keep your API keys secure and never commit them to version control systems. The provided `.gitignore` file helps prevent accidental exposure of your sensitive information.

---

Author: Igor Savinkin, [webscraping.pro](https://webscraping.pro)