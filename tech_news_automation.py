"""
Tech News Automation - Dual Mode (Local HTML / GitHub Email)
"""

import feedparser
import requests
import smtplib
import os
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dotenv import load_dotenv
import webbrowser

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechNewsAutomation:
    def __init__(self):
        # Check if running on GitHub Actions
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        # Email configuration
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.receiver_email = os.getenv('RECEIVER_EMAIL', self.sender_email)
        
        # Tech news RSS feeds - PURE TECH SOURCES ONLY
        self.news_sources = {
            # Hardware & Gadgets
            '🖥️ AnandTech': 'https://www.anandtech.com/rss',
            '📱 GSMArena': 'https://www.gsmarena.com/rss-news-reviews.php3',
            '🔧 Tom\'s Hardware': 'https://www.tomshardware.com/feeds/all',
            '🎮 Engadget': 'https://www.engadget.com/rss.xml',
            
            # Software & Development
            '💻 Hacker News': 'https://hnrss.org/frontpage?count=20',
            '🚀 GitHub Trends': 'https://github.com/trending/feed',
            '🐍 Python.org': 'https://www.python.org/blogs/rss/',
            '⚛️ React Blog': 'https://reactjs.org/feed.xml',
            '📦 npm Blog': 'https://blog.npmjs.org/rss',
            
            # Tech News & Reviews
            '🔥 TechCrunch': 'https://techcrunch.com/feed/',
            '🔬 Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
            '📱 The Verge Tech': 'https://www.theverge.com/tech/rss/index.xml',
            '🌐 Wired Tech': 'https://www.wired.com/feed/rss',
            '🖥️ TechSpot': 'https://www.techspot.com/backend.xml',
            
            # AI & Emerging Tech
            '🤖 OpenAI Blog': 'https://openai.com/blog/rss/',
            '🧠 Google AI': 'https://ai.googleblog.com/feeds/posts/default',
            '🚀 MIT Tech Review': 'https://www.technologyreview.com/feed/',
            '🔮 The Next Web': 'https://thenextweb.com/feed/',
            
            # Security & Privacy
            '🔒 Krebs Security': 'https://krebsonsecurity.com/feed/',
            '🛡️ Schneier on Security': 'https://www.schneier.com/feed/',
            '⚠️ Threatpost': 'https://threatpost.com/feed/',
            
            # Cloud & Infrastructure
            '☁️ AWS Blog': 'https://aws.amazon.com/blogs/aws/feed/',
            '🌀 Azure Blog': 'https://azure.microsoft.com/en-us/blog/feed/',
            '📊 Google Cloud Blog': 'https://cloud.google.com/blog/rss',
            
            # Linux & Open Source
            '🐧 Linux Journal': 'https://www.linuxjournal.com/node/feed',
            '🐚 Ubuntu Blog': 'https://ubuntu.com/blog/feed',
            '📦 Arch Linux News': 'https://archlinux.org/feeds/news/',
        }
        
        # Tech keywords to look for
        self.keywords = [
            # Programming
            'Python', 'JavaScript', 'TypeScript', 'React', 'Vue', 'Node.js',
            'Java', 'C++', 'Rust', 'Go', 'Kotlin', 'Swift',
            
            # AI/ML
            'AI', 'Artificial Intelligence', 'Machine Learning', 'Deep Learning',
            'Neural Network', 'LLM', 'GPT', 'Transformer',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'GCP', 'Google Cloud', 'Kubernetes', 'Docker',
            'DevOps', 'CI/CD', 'Microservices', 'Serverless',
            
            # Security
            'Cybersecurity', 'Encryption', 'Zero Trust', 'VPN', 'Firewall',
            'Malware', 'Ransomware', 'Phishing',
            
            # Hardware
            'CPU', 'GPU', 'RAM', 'SSD', 'NVIDIA', 'AMD', 'Intel',
            'Smartphone', 'Laptop', 'Processor', 'Chip',
            
            # Emerging Tech
            'Quantum', 'Blockchain', 'IoT', 'AR', 'VR', 'Metaverse',
            '5G', '6G', 'Autonomous', 'Drone',
        ]
        
        logger.info(f"Running in {'GitHub Actions' if self.is_github_actions else 'Local'} mode")
    
    def fetch_all_news(self):
        """Get news from all sources"""
        all_articles = []
        
        for source_name, feed_url in self.news_sources.items():
            try:
                logger.info(f"Fetching from {source_name}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:8]:  # Get top 8 from each source
                    article = {
                        'source': source_name,
                        'title': entry.title[:150],
                        'link': entry.link,
                        'published': entry.get('published', 'Recent'),
                        'summary': entry.get('summary', 'No summary available')[:250],
                        'relevance': self.check_relevance(entry.title + ' ' + entry.get('summary', ''))
                    }
                    
                    all_articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error with {source_name}: {e}")
        
        # Sort by relevance
        all_articles.sort(key=lambda x: x['relevance'], reverse=True)
        
        return all_articles[:30]  # Return top 30 articles
    
    def check_relevance(self, text):
        """Check how relevant the article is"""
        score = 0
        text_lower = text.lower()
        
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                score += 2
        
        # Bonus for breaking/urgent news
        urgency_words = ['breaking', 'urgent', 'critical', 'alert', 'exclusive']
        for word in urgency_words:
            if word in text_lower:
                score += 1
        
        return score
    
    def create_html_content(self, articles):
        """Create beautiful HTML content for email or file"""
        
        # Count articles per source
        source_count = {}
        for article in articles:
            source = article['source']
            source_count[source] = source_count.get(source, 0) + 1
        
        source_summary = " | ".join([f"{source}: {count}" for source, count in source_count.items()])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tech News Digest - {datetime.now().strftime('%B %d, %Y')}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 700px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f7fa;
                }}
                .email-container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 8px;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .header .date {{
                    opacity: 0.9;
                    font-size: 14px;
                    margin-top: 5px;
                }}
                .stats {{
                    background: #e8f4fd;
                    padding: 15px;
                    border-radius: 6px;
                    margin-bottom: 25px;
                    font-size: 14px;
                    color: #2c5282;
                }}
                .article {{
                    border-left: 4px solid #4299e1;
                    padding: 15px;
                    margin-bottom: 20px;
                    background: #f8fafc;
                    border-radius: 0 6px 6px 0;
                }}
                .article.high-relevance {{
                    border-left-color: #48bb78;
                    background: #f0fff4;
                }}
                .article-title {{
                    margin: 0 0 10px 0;
                }}
                .article-title a {{
                    color: #2d3748;
                    text-decoration: none;
                    font-size: 18px;
                    font-weight: 600;
                }}
                .article-title a:hover {{
                    color: #4299e1;
                    text-decoration: underline;
                }}
                .meta {{
                    font-size: 13px;
                    color: #718096;
                    margin-bottom: 8px;
                }}
                .source {{
                    background: #e2e8f0;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .summary {{
                    font-size: 14px;
                    color: #4a5568;
                    line-height: 1.5;
                }}
                .relevance-badge {{
                    background: #48bb78;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 11px;
                    margin-left: 10px;
                }}
                .keywords {{
                    margin-top: 20px;
                    padding: 10px;
                    background: #fffaf0;
                    border-radius: 6px;
                    font-size: 13px;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                    text-align: center;
                    color: #a0aec0;
                    font-size: 12px;
                }}
                @media (max-width: 600px) {{
                    body {{
                        padding: 10px;
                    }}
                    .email-container {{
                        padding: 15px;
                    }}
                    .article-title a {{
                        font-size: 16px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>📰 Your Tech News Digest</h1>
                    <div class="date">{datetime.now().strftime("%A, %B %d, %Y")}</div>
                </div>
                
                <div class="stats">
                    <strong>📊 Today's Summary:</strong> {len(articles)} articles from {len(source_count)} sources<br>
                    <strong>📌 Sources:</strong> {source_summary}
                </div>
                
                <h2>🎯 Top Stories</h2>
        """
        
        # Add each article
        for i, article in enumerate(articles, 1):
            relevance_class = "high-relevance" if article['relevance'] > 0 else ""
            relevance_badge = f'<span class="relevance-badge">Relevant</span>' if article['relevance'] > 0 else ""
            
            html += f"""
                <div class="article {relevance_class}">
                    <h3 class="article-title">
                        {i}. <a href="{article['link']}" target="_blank">{article['title']}</a>
                        {relevance_badge}
                    </h3>
                    <div class="meta">
                        <span class="source">{article['source']}</span>
                        📅 {article['published']}
                    </div>
                    <div class="summary">
                        {article['summary']}...
                        <a href="{article['link']}" style="color: #4299e1; font-size: 12px;">[Read more]</a>
                    </div>
                </div>
            """
        
        # Add footer
        html += f"""
                <div class="keywords">
                    <strong>🔍 Tracking keywords:</strong> {', '.join(self.keywords[:8])}...
                </div>
                
                <div class="footer">
                    <p>This email was automatically generated by your Tech News Automation system.</p>
                    <p>💡 Tip: Check your spam folder if you don't see these emails regularly</p>
                    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, html_content):
        """Send email to multiple recipients using BCC"""
        
        if not all([self.sender_email, self.sender_password]):
            logger.error("❌ Email credentials missing in .env file")
            return False
        
        # Get all recipients
        receiver_email = self.receiver_email
        additional_emails_str = os.getenv('ADDITIONAL_EMAILS', '')
        
        # Parse additional emails
        additional_emails = []
        if additional_emails_str:
            additional_emails = [email.strip() for email in additional_emails_str.split(',') if email.strip()]
        
        # Combine and remove duplicates
        all_recipients = list(set([receiver_email] + additional_emails))
        
        if len(all_recipients) == 0:
            logger.error("❌ No recipient emails found")
            return False
        
        logger.info(f"📧 Preparing email for {len(all_recipients)} recipients")
        
        try:
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📡 Tech News Digest - {datetime.now().strftime('%b %d, %Y')}"
            msg['From'] = f"Tech News Bot <{self.sender_email}>"
            
            # Set TO and BCC
            msg['To'] = receiver_email
            if len(all_recipients) > 1:
                bcc_recipients = all_recipients[1:]  # All except first
                msg['Bcc'] = ', '.join(bcc_recipients)
                logger.info(f"  To: {receiver_email}")
                logger.info(f"  BCC: {len(bcc_recipients)} recipients")
            
            # Attach HTML
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            try:
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
                
            except Exception as e1:
                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
            
            logger.info(f"✅ Email sent to {len(all_recipients)} recipients successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def save_to_html_file(self, html_content):
        """Save HTML content to a local file"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"Tech_News_Digest_{timestamp}.html"
            
            # Save file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            absolute_path = os.path.abspath(filename)
            logger.info(f"💾 Saved to local file: {absolute_path}")
            
            # Try to open in browser
            try:
                webbrowser.open(f'file://{absolute_path}')
                logger.info("🌐 Opened in default browser")
            except:
                pass
            
            return absolute_path
            
        except Exception as e:
            logger.error(f"❌ Failed to save file: {e}")
            return None
    
    def run(self):
        """Main function to run the entire process"""
        logger.info("=" * 60)
        logger.info("🚀 STARTING TECH NEWS AUTOMATION")
        logger.info("=" * 60)
        
        try:
            # Step 1: Fetch news
            logger.info("📥 Fetching latest tech news...")
            articles = self.fetch_all_news()
            
            if not articles:
                logger.warning("No articles found!")
                return
            
            logger.info(f"✅ Found {len(articles)} articles")
            
            # Step 2: Create HTML content
            logger.info("📧 Creating email content...")
            html_content = self.create_html_content(articles)
            
            # Step 3: Send email or save file based on mode
            if self.is_github_actions:
                # On GitHub Actions: Send email
                logger.info("🚀 Running on GitHub Actions - Sending email...")
                success = self.send_email(html_content)
                
                if success:
                    logger.info("🎉 Email sent successfully via GitHub Actions!")
                else:
                    logger.error("💥 Failed to send email")
                    
                    # Fallback: Save as artifact
                    self.save_to_html_file(html_content)
                    
            else:
                # Locally: Save to file
                logger.info("💻 Running locally - Saving to HTML file...")
                filepath = self.save_to_html_file(html_content)
                
                if filepath:
                    logger.info(f"🎉 Local run successful! File saved: {filepath}")
                    
                    # Show summary in terminal
                    print("\n" + "="*60)
                    print("📊 TODAY'S TOP STORIES:")
                    print("="*60)
                    for i, article in enumerate(articles[:5], 1):
                        print(f"{i}. {article['title']}")
                        print(f"   📍 Source: {article['source']}")
                        print(f"   🔗 Link: {article['link'][:80]}...")
                        print()
                
                # Also try to send email locally (might fail due to firewall)
                logger.info("🔄 Attempting local email send (may fail due to firewall)...")
                if self.sender_email and self.sender_password:
                    self.send_email(html_content)
            
            logger.info("=" * 60)
            logger.info("🏁 PROCESS COMPLETED")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"💥 Error in main process: {e}")
            raise

def main():
    """Run the automation"""
    automation = TechNewsAutomation()
    automation.run()

if __name__ == "__main__":
    main()
