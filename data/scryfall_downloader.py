#!/usr/bin/env python3
"""
Scryfall Data Downloader

Downloads and caches Scryfall bulk data for MTGA card resolution.
Creates a local JSON cache with card metadata indexed by Arena ID and name.
"""

import json
import os
import requests
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScryfallDownloader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.cards_file = self.data_dir / "cards.json"
        self.bulk_file = self.data_dir / "scryfall_bulk.json"
        
    def download_bulk_data(self) -> bool:
        """Download Scryfall bulk data and save to local file."""
        try:
            logger.info("Fetching Scryfall bulk data...")
            
            # Get bulk data endpoint
            response = requests.get("https://api.scryfall.com/bulk-data")
            response.raise_for_status()
            
            bulk_data = response.json()
            
            # Find Oracle Cards bulk data
            oracle_cards_url = None
            for item in bulk_data["data"]:
                if item["type"] == "oracle_cards":
                    oracle_cards_url = item["download_uri"]
                    break
            
            if not oracle_cards_url:
                logger.error("Could not find Oracle Cards bulk data")
                return False
            
            # Download the actual card data
            logger.info(f"Downloading Oracle Cards from {oracle_cards_url}")
            response = requests.get(oracle_cards_url)
            response.raise_for_status()
            
            # Save raw bulk data
            with open(self.bulk_file, 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, indent=2)
            
            logger.info(f"Bulk data saved to {self.bulk_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download bulk data: {e}")
            return False
    
    def process_cards(self) -> bool:
        """Process bulk data and create optimized card cache."""
        try:
            if not self.bulk_file.exists():
                logger.error("Bulk data file not found. Run download_bulk_data() first.")
                return False
            
            logger.info("Processing card data...")
            
            with open(self.bulk_file, 'r', encoding='utf-8') as f:
                bulk_data = json.load(f)
            
            # Create optimized card cache
            cards_cache = {
                "by_arena_id": {},
                "by_name": {},
                "by_scryfall_id": {},
                "metadata": {
                    "total_cards": 0,
                    "processed_at": None
                }
            }
            
            processed_count = 0
            for card in bulk_data:
                # Skip digital-only cards that aren't in Arena
                if card.get("digital", False) and not card.get("arena_id"):
                    continue
                
                # Extract essential card data
                card_data = {
                    "name": card.get("name", ""),
                    "mana_cost": card.get("mana_cost", ""),
                    "cmc": card.get("cmc", 0),
                    "type_line": card.get("type_line", ""),
                    "oracle_text": card.get("oracle_text", ""),
                    "power": card.get("power"),
                    "toughness": card.get("toughness"),
                    "colors": card.get("colors", []),
                    "color_identity": card.get("color_identity", []),
                    "keywords": card.get("keywords", []),
                    "arena_id": card.get("arena_id"),
                    "scryfall_id": card.get("id"),
                    "set": card.get("set", ""),
                    "rarity": card.get("rarity", ""),
                    "legalities": card.get("legalities", {}),
                    "image_uris": card.get("image_uris", {}),
                    "card_faces": card.get("card_faces", [])
                }
                
                # Index by Arena ID if available
                if card_data["arena_id"]:
                    cards_cache["by_arena_id"][str(card_data["arena_id"])] = card_data
                
                # Index by name (handle multiple versions)
                name = card_data["name"].lower()
                if name not in cards_cache["by_name"]:
                    cards_cache["by_name"][name] = []
                cards_cache["by_name"][name].append(card_data)
                
                # Index by Scryfall ID
                cards_cache["by_scryfall_id"][card_data["scryfall_id"]] = card_data
                
                processed_count += 1
                
                if processed_count % 1000 == 0:
                    logger.info(f"Processed {processed_count} cards...")
            
            # Update metadata
            cards_cache["metadata"]["total_cards"] = processed_count
            cards_cache["metadata"]["processed_at"] = str(Path().cwd())
            
            # Save processed cache
            with open(self.cards_file, 'w', encoding='utf-8') as f:
                json.dump(cards_cache, f, indent=2)
            
            logger.info(f"Card cache saved to {self.cards_file}")
            logger.info(f"Processed {processed_count} cards total")
            logger.info(f"Cards with Arena IDs: {len(cards_cache['by_arena_id'])}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process cards: {e}")
            return False
    
    def load_cards_cache(self) -> Optional[Dict]:
        """Load the processed cards cache."""
        try:
            if not self.cards_file.exists():
                logger.warning("Cards cache not found. Run download and process first.")
                return None
            
            with open(self.cards_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Failed to load cards cache: {e}")
            return None
    
    def get_card_by_arena_id(self, arena_id: str) -> Optional[Dict]:
        """Get card data by Arena ID."""
        cache = self.load_cards_cache()
        if cache:
            return cache["by_arena_id"].get(str(arena_id))
        return None
    
    def get_card_by_name(self, name: str) -> Optional[List[Dict]]:
        """Get card data by name (returns all versions)."""
        cache = self.load_cards_cache()
        if cache:
            return cache["by_name"].get(name.lower())
        return None

def main():
    """Main function to download and process Scryfall data."""
    downloader = ScryfallDownloader()
    
    print("MTGA Coach - Scryfall Data Downloader")
    print("=" * 40)
    
    # Download bulk data
    if not downloader.download_bulk_data():
        print("Failed to download bulk data")
        return False
    
    # Process cards
    if not downloader.process_cards():
        print("Failed to process cards")
        return False
    
    print("Scryfall data download and processing complete!")
    print(f"Card cache saved to: {downloader.cards_file}")
    
    # Test the cache
    cache = downloader.load_cards_cache()
    if cache:
        print(f"Cache contains {cache['metadata']['total_cards']} cards")
        print(f"Cards with Arena IDs: {len(cache['by_arena_id'])}")
    
    return True

if __name__ == "__main__":
    main()
