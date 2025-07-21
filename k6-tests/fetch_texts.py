#!/usr/bin/env python3
"""
Script to fetch texts from various internet sources and populate JSONL dataset files
for load testing the preprocessing service.
"""

import json
import re
import uuid
from typing import List, Dict, Any
import requests
from urllib.parse import urljoin
import time


class TextFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def classify_text_size(self, text: str) -> str:
        """Classify text by length"""
        length = len(text)
        if length < 200:
            return "short"
        elif length < 1500:
            return "medium"
        else:
            return "long"
    
    def detect_features(self, text: str) -> List[str]:
        """Detect features in text for testing different preprocessing scenarios"""
        features = []
        
        if re.search(r'http[s]?://\S+', text):
            features.append("urls")
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            features.append("emails")
        if re.search(r'[^\w\s.,!?;:]', text):
            features.append("special_chars")
        if re.search(r'\d+', text):
            features.append("numbers")
        if re.search(r'[A-Z]', text) and re.search(r'[a-z]', text):
            features.append("mixed_case")
        if len(re.findall(r'[.,!?;:]', text)) > len(text) * 0.05:
            features.append("punctuation_heavy")
        if re.search(r'#\w+', text):
            features.append("hashtags")
            
        return features
    
    def create_text_entry(self, content: str, source: str, text_type: str = "general") -> Dict[str, Any]:
        """Create a standardized text entry"""
        return {
            "id": str(uuid.uuid4())[:8],
            "content": content.strip(),
            "size": len(content),
            "category": self.classify_text_size(content),
            "features": self.detect_features(content),
            "source": source,
            "type": text_type
        }
    
    def fetch_news_articles(self) -> List[Dict[str, Any]]:
        """Fetch news articles from Hacker News"""
        texts = []
        try:
            # Get top stories
            response = self.session.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = response.json()[:30]  # Get top 30 stories
            
            for story_id in story_ids[:10]:  # Limit to 10 for demo
                try:
                    story_response = self.session.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
                    story = story_response.json()
                    
                    if story and 'title' in story:
                        title = story['title']
                        text = title
                        
                        # Add text if available
                        if 'text' in story and story['text']:
                            text = f"{title}. {story['text']}"
                        
                        texts.append(self.create_text_entry(text, "hackernews", "news"))
                        time.sleep(0.1)  # Rate limiting
                        
                except Exception as e:
                    print(f"Error fetching story {story_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
            
        return texts
    
    def fetch_quotes(self) -> List[Dict[str, Any]]:
        """Fetch quotes from quotable.io API"""
        texts = []
        try:
            for page in range(1, 6):  # Get 5 pages
                response = self.session.get(f"https://api.quotable.io/quotes?page={page}&limit=20")
                data = response.json()
                
                for quote in data.get('results', []):
                    content = f'"{quote["content"]}" - {quote["author"]}'
                    texts.append(self.create_text_entry(content, "quotable", "quote"))
                    
                time.sleep(0.2)  # Rate limiting
                
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            
        return texts
    
    def fetch_lorem_variants(self) -> List[Dict[str, Any]]:
        """Generate various lorem ipsum style texts"""
        texts = []
        
        # Short lorem texts
        short_texts = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "Ut enim ad minim veniam, quis nostrud exercitation.",
            "Contact support@example.com for help with https://example.com/docs",
            "Check out our new features at https://product.com! #innovation #tech"
        ]
        
        # Medium lorem text
        medium_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
        incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
        exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure 
        dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
        For more information, visit https://lorem-ipsum.com or email info@lorem.com. 
        Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt 
        mollit anim id est laborum. #lorem #ipsum #test"""
        
        # Long lorem text
        long_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

        Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.

        For technical support, contact support@company.com or visit our documentation at https://docs.company.com/api/v1/preprocessing. You can also reach us at +1-555-123-4567 or through our social media @company_handle.

        Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur?

        #lorem #ipsum #testing #preprocessing #api #performance #benchmark"""
        
        for text in short_texts:
            texts.append(self.create_text_entry(text, "generated", "lorem"))
            
        texts.append(self.create_text_entry(medium_text, "generated", "lorem"))
        texts.append(self.create_text_entry(long_text, "generated", "lorem"))
        
        return texts
    
    def save_texts_to_jsonl(self, texts: List[Dict[str, Any]], base_path: str):
        """Save texts to appropriate JSONL files based on category"""
        categorized = {"short": [], "medium": [], "long": []}
        
        for text in texts:
            category = text["category"]
            if category in categorized:
                categorized[category].append(text)
        
        for category, category_texts in categorized.items():
            file_path = f"{base_path}/{category}.jsonl"
            
            # Read existing content
            existing_texts = []
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        if line.strip():
                            existing_texts.append(json.loads(line))
            except FileNotFoundError:
                pass
            
            # Append new texts
            with open(file_path, 'w') as f:
                # Write existing texts back
                for text in existing_texts:
                    f.write(json.dumps(text) + '\n')
                
                # Write new texts
                for text in category_texts:
                    f.write(json.dumps(text) + '\n')
            
            print(f"Added {len(category_texts)} texts to {category}.jsonl")


def main():
    fetcher = TextFetcher()
    all_texts = []
    
    print("Fetching texts from various sources...")
    
    # Fetch from different sources
    print("- Fetching Hacker News stories...")
    all_texts.extend(fetcher.fetch_news_articles())
    
    print("- Fetching quotes...")
    all_texts.extend(fetcher.fetch_quotes())
    
    print("- Generating lorem ipsum variants...")
    all_texts.extend(fetcher.fetch_lorem_variants())
    
    print(f"\nTotal texts fetched: {len(all_texts)}")
    
    # Show distribution
    short_count = len([t for t in all_texts if t['category'] == 'short'])
    medium_count = len([t for t in all_texts if t['category'] == 'medium'])
    long_count = len([t for t in all_texts if t['category'] == 'long'])
    
    print(f"Distribution: Short={short_count}, Medium={medium_count}, Long={long_count}")
    
    # Save to JSONL files
    datasets_path = "datasets"
    fetcher.save_texts_to_jsonl(all_texts, datasets_path)
    
    print(f"\nTexts saved to {datasets_path}/{{short,medium,long}}.jsonl")
    print("Ready for load testing!")


if __name__ == "__main__":
    main()