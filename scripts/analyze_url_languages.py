"""Analyze existing URLs by predicted language.

This script analyzes all PENDING URLs in the database and predicts their language
using the LanguagePredictor from crawler-node. It generates statistics about the
language distribution and saves a list of non-EU URL IDs for cleanup.

Usage:
    python scripts/analyze_url_languages.py

Output:
    - Prints language distribution statistics
    - Creates /tmp/non_eu_urls.txt with IDs of non-EU URLs
"""

import sys
from collections import Counter
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Add crawler-node to path (assumes it's in the same parent directory)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "crawler-node" / "src"))

from src.database import SessionLocal
from src.models.url import URL, URLStatus

try:
    from crawler_node.language_predictor import LanguagePredictor
    from crawler_node.constants import EU_LANGUAGES
except ImportError:
    print("ERROR: Could not import crawler_node modules.")
    print("Make sure crawler-node is installed or available in ../crawler-node/")
    sys.exit(1)


def analyze_urls() -> None:
    """Analyze PENDING URLs and categorize by predicted language."""
    print("Initializing database session...")
    db = SessionLocal()

    print("Initializing language predictor...")
    predictor = LanguagePredictor()

    print("\nQuerying PENDING URLs from database...")
    pending_urls = db.query(URL).filter(URL.status == URLStatus.PENDING).all()

    total_urls = len(pending_urls)
    print(f"Found {total_urls:,} PENDING URLs")

    if total_urls == 0:
        print("No PENDING URLs to analyze.")
        db.close()
        return

    print("\nAnalyzing language for each URL...")
    language_counts = Counter()
    non_eu_url_ids = []
    eu_url_ids = []
    unknown_url_ids = []

    # Process URLs in batches for progress reporting
    batch_size = 1000
    for i in range(0, total_urls, batch_size):
        batch = pending_urls[i : i + batch_size]

        for url_obj in batch:
            predicted_lang = predictor.predict(url_obj.url)

            if predicted_lang == "SKIP":
                # Definitely non-EU
                non_eu_url_ids.append(url_obj.id)
                language_counts["NON_EU_SKIP"] += 1
            elif predicted_lang is None:
                # Unknown language (keep it)
                unknown_url_ids.append(url_obj.id)
                language_counts["UNKNOWN"] += 1
            elif predicted_lang in EU_LANGUAGES:
                # EU language
                eu_url_ids.append(url_obj.id)
                language_counts[f"EU_{predicted_lang.upper()}"] += 1
            else:
                # Predicted language but not in EU_LANGUAGES
                non_eu_url_ids.append(url_obj.id)
                language_counts[f"NON_EU_{predicted_lang.upper()}"] += 1

        # Progress report
        processed = min(i + batch_size, total_urls)
        percent = (processed / total_urls) * 100
        print(f"Progress: {processed:,}/{total_urls:,} ({percent:.1f}%)")

    db.close()

    # Print statistics
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print(f"\nTotal PENDING URLs: {total_urls:,}")
    print(f"EU URLs: {len(eu_url_ids):,} ({len(eu_url_ids)/total_urls*100:.1f}%)")
    print(f"Non-EU URLs: {len(non_eu_url_ids):,} ({len(non_eu_url_ids)/total_urls*100:.1f}%)")
    print(f"Unknown URLs: {len(unknown_url_ids):,} ({len(unknown_url_ids)/total_urls*100:.1f}%)")

    print("\n" + "-" * 60)
    print("Language Distribution (Top 20):")
    print("-" * 60)
    for lang, count in language_counts.most_common(20):
        percent = (count / total_urls) * 100
        print(f"  {lang:20s}: {count:8,} ({percent:5.1f}%)")

    # Save non-EU URL IDs to file
    output_file = "/tmp/non_eu_urls.txt"
    print(f"\nSaving {len(non_eu_url_ids):,} non-EU URL IDs to {output_file}...")
    with open(output_file, "w") as f:
        for url_id in non_eu_url_ids:
            f.write(f"{url_id}\n")

    print(f"✓ Non-EU URL IDs saved to {output_file}")
    print("\nNext steps:")
    print(f"1. Review the statistics above")
    print(f"2. Run: python scripts/mark_non_eu_urls_skipped.py")
    print(f"   to mark {len(non_eu_url_ids):,} URLs as SKIPPED")


if __name__ == "__main__":
    try:
        analyze_urls()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
