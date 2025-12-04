"""
INDIA NEWS DIGEST - UPSC Focused News Aggregator
Enhanced with duplicate removal, freshness filter, and UPSC relevance
"""

import feedparser
import requests
import smtplib
import os
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from dotenv import load_dotenv
import webbrowser
import re
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_digest.log'),
        logging.StreamHandler()
    ]
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
        
        # Cache for duplicate detection
        self.seen_articles = set()
        self.load_cache()
        
        # News freshness threshold (24 hours)
        self.max_age_hours = 24
        
        # Optimized Indian Government Approved News Sources (Verified working RSS)
        self.news_sources = {
            # Official Government Portals
            '🇮🇳 PIB (Press Information Bureau)': 'https://www.pib.gov.in/rss.aspx',
            '🏛️ DD News': 'https://www.ddnews.gov.in/rss.xml',
            '📻 AIR News': 'https://newsonair.gov.in/Home/rssfeed',
            
            # National News Agencies
            '📰 PTI News': 'https://www.ptinews.com/pti.rss',
            '🏆 ANI News': 'https://aninews.in/rss/feed/',
            
            # Mainstream National Newspapers
            '📚 The Hindu': 'https://www.thehindu.com/news/national/feeder/default.rss',
            '📰 Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
            '🗞️ Hindustan Times': 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',
            '📊 Indian Express': 'https://indianexpress.com/feed/',
            '🌅 The Tribune': 'https://www.tribuneindia.com/rssfeeds',
            
            # Business & Economy
            '💼 Business Standard': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
            '📈 Economic Times': 'https://economictimes.indiatimes.com/rssfeedsdefault.cms',
            '💰 Mint': 'https://www.livemint.com/rss/news',
            
            # Science & Technology
            '🚀 ISRO News': 'https://www.isro.gov.in/feed',
            '🔬 CSIR News': 'https://www.csir.res.in/rss.xml',
            
            # International Relations
            '🌐 MEA India': 'https://www.mea.gov.in/rss-feed.htm',
            
            # UPSC Specific Sources
            '🎓 PRS India': 'https://prsindia.org/theprsblog/feed',
            '📋 Insights IAS': 'https://www.insightsonindia.com/feed/',
            '📘 ClearIAS': 'https://www.clearias.com/feed/',
            '📖 Drishti IAS': 'https://www.drishtiias.com/rss-feed',
            '🎯 Vision IAS': 'https://visionias.in/blog/feed',
        }
        
        # UPSC Focused Keywords with weights
        self.upsc_keywords = {
            'high': [  # Weight: 5 points
                'UPSC', 'Civil Services', 'IAS', 'IPS', 'IFS', 'Prelims', 'Mains', 
                'GS Paper', 'Current Affairs', 'Government Scheme', 'Policy', 'Act',
                'Amendment', 'Bill', 'Ordinance', 'Parliament', 'Constitution',
                'Supreme Court', 'Judgment', 'Landmark Case'
            ],
            'medium': [  # Weight: 3 points
                'Economy', 'GDP', 'Inflation', 'Fiscal', 'Monetary', 'RBI', 'Budget',
                'Agriculture', 'Farmers', 'Rural', 'Employment', 'Skill Development',
                'Education', 'Health', 'Healthcare', 'Infrastructure', 'Transport',
                'Environment', 'Climate', 'Pollution', 'Sustainable', 'Renewable',
                'Technology', 'Digital', 'AI', 'Startup', 'Innovation', 'Science',
                'Research', 'Space', 'Defence', 'Security', 'International', 'Diplomacy'
            ],
            'low': [  # Weight: 1 point
                'State', 'Regional', 'Development', 'Social', 'Welfare', 'Women',
                'Children', 'Senior Citizens', 'Minorities', 'Tribal', 'SC/ST',
                'Urban', 'Smart City', 'Tourism', 'Culture', 'Heritage', 'History',
                'Geography', 'Disaster', 'Management', 'Governance', 'Transparency'
            ]
        }
        
        # UPSC Subjects Mapping
        self.upsc_subjects = {
            'polity': ['Constitution', 'Parliament', 'President', 'Governor', 'Judiciary', 
                      'Fundamental Rights', 'Directive Principles', 'Amendment'],
            'economy': ['GDP', 'Inflation', 'Fiscal Policy', 'Monetary Policy', 'Budget',
                       'Banking', 'Taxation', 'Subsidy', 'WTO', 'IMF', 'World Bank'],
            'history': ['Ancient', 'Medieval', 'Modern', 'Independence', 'Freedom Struggle',
                       'Mahatma Gandhi', 'Jawaharlal Nehru', 'Sardar Patel'],
            'geography': ['Climate', 'Monsoon', 'Soil', 'Agriculture', 'Mineral', 'Resources',
                         'River', 'Mountain', 'Forest', 'Biodiversity'],
            'environment': ['Pollution', 'Climate Change', 'Conservation', 'Wildlife',
                           'Sustainable Development', 'Renewable Energy', 'Paris Agreement'],
            'science': ['ISRO', 'Space', 'Technology', 'Nuclear', 'Defence', 'Research',
                       'Innovation', 'AI', 'Robotics', 'Biotechnology'],
            'international': ['UN', 'WTO', 'WHO', 'SAARC', 'BRICS', 'G20', 'ASEAN',
                            'Bilateral', 'Diplomacy', 'Foreign Policy']
        }
        
        logger.info(f"Running in {'GitHub Actions' if self.is_github_actions else 'Local'} mode")
    
    def load_cache(self):
        """Load cache of previously seen articles"""
        try:
            if os.path.exists('seen_articles.json'):
                with open('seen_articles.json', 'r') as f:
                    data = json.load(f)
                    # Only keep articles from last 2 days
                    cutoff = datetime.now() - timedelta(days=2)
                    for article_hash, timestamp in data.items():
                        if datetime.fromisoformat(timestamp) > cutoff:
                            self.seen_articles.add(article_hash)
        except:
            self.seen_articles = set()
    
    def save_cache(self):
        """Save cache of seen articles"""
        try:
            cache_data = {}
            cutoff = datetime.now() - timedelta(days=2)
            
            # Clean old entries
            with open('seen_articles.json', 'r') as f:
                old_data = json.load(f)
                for article_hash, timestamp in old_data.items():
                    if datetime.fromisoformat(timestamp) > cutoff:
                        cache_data[article_hash] = timestamp
            
            # Add current entries
            timestamp = datetime.now().isoformat()
            for article_hash in self.seen_articles:
                cache_data[article_hash] = timestamp
            
            with open('seen_articles.json', 'w') as f:
                json.dump(cache_data, f)
        except:
            pass
    
    def generate_article_hash(self, article):
        """Generate unique hash for article to detect duplicates"""
        # Use title + first 50 chars of summary for hash
        content = f"{article['title']}_{article['link'][:100]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_fresh_article(self, published_date_str):
        """Check if article is fresh (less than 24 hours old)"""
        try:
            # Try to parse various date formats
            published_date = None
            
            # Common RSS date formats
            date_formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S',
                '%d %b %Y',
                '%B %d, %Y'
            ]
            
            for fmt in date_formats:
                try:
                    published_date = datetime.strptime(published_date_str, fmt)
                    break
                except:
                    continue
            
            if not published_date:
                # If can't parse, assume it's recent
                return True
            
            # Check if within 24 hours
            age = datetime.now() - published_date.replace(tzinfo=None)
            return age.total_seconds() <= (self.max_age_hours * 3600)
            
        except Exception as e:
            logger.warning(f"Could not parse date '{published_date_str}': {e}")
            return True  # Give benefit of doubt
    
    def calculate_upsc_score(self, text):
        """Calculate UPSC relevance score"""
        score = 0
        text_lower = text.lower()
        
        # Check high priority keywords
        for keyword in self.upsc_keywords['high']:
            if keyword.lower() in text_lower:
                score += 5
        
        # Check medium priority keywords
        for keyword in self.upsc_keywords['medium']:
            if keyword.lower() in text_lower:
                score += 3
        
        # Check low priority keywords
        for keyword in self.upsc_keywords['low']:
            if keyword.lower() in text_lower:
                score += 1
        
        # Bonus for government sources
        govt_sources = ['pib', 'dd news', 'air news', 'mea', 'isro', 'csir']
        if any(source in text_lower for source in govt_sources):
            score += 2
        
        return score
    
    def categorize_upsc_subject(self, text):
        """Categorize article into UPSC subjects"""
        subjects = []
        text_lower = text.lower()
        
        for subject, keywords in self.upsc_subjects.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    subjects.append(subject)
                    break
        
        return subjects
    
    def fetch_all_news(self):
        """Get fresh news from all sources with duplicate removal"""
        all_articles = []
        
        for source_name, feed_url in self.news_sources.items():
            try:
                logger.info(f"📡 Fetching from {source_name}")
                
                # Add timeout and user-agent to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # Try to fetch with requests first for better error handling
                try:
                    response = requests.get(feed_url, headers=headers, timeout=10)
                    feed = feedparser.parse(response.content)
                except:
                    # Fallback to direct feedparser
                    feed = feedparser.parse(feed_url)
                
                if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
                    logger.warning(f"  ⚠️  RSS feed issue for {source_name}: {feed.bozo_exception}")
                
                article_count = 0
                for entry in feed.entries[:8]:  # Limit to 8 per source
                    try:
                        # Check freshness
                        published = entry.get('published', entry.get('updated', 'Recent'))
                        if not self.is_fresh_article(published):
                            continue
                        
                        # Generate article hash for duplicate detection
                        article_data = {
                            'title': entry.title[:200],
                            'link': entry.link,
                            'summary': entry.get('summary', entry.get('description', 'No summary'))[:300]
                        }
                        article_hash = self.generate_article_hash(article_data)
                        
                        # Skip duplicates
                        if article_hash in self.seen_articles:
                            continue
                        
                        self.seen_articles.add(article_hash)
                        
                        # Calculate UPSC relevance
                        content = f"{entry.title} {entry.get('summary', '')}"
                        upsc_score = self.calculate_upsc_score(content)
                        upsc_subjects = self.categorize_upsc_subject(content)
                        
                        article = {
                            'source': source_name,
                            'title': entry.title[:150],
                            'link': entry.link,
                            'published': published[:50],
                            'summary': article_data['summary'],
                            'upsc_score': upsc_score,
                            'upsc_subjects': upsc_subjects,
                            'hash': article_hash,
                            'is_govt_source': any(govt in source_name.lower() for govt in ['pib', 'dd', 'air', 'mea', 'isro', 'csir'])
                        }
                        
                        all_articles.append(article)
                        article_count += 1
                        
                    except Exception as e:
                        logger.warning(f"  ⚠️  Error processing article from {source_name}: {e}")
                        continue
                
                logger.info(f"  ✅ Found {article_count} fresh articles")
                
            except Exception as e:
                logger.error(f"❌ Error with {source_name}: {e}")
        
        # Sort by UPSC relevance score, then by govt source priority
        all_articles.sort(key=lambda x: (x['upsc_score'], x['is_govt_source']), reverse=True)
        
        # Save cache
        self.save_cache()
        
        return all_articles[:25]  # Return top 25 most relevant articles
    
    def create_html_content(self, articles):
        """Create beautiful React-like UI HTML content"""
        
        # Calculate statistics
        total_articles = len(articles)
        upsc_articles = len([a for a in articles if a['upsc_score'] > 0])
        govt_articles = len([a for a in articles if a['is_govt_source']])
        
        # Group by UPSC subjects
        subject_count = defaultdict(int)
        for article in articles:
            for subject in article['upsc_subjects']:
                subject_count[subject] += 1
        
        # Get top subjects
        top_subjects = sorted(subject_count.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Create timestamp
        now = datetime.now()
        timestamp = now.strftime("%A, %B %d, %Y • %I:%M %p")
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🇮🇳 India News Digest • UPSC Focus • {now.strftime('%b %d')}</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                :root {{
                    --primary: #1a365d;
                    --secondary: #2d3748;
                    --accent: #3182ce;
                    --success: #38a169;
                    --warning: #d69e2e;
                    --danger: #e53e3e;
                    --light: #f7fafc;
                    --dark: #2d3748;
                    --gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    --radius: 12px;
                }}
                
                body {{
                    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    color: var(--dark);
                    line-height: 1.6;
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                
                .header {{
                    background: var(--gradient);
                    color: white;
                    padding: 2.5rem;
                    border-radius: var(--radius);
                    margin-bottom: 2rem;
                    box-shadow: var(--shadow);
                    position: relative;
                    overflow: hidden;
                }}
                
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    right: 0;
                    width: 300px;
                    height: 300px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 50%;
                    transform: translate(100px, -100px);
                }}
                
                .header-content {{
                    position: relative;
                    z-index: 1;
                }}
                
                .header h1 {{
                    font-size: 2.5rem;
                    font-weight: 800;
                    margin-bottom: 0.5rem;
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                }}
                
                .header h1 i {{
                    font-size: 2rem;
                }}
                
                .subtitle {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                    margin-bottom: 1rem;
                }}
                
                .timestamp {{
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.9rem;
                    opacity: 0.8;
                }}
                
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }}
                
                .stat-card {{
                    background: white;
                    padding: 1.5rem;
                    border-radius: var(--radius);
                    box-shadow: var(--shadow);
                    display: flex;
                    align-items: center;
                    gap: 1rem;
                    transition: transform 0.3s ease;
                }}
                
                .stat-card:hover {{
                    transform: translateY(-5px);
                }}
                
                .stat-icon {{
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    color: white;
                }}
                
                .stat-1 {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .stat-2 {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
                .stat-3 {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
                .stat-4 {{ background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }}
                
                .stat-info h3 {{
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: var(--primary);
                }}
                
                .stat-info p {{
                    font-size: 0.9rem;
                    color: var(--secondary);
                    opacity: 0.8;
                }}
                
                .articles-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                    gap: 1.5rem;
                    margin-bottom: 2rem;
                }}
                
                .article-card {{
                    background: white;
                    border-radius: var(--radius);
                    overflow: hidden;
                    box-shadow: var(--shadow);
                    transition: all 0.3s ease;
                    border-left: 5px solid var(--accent);
                }}
                
                .article-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
                }}
                
                .article-card.high-priority {{
                    border-left-color: var(--success);
                }}
                
                .article-card.govt-source {{
                    border-left-color: var(--warning);
                }}
                
                .article-header {{
                    padding: 1.5rem;
                    border-bottom: 1px solid #e2e8f0;
                }}
                
                .article-title {{
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: var(--primary);
                    margin-bottom: 0.75rem;
                    line-height: 1.4;
                }}
                
                .article-title a {{
                    color: inherit;
                    text-decoration: none;
                    transition: color 0.2s;
                }}
                
                .article-title a:hover {{
                    color: var(--accent);
                }}
                
                .article-meta {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 0.85rem;
                    color: var(--secondary);
                }}
                
                .source-badge {{
                    background: #e2e8f0;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-weight: 600;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                .article-body {{
                    padding: 1.5rem;
                }}
                
                .article-summary {{
                    color: var(--secondary);
                    margin-bottom: 1.5rem;
                    line-height: 1.6;
                }}
                
                .upsc-badges {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                    margin-bottom: 1rem;
                }}
                
                .upsc-badge {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.75rem;
                    font-weight: 600;
                }}
                
                .upsc-badge.subject {{
                    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                }}
                
                .upsc-badge.govt {{
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                
                .upsc-score {{
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                    background: #f0fff4;
                    color: #38a169;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 0.9rem;
                }}
                
                .article-footer {{
                    padding: 1rem 1.5rem;
                    background: #f8fafc;
                    border-top: 1px solid #e2e8f0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .read-more {{
                    background: var(--accent);
                    color: white;
                    padding: 0.5rem 1.25rem;
                    border-radius: 20px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.9rem;
                    transition: all 0.2s;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                .read-more:hover {{
                    background: var(--primary);
                    transform: scale(1.05);
                }}
                
                .date {{
                    font-size: 0.85rem;
                    color: var(--secondary);
                    opacity: 0.8;
                }}
                
                .footer {{
                    text-align: center;
                    padding: 2rem;
                    color: var(--secondary);
                    font-size: 0.9rem;
                    opacity: 0.8;
                    border-top: 1px solid #e2e8f0;
                    margin-top: 2rem;
                }}
                
                .subject-tags {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.75rem;
                    margin: 1.5rem 0;
                    justify-content: center;
                }}
                
                .subject-tag {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 0.5rem 1.25rem;
                    border-radius: 25px;
                    font-size: 0.9rem;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }}
                
                @media (max-width: 768px) {{
                    .header h1 {{
                        font-size: 2rem;
                    }}
                    
                    .articles-container {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .stats-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <div class="header-content">
                        <h1>
                            <i class="fas fa-newspaper"></i>
                            India News Digest
                        </h1>
                        <div class="subtitle">
                            Curated Daily Digest • UPSC Focused • Government Verified Sources
                        </div>
                        <div class="timestamp">
                            <i class="far fa-clock"></i>
                            {timestamp}
                        </div>
                    </div>
                </div>
                
                <!-- Statistics -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon stat-1">
                            <i class="fas fa-newspaper"></i>
                        </div>
                        <div class="stat-info">
                            <h3>{total_articles}</h3>
                            <p>Fresh Articles Today</p>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon stat-2">
                            <i class="fas fa-graduation-cap"></i>
                        </div>
                        <div class="stat-info">
                            <h3>{upsc_articles}</h3>
                            <p>UPSC Relevant Articles</p>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon stat-3">
                            <i class="fas fa-landmark"></i>
                        </div>
                        <div class="stat-info">
                            <h3>{govt_articles}</h3>
                            <p>Government Sources</p>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <div class="stat-icon stat-4">
                            <i class="fas fa-filter"></i>
                        </div>
                        <div class="stat-info">
                            <h3>{len(top_subjects)}</h3>
                            <p>Key UPSC Subjects</p>
                        </div>
                    </div>
                </div>
                
                <!-- Subject Tags -->
                <div class="subject-tags">
                    {''.join([f'<div class="subject-tag"><i class="fas fa-tag"></i> {subject.title()} ({count})</div>' for subject, count in top_subjects])}
                </div>
                
                <!-- Articles Grid -->
                <div class="articles-container">
        """
        
        # Add articles
        for article in articles:
            # Determine card class based on priority
            card_class = "article-card"
            if article['upsc_score'] >= 10:
                card_class += " high-priority"
            if article['is_govt_source']:
                card_class += " govt-source"
            
            # Create UPSC badges
            upsc_badges = ""
            if article['upsc_score'] > 0:
                upsc_badges += f'<div class="upsc-badge">UPSC Score: {article["upsc_score"]}</div>'
            
            for subject in article['upsc_subjects'][:3]:  # Show max 3 subjects
                upsc_badges += f'<div class="upsc-badge subject">{subject.title()}</div>'
            
            if article['is_govt_source']:
                upsc_badges += '<div class="upsc-badge govt">Govt Source</div>'
            
            html += f"""
                    <div class="{card_class}">
                        <div class="article-header">
                            <h2 class="article-title">
                                <a href="{article['link']}" target="_blank">{article['title']}</a>
                            </h2>
                            <div class="article-meta">
                                <span class="source-badge">
                                    {article['source'].split(' ')[0]} {article['source'].split(' ')[1] if len(article['source'].split(' ')) > 1 else ''}
                                </span>
                                <span class="date">
                                    <i class="far fa-clock"></i> {article['published']}
                                </span>
                            </div>
                        </div>
                        
                        <div class="article-body">
                            <p class="article-summary">
                                {article['summary']}
                            </p>
                            
                            <div class="upsc-badges">
                                {upsc_badges}
                            </div>
                        </div>
                        
                        <div class="article-footer">
                            <a href="{article['link']}" target="_blank" class="read-more">
                                <i class="fas fa-external-link-alt"></i>
                                Read Full Story
                            </a>
                            {f'<div class="upsc-score"><i class="fas fa-star"></i> UPSC Relevant</div>' if article['upsc_score'] > 5 else ''}
                        </div>
                    </div>
            """
        
        html += """
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <p>
                        <strong>📌 Important Notes:</strong><br>
                        1. All news is sourced from Indian government-approved and verified sources<br>
                        2. Articles are filtered for freshness (last 24 hours) and UPSC relevance<br>
                        3. Duplicate news has been removed for better reading experience<br>
                        4. Generated with ❤️ for UPSC aspirants and informed citizens
                    </p>
                    <p style="margin-top: 1rem;">
                        <i class="fas fa-sync-alt"></i> Updated Daily • 
                        <i class="fas fa-filter"></i> Smart Filtering • 
                        <i class="fas fa-graduation-cap"></i> UPSC Focused
                    </p>
                    <p style="margin-top: 1rem; font-size: 0.8rem;">
                        Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """ IST
                    </p>
                </div>
            </div>
            
            <script>
                // Add interactivity
                document.addEventListener('DOMContentLoaded', function() {{
                    // Add click tracking
                    document.querySelectorAll('.read-more').forEach(link => {{
                        link.addEventListener('click', function(e) {{
                            console.log('Opening:', this.href);
                        }});
                    }});
                    
                    // Add animation on scroll
                    const observerOptions = {{
                        threshold: 0.1,
                        rootMargin: '0px 0px -50px 0px'
                    }};
                    
                    const observer = new IntersectionObserver((entries) => {{
                        entries.forEach(entry => {{
                            if (entry.isIntersecting) {{
                                entry.target.style.opacity = '1';
                                entry.target.style.transform = 'translateY(0)';
                            }}
                        }});
                    }}, observerOptions);
                    
                    document.querySelectorAll('.article-card').forEach(card => {{
                        card.style.opacity = '0';
                        card.style.transform = 'translateY(20px)';
                        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                        observer.observe(card);
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, html_content):
        """Send email with beautiful HTML content"""
        
        if not all([self.sender_email, self.sender_password]):
            logger.error("❌ Email credentials missing in .env file")
            return False
        
        # Get recipients
        receiver_email = self.receiver_email
        additional_emails_str = os.getenv('ADDITIONAL_EMAILS', '')
        
        additional_emails = []
        if additional_emails_str:
            additional_emails = [email.strip() for email in additional_emails_str.split(',') if email.strip()]
        
        all_recipients = list(set([receiver_email] + additional_emails))
        
        if len(all_recipients) == 0:
            logger.error("❌ No recipient emails found")
            return False
        
        logger.info(f"📧 Preparing email for {len(all_recipients)} recipients")
        
        try:
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🇮🇳 India News Digest • UPSC Focus • {datetime.now().strftime('%b %d')}"
            msg['From'] = f"India News Digest <{self.sender_email}>"
            
            # Set recipients
            msg['To'] = receiver_email
            if len(all_recipients) > 1:
                bcc_recipients = all_recipients[1:]
                msg['BCC'] = ', '.join(bcc_recipients)
                logger.info(f"  To: {receiver_email}")
                logger.info(f"  BCC: {len(bcc_recipients)} recipients")
            
            # Attach HTML
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            try:
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
                logger.info("✅ Email sent successfully via SSL")
                
            except Exception as e1:
                logger.warning(f"SSL failed, trying TLS: {e1}")
                server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                server.quit()
                logger.info("✅ Email sent successfully via TLS")
            
            logger.info(f"🎉 Email delivered to {len(all_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def save_to_html_file(self, html_content):
        """Save HTML content to a local file"""
        try:
            # Create filename
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
        """Main execution function"""
        logger.info("=" * 70)
        logger.info("🚀 STARTING INDIA NEWS DIGEST - UPSC FOCUSED")
        logger.info("=" * 70)
        
        try:
            # Step 1: Fetch fresh news
            logger.info("📥 Fetching fresh news (last 24 hours)...")
            articles = self.fetch_all_news()
            
            if not articles:
                logger.warning("⚠️ No fresh articles found!")
                return
            
            # Statistics
            upsc_count = len([a for a in articles if a['upsc_score'] > 0])
            govt_count = len([a for a in articles if a['is_govt_source']])
            
            logger.info(f"✅ Found {len(articles)} fresh articles")
            logger.info(f"   📚 UPSC Relevant: {upsc_count}")
            logger.info(f"   🏛️ Government Sources: {govt_count}")
            logger.info(f"   🔍 Duplicates Removed: {len(self.seen_articles) - len(articles)}")
            
            # Step 2: Create HTML
            logger.info("🎨 Creating beautiful digest...")
            html_content = self.create_html_content(articles)
            
            # Step 3: Send or Save
            if self.is_github_actions:
                logger.info("🚀 GitHub Actions Mode - Sending email...")
                success = self.send_email(html_content)
                
                if success:
                    logger.info("🎉 Digest sent successfully!")
                else:
                    logger.error("💥 Email failed, saving locally...")
                    self.save_to_html_file(html_content)
                    
            else:
                logger.info("💻 Local Mode - Saving to file...")
                filepath = self.save_to_html_file(html_content)
                
                if filepath:
                    logger.info(f"📄 File saved: {filepath}")
                    
                    # Terminal preview
                    print("\n" + "="*70)
                    print("📊 TODAY'S TOP STORIES FOR UPSC:")
                    print("="*70)
                    for i, article in enumerate(articles[:8], 1):
                        score_stars = "★" * min(article['upsc_score'] // 2, 5)
                        print(f"{i}. {article['title'][:80]}...")
                        print(f"   📍 {article['source']}")
                        if article['upsc_score'] > 0:
                            print(f"   🎯 UPSC Score: {article['upsc_score']} {score_stars}")
                        if article['upsc_subjects']:
                            print(f"   📚 Subjects: {', '.join(article['upsc_subjects'][:3])}")
                        print()
                
                # Optional: Try email locally
                if self.sender_email and self.sender_password:
                    logger.info("📤 Attempting to send email locally...")
                    self.send_email(html_content)
            
            logger.info("=" * 70)
            logger.info("✅ PROCESS COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"💥 Critical error: {e}", exc_info=True)
            raise

def main():
    """Entry point"""
    digest = IndiaNewsDigest()
    digest.run()

if __name__ == "__main__":
    main()
