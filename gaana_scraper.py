# ============================================================
# GAANA REVIEW SCRAPER
# ============================================================

# Step 1: Install
# !pip install google-play-scraper

from google_play_scraper import reviews, Sort
import pandas as pd
import json

# Step 2: Scrape reviews
print("Scraping Gaana reviews from Play Store...")

result, _ = reviews(
    'com.gaana',           # Gaana's package ID
    lang='en',             # English reviews
    country='in',          # India
    sort=Sort.NEWEST,      # Most recent first
    count=500,             # Pull 500 reviews
)

print(f"Fetched {len(result)} reviews")

# Step 3: Convert to DataFrame
df = pd.DataFrame(result)[['userName', 'score', 'content', 'at', 'thumbsUpCount']]
df.columns = ['user', 'rating', 'review', 'date', 'likes']
df['date'] = pd.to_datetime(df['date']).dt.date

# Step 4: Filter relevant reviews (discovery-related keywords)
discovery_keywords = [
    'recommend', 'discover', 'suggest', 'new song', 'new music',
    'same song', 'repeat', 'boring', 'playlist', 'autoplay',
    'radio', 'similar', 'variety', 'explore', 'find music',
    'algorithm', 'boring', 'shuffle', 'mix'
]

pattern = '|'.join(discovery_keywords)
df_discovery = df[df['review'].str.lower().str.contains(pattern, na=False)]

print(f"\nTotal reviews: {len(df)}")
print(f"Discovery-related reviews: {len(df_discovery)}")
print(f"\nRating distribution:")
print(df['rating'].value_counts().sort_index())

# Step 5: Save both files
df.to_csv('gaana_all_reviews.csv', index=False)
df_discovery.to_csv('gaana_discovery_reviews.csv', index=False)

print("\n✅ Saved: gaana_all_reviews.csv")
print("✅ Saved: gaana_discovery_reviews.csv")
print("\nSample discovery reviews:")
print(df_discovery[['rating', 'review']].head(5).to_string())
