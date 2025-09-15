# JobBot - Automated Job Scraper

An intelligent job scraping automation that pulls product management internship opportunities from multiple sources and automatically adds them to your Notion database.

## 🎯 Features

- **Multi-Source Scraping**: Pulls jobs from 4 different sources:
  - **BuiltIn** - External job board
  - **LinkedIn** - External job board
  - **CMS/12twenty** - Kellogg's internal job system
  - **Handshake** - University job platform
- **Smart Filtering**: Automatically filters for product management internships
- **Notion Integration**: Automatically adds new jobs to your Notion database
- **Scheduled Automation**: Runs daily at 9 AM EST
- **Duplicate Prevention**: Checks for existing jobs before adding new ones

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- A Notion account with API access
- Kellogg Northwestern University credentials (for CMS and Handshake)

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd jobbot

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root with the following variables:

```env
# Notion API Configuration
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here

# Kellogg Northwestern University Credentials
KELLOGG_NETID=your_netid_here
KELLOGG_PASS=your_password_here

# Optional: Handshake-specific email (if different from NetID)
KELLOGG_EMAIL=your_email@kellogg.northwestern.edu
```

#### Getting Your Notion API Key and Database ID

1. **API Key**:

   - Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
   - Click "New integration"
   - Give it a name (e.g., "JobBot")
   - Copy the "Internal Integration Token"

2. **Database ID**:

   - Create a new Notion database with these properties:
     - `Title` (Title)
     - `Company` (Text)
     - `Location` (Text)
     - `URL` (URL)
     - `Date Added` (Date)
   - Copy the database ID from the URL (the long string between the last `/` and `?`)

3. **Share Database with Integration**:
   - In your Notion database, click "Share" → "Invite"
   - Add your integration by name

### 3. Local Testing

```bash
# Test individual scrapers
python builtin_scraper.py
python linkedin_scraper.py
python CMS_scraper.py
python handshake_scraper.py

# Test the full system
python main.py
```

### 4. Manual Job Scraping

```bash
# Run the scraper manually
curl -X GET "http://localhost:8000/run-scraper"
```

## 🌐 Deployment on Render

### 1. Prepare for Deployment

Create a `render.yaml` file in your project root:

```yaml
services:
  - type: web
    name: jobbot
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: NOTION_API_KEY
        sync: false
      - key: NOTION_DATABASE_ID
        sync: false
      - key: KELLOGG_NETID
        sync: false
      - key: KELLOGG_PASS
        sync: false
      - key: KELLOGG_EMAIL
        sync: false
```

### 2. Deploy to Render

1. **Connect Repository**:

   - Go to [https://render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:

   - **Name**: `jobbot` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**:

   - In the Render dashboard, go to your service
   - Navigate to "Environment" tab
   - Add all the environment variables from your `.env` file:
     - `NOTION_API_KEY`
     - `NOTION_DATABASE_ID`
     - `KELLOGG_NETID`
     - `KELLOGG_PASS`
     - `KELLOGG_EMAIL`

4. **Deploy**:
   - Click "Create Web Service"
   - Render will automatically build and deploy your application

### 3. Verify Deployment

Once deployed, you can:

- **Check Status**: Visit your Render service URL
- **Test Scraper**: `GET https://your-app-name.onrender.com/run-scraper`
- **View Logs**: Check the Render dashboard for any errors

## 📊 How It Works

### Scraping Process

1. **BuiltIn Scraper**: Scrapes product management internships from BuiltIn.com
2. **LinkedIn Scraper**: Searches LinkedIn for product management internships
3. **CMS Scraper**: Logs into Kellogg's 12twenty system and scrapes job postings
4. **Handshake Scraper**: Logs into Handshake and searches for product management internships

### Data Flow

```
Scrapers → Filter for Product Management Internships → Check Notion for Duplicates → Add New Jobs to Notion
```

### Scheduling

The scraper runs automatically every day at 9 AM EST using APScheduler. You can also trigger it manually via the `/run-scraper` endpoint.

## 🔧 Configuration

### Customizing Job Filters

To modify what jobs are scraped, edit the filter conditions in each scraper:

```python
# Example: In any scraper file
if ("product" in title_lower and
    ("intern" in title_lower or "internship" in title_lower)):
    jobs.append(job_info)
```

### Changing Schedule

Modify the cron schedule in `main.py`:

```python
scheduler.add_job(
    run_scraper_job,
    CronTrigger.from_crontab("0 9 * * *", timezone="America/New_York"),  # 9 AM EST daily
    id="daily_scraper_job",
    replace_existing=True
)
```

## 🐛 Troubleshooting

### Common Issues

1. **Login Failures**:

   - Verify your Kellogg credentials are correct
   - Check if your account has 2FA enabled (may need additional setup)

2. **Notion Integration Issues**:

   - Ensure your integration has access to the database
   - Verify the database ID is correct
   - Check that all required properties exist in your Notion database

3. **Scraping Errors**:

   - Websites may change their structure - check logs for selector errors
   - Some sites may have rate limiting - the scrapers include delays

4. **Render Deployment Issues**:
   - Check that all environment variables are set
   - Verify the build command completes successfully
   - Check Render logs for specific error messages

### Debug Mode

Run scrapers individually to debug issues:

```bash
# Test with debug output
python CMS_scraper.py
python handshake_scraper.py
```

## 📝 API Endpoints

- `GET /` - Health check
- `GET /run-scraper` - Manually trigger job scraping

## 🔒 Security Notes

- Never commit your `.env` file to version control
- Use environment variables for all sensitive data
- Consider using a secrets management service for production
- Regularly rotate your API keys and passwords

## 📈 Monitoring

- Check Render logs regularly for scraping success/failures
- Monitor your Notion database for new job additions
- Set up alerts if the scraper stops working

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the logs in Render dashboard
3. Test individual scrapers locally
4. Open an issue in the repository

---

**Happy Job Hunting! 🎯**
