# Automated Content Generation Agent

An AI-powered agent that researches trends, plans content, generates images, and schedules posts automatically to Telegram. Built with CrewAI orchestration and supporting both Gemini and ZAI language models.

## 🚀 Features

- **Trend Research**: Automatically researches trending topics in your niche
- **Content Planning**: Creates engaging captions, hashtags, and content strategies
- **Image Generation**: Generates stunning images using Replicate's ideogram-v3-turbo model
- **Smart Scheduling**: Posts content at specified intervals using natural language commands
- **Multi-LLM Support**: Works with both Gemini Flash and ZAI GLM models
- **Telegram Integration**: Posts directly to your Telegram chat or channel
- **CrewAI Orchestration**: Uses specialized AI agents for different tasks
- **REST API**: FastAPI-based web service with comprehensive endpoints

## 📋 Prerequisites

- Python 3.11+
- API keys for Gemini or ZAI
- Replicate API key for image generation
- Telegram Bot Token and Chat ID

## 🛠️ Installation

1. **Clone and navigate to the project:**
   ```bash
   cd content-agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Core Agent Configuration
CORE_AGENT_TYPE=gemini  # or zai
GEMINI_API_KEY=your_gemini_api_key
ZAI_API_KEY=your_zai_api_key

# Image Generation Configuration
REPLICATE_API_KEY=your_replicate_api_key
REPLICATE_MODEL=ideogram-ai/ideogram-v3-turbo

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

## 🔑 Getting API Keys

### Gemini API
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy it to your `.env` file

### Replicate API
1. Visit [Replicate](https://replicate.com/account)
2. Sign up and get your API token
3. Copy it to your `.env` file

### Telegram Bot
1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` to create a new bot
3. Copy the bot token

### Telegram Chat ID
1. Start a chat with your bot
2. Send a message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your chat ID in the response

## 🧪 Testing

Run the test suite to verify your setup:

```bash
python test_agent.py
```

This will test:
- Environment variables
- LLM connections
- Telegram bot connection
- Trend research
- Content planning
- Mini workflow

## 🚀 Running the Server

Start the FastAPI server:

```bash
python main.py
```

The server will run on `http://localhost:8000`

## 📡 API Endpoints

### Main Endpoints

- `GET /` - Root endpoint with basic info
- `GET /health` - Health check and system status
- `POST /schedule-posts` - Schedule automated content posting
- `POST /circlo-hook` - Handle Circlo webhooks

### Management Endpoints

- `GET /schedules` - View all active schedules
- `GET /schedule/{schedule_id}/status` - Get schedule status
- `POST /schedule/{schedule_id}/pause` - Pause a schedule
- `DELETE /schedule/{schedule_id}` - Cancel a schedule
- `GET /posts/history` - View post history
- `GET /stats` - System statistics

### OpenAPI Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📝 Usage Examples

### Schedule Content Posting

```bash
curl -X POST "http://localhost:8000/schedule-posts" \
     -H "Content-Type: application/json" \
     -d '{
       "command": "post each 5 minutes for the next 30 minutes",
       "user_preferences": {
         "niche": "AI technology",
         "keywords": ["machine learning", "automation", "future tech"],
         "brand_voice": "informative and engaging",
         "target_audience": "tech enthusiasts"
       }
     }'
```

### Natural Language Schedule Commands

The agent understands various schedule commands:

- `"post each 2 minutes for the next one hour"`
- `"post daily for 7 days"`
- `"post every 4 hours for 2 days"`
- `"post hourly for 12 hours"`

### Check Schedule Status

```bash
curl "http://localhost:8000/schedule/your_schedule_id/status"
```

## 🤖 How It Works

### 1. CrewAI Orchestration
The agent uses specialized AI agents:
- **Trend Research Specialist**: Finds trending topics
- **Content Strategy Specialist**: Plans engaging content
- **Visual Content Creator**: Optimizes image prompts
- **Social Media Manager**: Organizes posting schedule

### 2. Content Generation Workflow
1. Parse user's natural language schedule command
2. Research trends relevant to user's niche
3. Create content plans with captions and hashtags
4. Generate optimized prompts for image generation
5. Create images using Replicate API
6. Schedule posts at specified intervals
7. Post to Telegram automatically

### 3. Scheduling System
- Uses APScheduler for reliable timing
- Supports pause/resume functionality
- Tracks success/failure rates
- Provides detailed statistics

## 📊 Monitoring

### System Health
Check system status:
```bash
curl "http://localhost:8000/health"
```

### Statistics
View system statistics:
```bash
curl "http://localhost:8000/stats"
```

### Post History
View recent posts:
```bash
curl "http://localhost:8000/posts/history"
```

## 🎯 Advanced Features

### Content Types
The agent creates various content types:
- Educational posts
- Entertaining content
- Promotional material
- Interactive posts

### Image Generation
- Uses Replicate's ideogram-v3-turbo model
- Optimizes prompts for best results
- Includes retry logic for failed generations
- Supports various aspect ratios

### Telegram Integration
- Supports text and image posts
- Automatic hashtag formatting
- Error notifications
- Completion notifications

## 🛡️ Safety Features

- Content validation before posting
- Error handling and retry logic
- Rate limiting for API calls
- Schedule conflict detection
- Emergency stop functionality

## 🔧 Customization

### Adding New LLMs
To add a new LLM provider:

1. Create a new wrapper in `agents/llm_wrappers.py`
2. Update the `_get_llm()` method in relevant classes
3. Update the environment variables

### Custom Content Types
Modify the content planner to support new content types in `agents/content_planner.py`.

### Additional Platforms
Extend the Telegram client to support other social media platforms.

## 📝 Troubleshooting

### Common Issues

1. **Environment Variables Not Loading**
   - Ensure `.env` file exists
   - Check for typos in variable names
   - Run `python test_agent.py` to verify

2. **Telegram Bot Not Receiving Messages**
   - Verify bot token is correct
   - Check chat ID is correct
   - Ensure bot has permission to post in the chat

3. **Image Generation Failing**
   - Check Replicate API key
   - Verify model name is correct
   - Check account credits

4. **LLM Connection Issues**
   - Verify API key is valid
   - Check internet connection
   - Ensure model name is correct

### Debug Mode

Enable verbose logging by setting:
```env
LOG_LEVEL=DEBUG
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [CrewAI](https://crewai.com/) - AI agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Replicate](https://replicate.com/) - Image generation
- [Telegram Bot API](https://core.telegram.org/bots/api) - Messaging platform

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Run the test suite for diagnostics
3. Create an issue in the repository

---

**Built with ❤️ for automated content creation**