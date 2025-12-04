"""
India News Automation - Dual Mode (Local HTML / GitHub Email)
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

class IndiaNewsAutomation:
    def __init__(self):
        # Check if running on GitHub Actions
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        # Email configuration
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.receiver_email = os.getenv('RECEIVER_EMAIL', self.sender_email)
        
        # Indian Government Approved News Sources
        self.news_sources = {
            # Official Government News Portals
            '🇮🇳 PIB (Press Information Bureau)': 'https://pib.gov.in/rssfeed.aspx',
            '🏛️ DD News': 'https://www.ddnews.gov.in/rss.xml',
            '📻 All India Radio': 'https://www.newsonair.gov.in/rss-feed',
            
            # National News Agencies
            '📰 PTI (Press Trust of India)': 'https://www.ptinews.com/rss',
            '🔄 UNI (United News of India)': 'https://www.uniindia.com/rssfeed',
            '🏆 ANI (Asian News International)': 'https://www.aninews.in/rss/',
            
            # Mainstream National Newspapers (Govt approved/recognized)
            '📚 The Hindu': 'https://www.thehindu.com/feeder/default.rss',
            '📰 Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
            '🗞️ Hindustan Times': 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',
            '📊 Indian Express': 'https://indianexpress.com/feed/',
            '🌅 The Tribune': 'https://www.tribuneindia.com/rss/feed',
            '📡 Deccan Herald': 'https://www.deccanherald.com/rss.php',
            
            # Business & Economy
            '💼 Business Standard': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
            '📈 Economic Times': 'https://economictimes.indiatimes.com/rssfeedsdefault.cms',
            '💰 Mint': 'https://www.livemint.com/rss/news',
            '🏦 Business Today': 'https://www.businesstoday.in/rssfeeds',
            
            # Science & Technology (Indian Focus)
            '🔬 CSIR News': 'https://www.csir.res.in/rss.xml',
            '🚀 ISRO News': 'https://www.isro.gov.in/rss.xml',
            '💡 DST (Dept of Science & Tech)': 'https://dst.gov.in/rss.xml',
            '🧪 NITI Aayog': 'https://www.niti.gov.in/rss.xml',
            '🏥 ICMR (Indian Council of Medical Research)': 'https://main.icmr.nic.in/rss.xml',
            
            # International Relations & Defence
            '🌐 Ministry of External Affairs': 'https://www.mea.gov.in/rss-feed.htm',
            '🛡️ Ministry of Defence': 'https://pib.gov.in/defence.aspx',
            '⚓ Indian Navy': 'https://www.indiannavy.nic.in/rss.xml',
            '✈️ Indian Air Force': 'https://indianairforce.nic.in/rss.xml',
            
            # Regional News (Major Languages)
            '🎭 Eenadu (Telugu)': 'https://www.eenadu.net/rss/rssfeed.xml',
            '🌸 Malayala Manorama': 'https://www.manoramaonline.com/rss/rssFeed.xml',
            '🌺 Daily Thanthi (Tamil)': 'https://www.dailythanthi.com/rssfeeds',
            '🌼 Anandabazar Patrika (Bengali)': 'https://www.anandabazar.com/rss',
            '🌻 Dainik Bhaskar (Hindi)': 'https://www.bhaskar.com/rss-feed/',
            '🌾 Dainik Jagran (Hindi)': 'https://www.jagran.com/rss',
            
            # Educational & Research
            '🎓 UGC News': 'https://www.ugc.gov.in/rss.xml',
            '📚 NCERT': 'https://ncert.nic.in/rss.xml',
            '🔍 ICSSR': 'https://icssr.org/rss.xml',
            
            # Cultural & Historical
            '🏛️ Archaeological Survey of India': 'https://asi.nic.in/rss.xml',
            '🎨 Ministry of Culture': 'https://www.indiaculture.nic.in/rss.xml',
            '📜 National Archives': 'https://nationalarchives.nic.in/rss.xml',
            
            # State Government News
            '🏙️ Delhi Govt News': 'https://delhi.gov.in/rss.xml',
            '🌊 Tamil Nadu Govt': 'https://www.tn.gov.in/rss.xml',
            '⛰️ Karnataka Govt': 'https://www.karnataka.gov.in/rss.xml',
            '🌄 Maharashtra Govt': 'https://www.maharashtra.gov.in/rss.xml',
            
            # Policy & Governance
            '📋 PRS Legislative Research': 'https://prsindia.org/theprsblog/feed',
            '⚖️ Supreme Court of India': 'https://main.sci.gov.in/rss.xml',
            '🏛️ Parliament of India': 'https://parliamentofindia.nic.in/rss.xml'
        }
        
        # Keywords for categorization
        self.keywords = {
            'international_relations': [
                'MEA', 'External Affairs', 'Diplomacy', 'Bilateral', 'Multilateral',
                'UN', 'United Nations', 'SAARC', 'BRICS', 'G20', 'QUAD',
                'Foreign Policy', 'Embassy', 'Consulate', 'Visa', 'Passport',
                'Trade Agreement', 'Defence Cooperation', 'Strategic Partnership'
            ],
            'economy': [
                'GDP', 'Inflation', 'RBI', 'Repo Rate', 'CRR', 'SLR',
                'Fiscal Deficit', 'Current Account', 'Trade Deficit',
                'Stock Market', 'Sensex', 'Nifty', 'BSE', 'NSE',
                'GST', 'Direct Tax', 'Indirect Tax', 'Budget', 'Union Budget',
                'FDI', 'Foreign Investment', 'Export', 'Import', 'Trade'
            ],
            'national_news': [
                'Prime Minister', 'President', 'Cabinet', 'Ministry',
                'Parliament', 'Lok Sabha', 'Rajya Sabha', 'Session',
                'Election', 'Voting', 'ECI', 'Election Commission',
                'State Government', 'Governor', 'Chief Minister',
                'Police', 'Law and Order', 'Security', 'Internal Security'
            ],
            'science_tech': [
                'ISRO', 'Space', 'Satellite', 'Rocket', 'Launch',
                'CSIR', 'Research', 'Innovation', 'Technology',
                'Startup', 'Digital India', 'Make in India',
                'AI', 'Artificial Intelligence', 'Machine Learning',
                'Renewable Energy', 'Solar', 'Wind', 'Nuclear'
            ],
            'history': [
                'Archaeology', 'Heritage', 'Monument', 'ASI',
                'Ancient', 'Medieval', 'Modern History',
                'Independence', 'Freedom Struggle', 'Gandhi',
                'Culture', 'Tradition', 'Festival', 'Art', 'Music'
            ],
            'political_news': [
                'Political Party', 'BJP', 'Congress', 'AAP', 'TMC', 'DMK',
                'Alliance', 'Coalition', 'Opposition', 'Ruling',
                'Election Campaign', 'Rally', 'Manifesto',
                'Bill', 'Act', 'Ordinance', 'Legislation',
                'Vote', 'MP', 'MLA', 'Council', 'Assembly'
            ]
        }
        
        logger.info(f"Running in {'GitHub Actions' if self.is_github_actions else 'Local'} mode")
    
    def fetch_all_news(self):
        """Get news from all Indian government-approved sources"""
        all_articles = []
        
        for source_name, feed_url in self.news_sources.items():
            try:
                logger.info(f"Fetching from {source_name}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # Get top 10 from each source
                    # Combine title and summary for categorization
                    content = entry.title + ' ' + entry.get('summary', '')
                    
                    article = {
                        'source': source_name,
                        'title': entry.title[:150],
                        'link': entry.link,
                        'published': entry.get('published', 'Recent'),
                        'summary': entry.get('summary', 'No summary available')[:250],
                        'categories': self.categorize_article(content)
                    }
                    
                    all_articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error with {source_name}: {e}")
        
        # Sort by number of categories (more relevant articles have more categories)
        all_articles.sort(key=lambda x: len(x['categories']), reverse=True)
        
        return all_articles[:40]  # Return top 40 articles
    
    def categorize_article(self, text):
        """Categorize article based on keywords"""
        categories = []
        text_lower = text.lower()
        
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if category not in categories:
                        categories.append(category)
                    break  # Found one keyword from this category, move to next
        
        return categories
    
    def create_html_content(self, articles):
        """Create beautiful HTML content for email or file"""
        
        # Count articles by category
        category_count = {}
        for article in articles:
            for category in article['categories']:
                category_count[category] = category_count.get(category, 0) + 1
        
        # Count articles per source
        source_count = {}
        for article in articles:
            source = article['source']
            source_count[source] = source_count.get(source, 0) + 1
        
        category_summary = " | ".join([f"{cat}: {count}" for cat, count in category_count.items()])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>India News Digest - {datetime.now().strftime('%B %d, %Y')}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                }}
                .email-container {{
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    border: 1px solid #e0e0e0;
                }}
                .header {{
                    background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
                    color: #333;
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 30px;
                    border: 2px solid #000080;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 32px;
                    color: #000080;
                    font-weight: bold;
                }}
                .header .date {{
                    color: #666;
                    font-size: 16px;
                    margin-top: 10px;
                    font-weight: 500;
                }}
                .stats {{
                    background: #e8f4fd;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                    font-size: 15px;
                    color: #2c5282;
                    border-left: 5px solid #000080;
                }}
                .category-badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: bold;
                    margin-right: 8px;
                    margin-bottom: 5px;
                }}
                .international {{ background: #4CAF50; color: white; }}
                .economy {{ background: #2196F3; color: white; }}
                .national {{ background: #F44336; color: white; }}
                .science {{ background: #9C27B0; color: white; }}
                .history {{ background: #FF9800; color: white; }}
                .political {{ background: #795548; color: white; }}
                
                .article {{
                    border-left: 5px solid #000080;
                    padding: 20px;
                    margin-bottom: 25px;
                    background: #f8fafc;
                    border-radius: 0 8px 8px 0;
                    transition: transform 0.2s;
                }}
                .article:hover {{
                    transform: translateX(5px);
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }}
                .article-title {{
                    margin: 0 0 12px 0;
                }}
                .article-title a {{
                    color: #1a237e;
                    text-decoration: none;
                    font-size: 20px;
                    font-weight: 600;
                }}
                .article-title a:hover {{
                    color: #FF9933;
                    text-decoration: underline;
                }}
                .meta {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 10px;
                }}
                .source {{
                    background: #000080;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 15px;
                    font-size: 13px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .summary {{
                    font-size: 15px;
                    color: #444;
                    line-height: 1.6;
                    margin: 10px 0;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 2px dashed #ddd;
                    text-align: center;
                    color: #666;
                    font-size: 13px;
                }}
                .category-section {{
                    margin: 30px 0;
                    padding: 15px;
                    background: #f0f8ff;
                    border-radius: 8px;
                }}
                .category-section h3 {{
                    color: #000080;
                    border-bottom: 2px solid #FF9933;
                    padding-bottom: 8px;
                }}
                @media (max-width: 600px) {{
                    body {{
                        padding: 10px;
                    }}
                    .email-container {{
                        padding: 15px;
                    }}
                    .article-title a {{
                        font-size: 18px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>🇮🇳 India News Digest</h1>
                    <div class="date">{datetime.now().strftime("%A, %B %d, %Y")}</div>
                    <div style="margin-top: 10px; font-size: 14px; color: #555;">
                        Curated from Government Approved Sources
                    </div>
                </div>
                
                <div class="stats">
                    <strong>📊 Today's Summary:</strong> {len(articles)} articles from {len(source_count)} sources<br>
                    <strong>📌 Categories:</strong> {category_summary}<br>
                    <strong>🏛️ Sources Active:</strong> {len(source_count)} government-approved portals
                </div>
                
                <h2 style="color: #000080; border-bottom: 3px solid #FF9933; padding-bottom: 10px;">
                    📰 Top Stories Across Categories
                </h2>
        """
        
        # Group articles by category for better organization
        categorized_articles = {}
        for article in articles:
            for category in article['categories']:
                if category not in categorized_articles:
                    categorized_articles[category] = []
                categorized_articles[category].append(article)
        
        # Display articles category-wise
        category_display_names = {
            'international_relations': '🌐 International Relations',
            'economy': '💰 Economy & Business',
            'national_news': '🏛️ National News',
            'science_tech': '🔬 Science & Technology',
            'history': '📜 History & Culture',
            'political_news': '⚖️ Political News'
        }
        
        for category_id in self.keywords.keys():
            if category_id in categorized_articles:
                category_name = category_display_names.get(category_id, category_id.replace('_', ' ').title())
                html += f"""
                <div class="category-section">
                    <h3>{category_name}</h3>
                """
                
                for article in categorized_articles[category_id][:5]:  # Top 5 per category
                    # Create category badges
                    badges_html = ""
                    for cat in article['categories']:
                        display_name = cat.replace('_', ' ')
                        badges_html += f'<span class="category-badge {cat}">{display_name.title()}</span>'
                    
                    html += f"""
                    <div class="article">
                        <h3 class="article-title">
                            <a href="{article['link']}" target="_blank">{article['title']}</a>
                        </h3>
                        <div class="meta">
                            <span class="source">{article['source']}</span>
                            📅 {article['published']}
                        </div>
                        <div>
                            {badges_html}
                        </div>
                        <div class="summary">
                            {article['summary']}...
                            <a href="{article['link']}" style="color: #138808; font-weight: bold; font-size: 13px;">[Read Full Story]</a>
                        </div>
                    </div>
                    """
                
                html += "</div>"
        
        # Add footer with disclaimer
        html += f"""
                <div class="footer">
                    <p><strong>Disclaimer:</strong> This digest aggregates news only from Indian government-approved and recognized sources.</p>
                    <p>All content is sourced from official government portals, PIB, and mainstream recognized media houses.</p>
                    <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST</p>
                    <p style="color: #000080; font-weight: bold; margin-top: 15px;">
                        जय हिन्द! 🇮🇳
                    </p>
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
            msg['Subject'] = f"🇮🇳 India News Digest - {datetime.now().strftime('%b %d, %Y')}"
            msg['From'] = f"India News Digest <{self.sender_email}>"
            
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
            filename = f"India_News_Digest_{timestamp}.html"
            
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
        logger.info("🚀 STARTING INDIA NEWS AUTOMATION")
        logger.info("=" * 60)
        
        try:
            # Step 1: Fetch news
            logger.info("📥 Fetching latest India news from government sources...")
            articles = self.fetch_all_news()
            
            if not articles:
                logger.warning("No articles found!")
                return
            
            logger.info(f"✅ Found {len(articles)} articles from Indian sources")
            
            # Step 2: Create HTML content
            logger.info("📧 Creating digest content...")
            html_content = self.create_html_content(articles)
            
            # Step 3: Send email or save file based on mode
            if self.is_github_actions:
                # On GitHub Actions: Send email
                logger.info("🚀 Running on GitHub Actions - Sending email...")
                success = self.send_email(html_content)
                
                if success:
                    logger.info("🎉 India News Digest sent successfully via GitHub Actions!")
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
                    print("📊 TODAY'S TOP INDIA NEWS:")
                    print("="*60)
                    for i, article in enumerate(articles[:5], 1):
                        print(f"{i}. {article['title']}")
                        print(f"   📍 Source: {article['source']}")
                        categories = ", ".join(article['categories'])
                        if categories:
                            print(f"   🏷️  Categories: {categories}")
                        print()
                
                # Also try to send email locally
                logger.info("🔄 Attempting local email send...")
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
    automation = IndiaNewsAutomation()
    automation.run()

if __name__ == "__main__":
    main()
