#!/usr/bin/env python3
"""
Script to generate synthetic texts using Faker and populate JSONL files
for load testing the preprocessing service.
"""

import json
import uuid
import random
from faker import Faker

fake = Faker()


def generate_short_text() -> str:
    """Generate short text (50-200 chars) with various features"""
    templates = [
        # Social media style
        lambda: f"Check out this cool article: {fake.url()} #{fake.word()}",
        lambda: f"Just had lunch at {fake.company()}! Contact them at {fake.email()}",
        lambda: f"{fake.sentence()} Visit {fake.url()} for more info.",
        lambda: f"Breaking: {fake.sentence()} More at {fake.url()}",
        
        # Business style
        lambda: f"Dear customer, please contact {fake.email()} for support.",
        lambda: f"New promotion available! Call {fake.phone_number()} today.",
        lambda: f"Order #{fake.random_int(min=1000, max=9999)} shipped to {fake.address().replace('\n', ', ')}",
        
        # Mixed content
        lambda: f"{fake.text(max_nb_chars=100)} Email: {fake.email()}",
        lambda: f"{fake.sentence()} Price: ${fake.random_int(min=10, max=1000)}",
        lambda: f"User {fake.user_name()}: {fake.sentence()}",
        
        # Simple sentences
        lambda: fake.sentence(),
        lambda: f"{fake.sentence()} {fake.sentence()}",
    ]
    
    text = random.choice(templates)()
    
    # Ensure it's within short range
    while len(text) > 200:
        text = random.choice(templates[:6])()  # Use shorter templates
    
    # Add some randomness to trigger different preprocessing features
    if random.random() < 0.2:
        text += f" Special chars: @#$%^&*()!"
    if random.random() < 0.3:
        text += f" Numbers: {fake.random_int(min=1, max=9999)}"
    
    return text


def generate_medium_text() -> str:
    """Generate medium text (200-1500 chars) with various features"""
    templates = [
        # Article style
        lambda: f"{fake.paragraph()} For more information, visit {fake.url()} or contact us at {fake.email()}. You can also call {fake.phone_number()} during business hours.",
        
        # Product description
        lambda: f"{fake.company()} presents: {fake.sentence()} {fake.paragraph()} Order now at {fake.url()} or email {fake.email()}. Price: ${fake.random_int(min=100, max=5000)}. Shipping available to {fake.address().replace(chr(10), ', ')}.",
        
        # News article
        lambda: f"BREAKING: {fake.sentence()} {fake.paragraph()} {fake.paragraph()} Source: {fake.url()}. For comments, contact {fake.email()}. #breaking #news",
        
        # Technical content
        lambda: f"Documentation for {fake.word()}: {fake.paragraph()} Configuration: {fake.paragraph()} For support, visit {fake.url()} or email support@{fake.domain_name()}. Version: {fake.random_int(min=1, max=10)}.{fake.random_int(min=0, max=99)}",
        
        # Email content
        lambda: f"Subject: {fake.sentence()} Dear {fake.name()}, {fake.paragraph()} {fake.paragraph()} Best regards, {fake.name()} {fake.email()} {fake.phone_number()}",
        
        # Review style
        lambda: f"Review of {fake.company()}: {fake.paragraph()} Rating: {fake.random_int(min=1, max=5)}/5 stars. Would recommend! Contact: {fake.url()}",
    ]
    
    text = random.choice(templates)()
    
    # Pad or trim to medium range
    while len(text) < 200:
        text += f" {fake.sentence()}"
    
    while len(text) > 1500:
        text = text[:1400] + "..."
    
    # Add special characters and numbers
    if random.random() < 0.4:
        text += f" Special: !@#$%^&*() Numbers: {fake.random_int(min=1000, max=99999)}"
    
    return text


