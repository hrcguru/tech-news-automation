"""
India News Digest - Professional Edition
Curated News Aggregator for UPSC & Competitive Exams
"""

import feedparser
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dotenv import load_dotenv
import webbrowser
import hashlib
import re
from collections import defaultdict

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IndiaNewsDigest:
    def __init__(self):
        # Check if running on GitHub Actions
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        # Email configuration
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.receiver_email = os.getenv('RECEIVER_EMAIL', self.sender_email)
        
        # News sources with priority and categories
        self.news_sources = {
            # High Priority - Government & National (Priority 1)
            'Government Portal': {
                'url': 'https://pib.gov.in/rssfeed.aspx',
                'category': 'national',
                'priority': 1
            },
            'National News Agency': {
                'url': 'https://www.aninews.in/rss/',
                'category': 'national',
                'priority': 1
            },
            'Press Trust of India': {
                'url': 'https://www.ptinews.com/rss',
                'category': 'national',
                'priority': 1
            },
            
            # International Coverage (Priority 2)
            'International Relations': {
                'url': 'https://www.mea.gov.in/rss-feed.htm',
                'category': 'international',
                'priority': 2
            },
            'Defence Updates': {
                'url': 'https://pib.gov.in/defence.aspx',
                'category': 'defence',
                'priority': 2
            },
            
            # Competitive Exam Focus (Priority 3)
            'Economic Survey': {
                'url': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
                'category': 'economy',
                'priority': 3
            },
            'Science & Tech': {
                'url': 'https://www.isro.gov.in/rss.xml',
                'category': 'science',
                'priority': 3
            },
            'Environment & Ecology': {
                'url': 'https://www.downtoearth.org.in/rss',
                'category': 'environment',
                'priority': 3
            },
            
            # International Perspectives (Priority 4)
            'Global Affairs': {
                'url': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
                'category': 'international',
                'priority': 4
            },
            'Strategic Analysis': {
                'url': 'https://thewire.in/feed',
                'category': 'analysis',
                'priority': 4
            },
            
            # Regional & Social Issues (Priority 5)
            'Social Justice': {
                'url': 'https://www.thehindu.com/feeder/default.rss',
                'category': 'social',
                'priority': 5
            },
            'Culture & Heritage': {
                'url': 'https://asi.nic.in/rss.xml',
                'category': 'culture',
                'priority': 5
            },
            
            # Policy & Governance (Priority 6)
            'Policy Watch': {
                'url': 'https://prsindia.org/theprsblog/feed',
                'category': 'policy',
                'priority': 6
            },
            'Legal Updates': {
                'url': 'https://main.sci.gov.in/rss.xml',
                'category': 'legal',
                'priority': 6
            }
        }
        
        # Keywords for relevance scoring (Competitive Exam Focus)
        self.relevance_keywords = {
            'high': [
                # Governance & Polity
                'Constitution', 'Parliament', 'Supreme Court', 'Judiciary',
                'Federalism', 'Governance', 'Public Policy', 'Administration',
                'Election Commission', 'Right to Information', 'Lokpal',
                
                # Economy & Development
                'GDP', 'Inflation', 'Fiscal Policy', 'Monetary Policy',
                'Economic Survey', 'Union Budget', 'NITI Aayog', 'Planning',
                'Sustainable Development', 'Poverty', 'Unemployment',
                
                # International Relations
                'Foreign Policy', 'Diplomacy', 'UN', 'WTO', 'IMF', 'World Bank',
                'Bilateral Relations', 'Multilateral Forum', 'Strategic Partnership',
                'Geopolitics', 'Security Council', 'Climate Change',
                
                # Social Issues
                'Education', 'Health', 'Gender', 'Minority', 'Caste',
                'Tribal Rights', 'Social Justice', 'Welfare Schemes',
                'Human Rights', 'Democracy', 'Secularism',
                
                # Science & Tech
                'Space Technology', 'Nuclear Energy', 'Renewable Energy',
                'Artificial Intelligence', 'Cyber Security', 'Digital India',
                'Innovation', 'Research & Development', 'Biotechnology',
                
                # Environment
                'Climate Change', 'Biodiversity', 'Conservation',
                'Pollution', 'Sustainable Development', 'Wildlife',
                'Forest Rights', 'Environmental Impact',
                
                # History & Culture
                'Indian Culture', 'Heritage', 'Art & Architecture',
                'Freedom Struggle', 'Modern History', 'Ancient Civilizations',
                'Philosophy', 'Religion', 'Social Reformers'
            ],
            'medium': [
                'Government Scheme', 'Policy Change', 'Law Amendment',
                'International Treaty', 'Trade Agreement', 'Defence Deal',
                'Scientific Discovery', 'Technological Breakthrough',
                'Social Movement', 'Judgment', 'Report Release',
                'Statistical Data', 'Survey Results', 'Committee Report'
            ]
        }
        
        # Track seen articles to avoid duplicates
        self.seen_articles = set()
        
        logger.info(f"Initializing News Digest in {'GitHub Actions' if self.is_github_actions else 'Local'} mode")
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def generate_article_id(self, article):
        """Generate unique ID for article to detect duplicates"""
        content = f"{article['title']}_{article['source']}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_recent(self, date_string):
        """Check if article is from last 24 hours"""
        try:
            # Try various date formats
            date_formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S',
                '%d %b %Y',
                '%b %d, %Y'
            ]
            
            publish_date = None
            for fmt in date_formats:
                try:
                    publish_date = datetime.strptime(date_string, fmt)
                    break
                except:
                    continue
            
            if not publish_date:
                # If date parsing fails, check if it contains today/yesterday
                date_lower = date_string.lower()
                today_words = ['today', 'just now', 'hours ago', 'minutes ago']
                if any(word in date_lower for word in today_words):
                    return True
                return False
            
            # Check if within 24 hours
            time_diff = datetime.now(publish_date.tzinfo) - publish_date if publish_date.tzinfo else datetime.now() - publish_date
            return time_diff.days == 0 and time_diff.seconds < 86400
            
        except Exception as e:
            logger.warning(f"Date parsing error for '{date_string}': {e}")
            return True  # Assume recent if can't parse
    
    def calculate_relevance_score(self, title, summary):
        """Calculate relevance score for competitive exams"""
        score = 0
        content = f"{title} {summary}".lower()
        
        # High priority keywords
        for keyword in self.relevance_keywords['high']:
            if keyword.lower() in content:
                score += 3
        
        # Medium priority keywords
        for keyword in self.relevance_keywords['medium']:
            if keyword.lower() in content:
                score += 1
        
        # Boost for government sources
        if 'pib' in content or 'government' in content or 'ministry' in content:
            score += 2
        
        # Boost for international relations
        international_terms = ['united nations', 'diplomacy', 'bilateral', 'multilateral', 'foreign minister']
        if any(term in content for term in international_terms):
            score += 2
        
        return score
    
    def fetch_all_news(self):
        """Fetch and filter news from all sources"""
        all_articles = []
        
        for source_name, source_info in self.news_sources.items():
            try:
                logger.info(f"Fetching from {source_name}")
                feed = feedparser.parse(source_info['url'])
                
                for entry in feed.entries[:15]:  # Get more entries to filter
                    # Skip if not recent
                    if not self.is_recent(entry.get('published', '')):
                        continue
                    
                    # Clean data
                    title = self.clean_text(entry.title)[:120]
                    summary = self.clean_text(entry.get('summary', ''))[:200]
                    
                    # Skip if essential data missing
                    if not title or not entry.link:
                        continue
                    
                    # Create article object
                    article = {
                        'id': self.generate_article_id({'title': title, 'source': source_name}),
                        'source': source_name,
                        'category': source_info['category'],
                        'priority': source_info['priority'],
                        'title': title,
                        'link': entry.link,
                        'published': entry.get('published', 'Today'),
                        'summary': summary,
                        'relevance_score': self.calculate_relevance_score(title, summary)
                    }
                    
                    # Skip duplicates
                    if article['id'] in self.seen_articles:
                        continue
                    
                    self.seen_articles.add(article['id'])
                    all_articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error with {source_name}: {e}")
                continue
        
        # Sort by priority, then relevance, then recency
        all_articles.sort(key=lambda x: (
            x['priority'],
            x['relevance_score'],
            -1 if 'today' in x['published'].lower() else 0
        ), reverse=True)
        
        # Limit to best 25 articles
        return all_articles[:25]
    
    def create_html_content(self, articles):
        """Create professional HTML digest"""
        
        # Group by category
        categorized = defaultdict(list)
        for article in articles:
            categorized[article['category']].append(article)
        
        # Category display names
        category_names = {
            'national': 'National Affairs',
            'international': 'Global Perspective',
            'economy': 'Economic Insights',
            'science': 'Science & Innovation',
            'environment': 'Ecology & Environment',
            'defence': 'Defence & Security',
            'social': 'Social Issues',
            'culture': 'Culture & Heritage',
            'policy': 'Policy Analysis',
            'legal': 'Legal Updates',
            'analysis': 'Strategic Analysis'
        }
        
        # Calculate stats
        today = datetime.now().strftime('%B %d, %Y')
        high_relevance = sum(1 for a in articles if a['relevance_score'] >= 3)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Digest | {today}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #F6D6D6 0%, #F6F7C4 25%, #A1EEBD 50%, #7BD3EA 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        
        .header {{
            background: linear-gradient(135deg, #7BD3EA 0%, #A1EEBD 100%);
            padding: 40px 30px;
            text-align: center;
            border-bottom: 3px solid #F6D6D6;
        }}
        
        .header h1 {{
            font-size: 2.8rem;
            color: #2c3e50;
            margin-bottom: 10px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        .header .date {{
            font-size: 1.1rem;
            color: #34495e;
            font-style: italic;
            margin-bottom: 20px;
        }}
        
        .header .tagline {{
            font-size: 1rem;
            color: #7f8c8d;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.5;
        }}
        
        .stats-bar {{
            background: #F6F7C4;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            border-bottom: 2px dashed #F6D6D6;
            font-size: 0.9rem;
        }}
        
        .stat-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .stat-badge {{
            background: #2c3e50;
            color: #F6F7C4;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 600;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .category-section {{
            margin-bottom: 40px;
            background: #fff;
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #7BD3EA;
            transition: transform 0.3s ease;
        }}
        
        .category-section:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
        }}
        
        .category-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #A1EEBD;
        }}
        
        .category-icon {{
            width: 40px;
            height: 40px;
            background: #F6D6D6;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }}
        
        .category-title {{
            font-size: 1.5rem;
            color: #2c3e50;
            font-weight: 600;
        }}
        
        .article {{
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 1px solid #e9ecef;
            transition: all 0.3s ease;
        }}
        
        .article:hover {{
            background: #fff;
            border-color: #7BD3EA;
            box-shadow: 0 4px 15px rgba(123, 211, 234, 0.2);
        }}
        
        .article-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }}
        
        .article-title {{
            font-size: 1.2rem;
            color: #2c3e50;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        
        .article-title a {{
            color: inherit;
            text-decoration: none;
            transition: color 0.3s;
        }}
        
        .article-title a:hover {{
            color: #7BD3EA;
        }}
        
        .relevance-badge {{
            background: #A1EEBD;
            color: #2c3e50;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            white-space: nowrap;
            margin-left: 10px;
        }}
        
        .article-meta {{
            display: flex;
            gap: 15px;
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        
        .source-tag {{
            background: #F6F7C4;
            padding: 3px 10px;
            border-radius: 15px;
            font-weight: 600;
        }}
        
        .article-summary {{
            color: #34495e;
            line-height: 1.7;
            margin-bottom: 15px;
            font-size: 0.95rem;
        }}
        
        .read-more {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: #7BD3EA;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            transition: gap 0.3s;
        }}
        
        .read-more:hover {{
            gap: 12px;
        }}
        
        .priority-indicator {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .priority-1 {{ background: #e74c3c; }}
        .priority-2 {{ background: #f39c12; }}
        .priority-3 {{ background: #2ecc71; }}
        .priority-4 {{ background: #3498db; }}
        
        .footer {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 30px;
            text-align: center;
            border-top: 3px solid #F6D6D6;
        }}
        
        .footer-content {{
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .footer h3 {{
            font-size: 1.2rem;
            margin-bottom: 15px;
            color: #A1EEBD;
        }}
        
        .footer p {{
            font-size: 0.9rem;
            line-height: 1.6;
            margin-bottom: 10px;
            color: #bdc3c7;
        }}
        
        .update-time {{
            font-size: 0.8rem;
            color: #95a5a6;
            margin-top: 20px;
            font-style: italic;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                border-radius: 15px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .stats-bar {{
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }}
            
            .article-header {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .relevance-badge {{
                align-self: flex-start;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .category-section {{
                padding: 20px;
            }}
        }}
        
        @media print {{
            body {{
                background: white !important;
            }}
            
            .container {{
                box-shadow: none;
                border: 1px solid #ddd;
            }}
            
            .read-more {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Daily Digest</h1>
            <div class="date">{today}</div>
            <div class="tagline">
                Curated analysis of significant developments with strategic relevance
            </div>
        </div>
        
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-badge">{len(articles)}</span>
                <span>Stories Analyzed</span>
            </div>
            <div class="stat-item">
                <span class="stat-badge">{high_relevance}</span>
                <span>High Relevance</span>
            </div>
            <div class="stat-item">
                <span class="stat-badge">{len(categorized)}</span>
                <span>Categories</span>
            </div>
        </div>
        
        <div class="content">
"""
        
        # Add categorized content
        for category, cat_articles in categorized.items():
            display_name = category_names.get(category, category.title())
            
            html += f"""
            <div class="category-section">
                <div class="category-header">
                    <div class="category-icon">
                        {self.get_category_icon(category)}
                    </div>
                    <h2 class="category-title">{display_name}</h2>
                </div>
            """
            
            for article in cat_articles[:4]:  # Max 4 per category
                relevance_text = "High Relevance" if article['relevance_score'] >= 3 else "Moderate Relevance"
                
                html += f"""
                <div class="article">
                    <div class="article-header">
                        <h3 class="article-title">
                            <span class="priority-indicator priority-{article['priority']}"></span>
                            <a href="{article['link']}" target="_blank">{article['title']}</a>
                        </h3>
                        <span class="relevance-badge">{relevance_text}</span>
                    </div>
                    
                    <div class="article-meta">
                        <span class="source-tag">{article['source']}</span>
                        <span>•</span>
                        <span>{article['published']}</span>
                    </div>
                    
                    <div class="article-summary">
                        {article['summary']}
                    </div>
                    
                    <a href="{article['link']}" class="read-more" target="_blank">
                        Read Full Analysis →
                    </a>
                </div>
                """
            
            html += "</div>"
        
        # Footer
        html += f"""
        </div>
        
        <div class="footer">
            <div class="footer-content">
                <h3>About This Digest</h3>
                <p>
                    This digest provides carefully selected news with emphasis on developments 
                    that have broader implications for governance, policy, and international relations. 
                    Sources are chosen for their reliability and analytical depth.
                </p>
                <p>
                    Updates are compiled daily with a focus on substantive reporting over 
                    sensationalism. All links direct to original sources for comprehensive reading.
                </p>
                <div class="update-time">
                    Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def get_category_icon(self, category):
        """Get icon for category"""
        icons = {
            'national': '🏛️',
            'international': '🌐',
            'economy': '📈',
            'science': '🔬',
            'environment': '🌿',
            'defence': '🛡️',
            'social': '👥',
            'culture': '🎨',
            'policy': '📋',
            'legal': '⚖️',
            'analysis': '📊'
        }
        return icons.get(category, '📰')
    
    def send_email(self, html_content):
        """Send professional email"""
        if not all([self.sender_email, self.sender_password]):
            logger.error("Email credentials missing")
            return False
        
        # Get recipients
        receiver_email = self.receiver_email
        additional_emails_str = os.getenv('ADDITIONAL_EMAILS', '')
        
        additional_emails = []
        if additional_emails_str:
            additional_emails = [email.strip() for email in additional_emails_str.split(',') if email.strip()]
        
        all_recipients = list(set([receiver_email] + additional_emails))
        
        if not all_recipients:
            logger.error("No recipient emails found")
            return False
        
        logger.info(f"Preparing email for {len(all_recipients)} recipients")
        
        try:
            msg = MIMEMultipart('alternative')
            today = datetime.now().strftime('%b %d')
            msg['Subject'] = f"Daily Digest | {today}"
            msg['From'] = f"News Digest <{self.sender_email}>"
            msg['To'] = receiver_email
            
            if len(all_recipients) > 1:
                bcc_recipients = all_recipients[1:]
                msg['Bcc'] = ', '.join(bcc_recipients)
                logger.info(f"BCC: {len(bcc_recipients)} recipients")
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send with retry logic
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            except:
                with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def save_to_html_file(self, html_content):
        """Save digest to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"Daily_Digest_{timestamp}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            filepath = os.path.abspath(filename)
            logger.info(f"Saved to: {filepath}")
            
            # Try to open in browser
            try:
                webbrowser.open(f'file://{filepath}')
                logger.info("Opened in browser")
            except:
                pass
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return None
    
    def run(self):
        """Main execution flow"""
        logger.info("=" * 60)
        logger.info("Starting Daily Digest Generation")
        logger.info("=" * 60)
        
        try:
            # Fetch and filter news
            logger.info("Fetching latest news...")
            articles = self.fetch_all_news()
            
            if not articles:
                logger.warning("No recent articles found")
                return
            
            logger.info(f"Found {len(articles)} relevant articles")
            
            # Create content
            logger.info("Creating digest...")
            html_content = self.create_html_content(articles)
            
            # Output based on mode
            if self.is_github_actions:
                logger.info("Running on GitHub Actions - Sending email...")
                if self.send_email(html_content):
                    logger.info("Digest sent successfully")
                else:
                    logger.error("Email failed, saving locally")
                    self.save_to_html_file(html_content)
            else:
                logger.info("Running locally - Saving to file...")
                filepath = self.save_to_html_file(html_content)
                
                if filepath:
                    logger.info(f"Digest saved: {filepath}")
                    
                    # Terminal summary
                    print("\n" + "="*60)
                    print("DAILY DIGEST SUMMARY")
                    print("="*60)
                    
                    # Group by relevance
                    high_rel = [a for a in articles if a['relevance_score'] >= 3]
                    mod_rel = [a for a in articles if a['relevance_score'] < 3]
                    
                    print(f"\n📊 Statistics:")
                    print(f"   • Total Articles: {len(articles)}")
                    print(f"   • High Relevance: {len(high_rel)}")
                    print(f"   • Categories: {len(set(a['category'] for a in articles))}")
                    
                    print(f"\n⭐ Top High-Relevance Stories:")
                    for i, article in enumerate(high_rel[:3], 1):
                        print(f"   {i}. {article['title']}")
                        print(f"      📍 {article['source']}")
                    
                    print(f"\n📁 File saved: {filepath}")
                    print("="*60)
                
                # Attempt email if credentials available
                if self.sender_email and self.sender_password:
                    logger.info("Attempting to send email...")
                    self.send_email(html_content)
            
            logger.info("=" * 60)
            logger.info("Process Completed Successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error in main process: {e}")
            import traceback
            traceback.print_exc()
            raise

def main():
    """Entry point"""
    digest = IndiaNewsDigest()
    digest.run()

if __name__ == "__main__":
    main()