def generate_long_text() -> str:
    """Generate long text (1500+ chars) with various features"""
    templates = [
        # Long article
        lambda: f"""
        {fake.sentence()} {fake.paragraph()} {fake.paragraph()} {fake.paragraph()}
        
        For detailed information, please visit our website at {fake.url()} or contact our support team at {fake.email()}.
        You can also reach us by phone at {fake.phone_number()} during business hours (9 AM - 5 PM EST).
        
        {fake.paragraph()} {fake.paragraph()}
        
        Additional resources:
        - Website: {fake.url()}
        - Support: support@{fake.domain_name()}
        - Sales: sales@{fake.domain_name()}
        - Phone: {fake.phone_number()}
        
        {fake.paragraph()} Special pricing available! Use code SAVE20 for 20% off.
        
        {fake.paragraph()} Don't forget to follow us on social media @{fake.user_name()} for updates!
        """.strip(),
        
        # Technical documentation
        lambda: f"""
        {fake.company()} Technical Documentation v{fake.random_int(min=1, max=5)}.{fake.random_int(min=0, max=99)}
        
        Overview: {fake.paragraph()}
        
        Installation Instructions:
        {fake.paragraph()} {fake.paragraph()}
        
        Configuration:
        {fake.paragraph()} For configuration examples, visit {fake.url()}/docs
        
        API Endpoints:
        - GET {fake.url()}/api/users
        - POST {fake.url()}/api/data
        - DELETE {fake.url()}/api/cleanup
        
        Troubleshooting:
        {fake.paragraph()} If issues persist, contact support@{fake.domain_name()} or call {fake.phone_number()}.
        
        {fake.paragraph()} {fake.paragraph()}
        
        License: MIT License. For questions, email legal@{fake.domain_name()}.
        """.strip(),
        
        # Long email/letter
        lambda: f"""
        Subject: {fake.sentence()}
        
        Dear {fake.name()},
        
        {fake.paragraph()}
        
        {fake.paragraph()} {fake.paragraph()}
        
        Here are the key points we discussed:
        1. {fake.sentence()}
        2. {fake.sentence()}
        3. {fake.sentence()}
        
        {fake.paragraph()}
        
        Please don't hesitate to contact me at {fake.email()} or {fake.phone_number()} if you have any questions.
        You can also visit our website at {fake.url()} for more information.
        
        {fake.paragraph()}
        
        Best regards,
        {fake.name()}
        {fake.job()}
        {fake.company()}
        {fake.email()}
        {fake.phone_number()}
        {fake.url()}
        
        P.S. {fake.sentence()}
        """.strip(),
        
        # Story/content
        lambda: f"""
        {fake.sentence()}
        
        {fake.paragraph()} {fake.paragraph()} {fake.paragraph()}
        
        {fake.paragraph()} The main character's email was {fake.email()} and they lived at {fake.address().replace(chr(10), ', ')}.
        
        {fake.paragraph()} {fake.paragraph()}
        
        For more stories like this, visit {fake.url()} or subscribe to our newsletter by emailing subscribe@{fake.domain_name()}.
        
        {fake.paragraph()} Special characters appeared everywhere: !@#$%^&*()[]{'{'}|;:,.<>?
        
        {fake.paragraph()} The numbers were significant: {fake.random_int(min=1000, max=999999)}, {fake.random_int(min=100, max=9999)}.
        
        {fake.paragraph()}
        """.strip(),
    ]
    
    text = random.choice(templates)()
    
    # Ensure it's long enough
    while len(text) < 1500:
        text += f"\n\n{fake.paragraph()}"
    
    return text


def classify_text_size(text: str) -> str:
    """Classify text by length"""
    length = len(text)
    if length < 200:
        return "short"
    elif length < 1500:
        return "medium"
    else:
        return "long"


def create_text_entry(content: str, entry_id: str) -> dict:
    """Create a standardized text entry"""
    return {
        "id": entry_id,
        "content": content.strip(),
        "size": len(content),
        "category": classify_text_size(content)
    }


def generate_texts(target_category: str, count: int = 1000):
    """Generate texts for a specific category"""
    texts = []
    generators = {
        "short": generate_short_text,
        "medium": generate_medium_text,
        "long": generate_long_text
    }
    
    generator = generators[target_category]
    
    for i in range(count):
        text = generator()
        entry_id = f"{target_category}_{i+1:04d}"
        texts.append(create_text_entry(text, entry_id))
    
    return texts


def save_texts_to_jsonl(texts, file_path):
    """Save texts to JSONL file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for text in texts:
            f.write(json.dumps(text, ensure_ascii=False) + '\n')


def main():
    print("Generating synthetic texts for load testing...")
    
    categories = ["short", "medium", "long"]
    
    for category in categories:
        print(f"Generating {category} texts...")
        texts = generate_texts(category, 1000)
        
        file_path = f"datasets/{category}.jsonl"
        save_texts_to_jsonl(texts, file_path)
        
        print(f"Saved 1000 {category} texts to {file_path}")
        
        # Show sample
        sample = texts[0]
        print(f"Sample {category} text ({sample['size']} chars): {sample['content'][:100]}...")
        print()
    
    print("Dataset generation complete!")
    print("Files created:")
    print("- datasets/short.jsonl (1000 entries)")
    print("- datasets/medium.jsonl (1000 entries)")
    print("- datasets/long.jsonl (1000 entries)")


if __name__ == "__main__":
    main()