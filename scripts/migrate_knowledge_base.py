#!/usr/bin/env python3
"""
Migrate knowledge from knowledge_raw/ to kb/lessons/ with proper structure

Workflow:
1. Read markdown files from knowledge_raw/
2. Create lesson entities with metadata
3. Organize by category in kb/lessons/
4. Generate indices and relationships
5. Create KB metadata
"""

import os
import json
from pathlib import Path
from datetime import datetime
import hashlib
from typing import Dict, List, Any
import re

# Categories mapping
CATEGORIES = {
    "beginners": "beginners",
    "gold-mechanics": "gold-mechanics",
    "market-mechanics": "market-mechanics",
    "principles": "principles",
    "psychology": "psychology",
    "risk-management": "risk-management",
    "structure-and-liquidity": "structure-and-liquidity",
    "tda-and-entry-models": "tda-and-entry-models",
}

LEVEL_MAP = {
    "beginners": "beginner",
    "principles": "intermediate",
    "market-mechanics": "intermediate",
    "structure-and-liquidity": "intermediate",
    "tda-and-entry-models": "advanced",
    "gold-mechanics": "advanced",
    "psychology": "intermediate",
    "risk-management": "intermediate",
}


def generate_lesson_id(title: str, category: str) -> str:
    """Generate unique lesson ID from title"""
    clean_title = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
    return f"lesson_{category}_{clean_title}"[:50]


def extract_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from markdown content"""
    lines = content.split('\n')

    # Extract first heading as title
    title = None
    for line in lines:
        if line.startswith('# '):
            title = line[2:].strip()
            break

    # Count words for reading time
    word_count = len(content.split())
    reading_time = max(1, word_count // 200)  # ~200 words per minute

    # Extract learning objectives (if marked with specific patterns)
    objectives = []
    for line in lines:
        if 'после' in line.lower() and 'ты' in line.lower():
            objectives.append(line.strip())

    # Find key terms (words in backticks or **bold**)
    terms = re.findall(r'`([^`]+)`', content)

    return {
        "title": title,
        "word_count": word_count,
        "reading_time": reading_time,
        "objectives": objectives[:3],  # Max 3
        "key_terms": list(set(terms))[:5],  # Max 5 unique
    }


def create_lesson_entity(
    file_path: Path,
    category: str,
    metadata: Dict[str, Any],
    content: str
) -> Dict[str, Any]:
    """Create lesson entity from markdown file"""

    title = metadata.get("title") or file_path.stem.replace("-", " ").title()
    lesson_id = generate_lesson_id(title, category)

    return {
        "id": lesson_id,
        "title": title,
        "description": f"Lesson on {metadata.get('title', 'trading concepts')}",
        "category": category,
        "level": LEVEL_MAP.get(category, "intermediate"),
        "content": content,
        "learning_objectives": metadata.get("objectives", []),
        "related_topics": [],  # Will be filled by relationship analysis
        "related_rules": [],
        "related_patterns": [],
        "chart_examples": [],
        "mistake_cases": [],
        "estimated_read_time": metadata.get("reading_time", 5),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "author": "JARVIS Knowledge Base",
        "tags": [category] + metadata.get("key_terms", []),
        "source_file": str(file_path),
        "file_hash": hashlib.sha256(content.encode()).hexdigest()[:12],
        "status": "active"
    }


def migrate_knowledge_base():
    """Main migration function"""

    base_dir = Path("/sessions/tender-wizardly-gauss/mnt/jarvis-trading-bot")
    source_dir = base_dir / "knowledge_raw"
    target_dir = base_dir / "kb" / "lessons"

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Statistics
    stats = {
        "total_files": 0,
        "migrated": 0,
        "errors": 0,
        "by_category": {},
        "lessons": []
    }

    print("🔄 Starting Knowledge Base Migration...\n")

    # Iterate through categories
    for category_dir in source_dir.iterdir():
        if not category_dir.is_dir():
            continue

        category = category_dir.name
        if category not in CATEGORIES:
            print(f"⚠️  Unknown category: {category}")
            continue

        print(f"📂 Processing category: {category}")
        stats["by_category"][category] = {"total": 0, "migrated": 0}

        # Create category directory in target
        category_target = target_dir / category
        category_target.mkdir(parents=True, exist_ok=True)

        # Process files
        for md_file in sorted(category_dir.glob("*.md")):
            stats["total_files"] += 1
            stats["by_category"][category]["total"] += 1

            try:
                # Read content
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract metadata
                metadata = extract_metadata(content)

                # Create lesson entity
                lesson = create_lesson_entity(md_file, category, metadata, content)

                # Save to JSON
                lesson_json_path = category_target / f"{lesson['id']}.json"
                with open(lesson_json_path, 'w', encoding='utf-8') as f:
                    json.dump(lesson, f, ensure_ascii=False, indent=2)

                # Also save markdown
                md_target = category_target / f"{lesson['id']}.md"
                with open(md_target, 'w', encoding='utf-8') as f:
                    f.write(content)

                stats["migrated"] += 1
                stats["by_category"][category]["migrated"] += 1
                stats["lessons"].append(lesson)

                print(f"  ✅ {md_file.name}")

            except Exception as e:
                stats["errors"] += 1
                print(f"  ❌ {md_file.name}: {str(e)}")

        print()

    # Create category indices
    print("📑 Creating category indices...")
    for category in CATEGORIES.keys():
        category_target = target_dir / category
        if not category_target.exists():
            continue

        # List all lessons in category
        lessons_in_category = [
            l for l in stats["lessons"]
            if l["category"] == category
        ]

        index = {
            "category": category,
            "total_lessons": len(lessons_in_category),
            "lessons": [
                {
                    "id": l["id"],
                    "title": l["title"],
                    "level": l["level"],
                    "reading_time": l["estimated_read_time"]
                }
                for l in lessons_in_category
            ],
            "created_at": datetime.now().isoformat()
        }

        index_path = category_target / "index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"  ✅ {category}: {len(lessons_in_category)} lessons")

    # Create main KB metadata
    print("\n📊 Creating KB metadata...")

    kb_metadata = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "total_lessons": len(stats["lessons"]),
        "total_patterns": 0,
        "total_rules": 0,
        "total_topics": 0,
        "total_terms": 0,
        "total_charts": 0,
        "total_images": 0,
        "total_videos": 0,
        "embeddings_indexed": 0,
        "categories": list(CATEGORIES.values()),
        "sources": [
            {
                "name": "knowledge_raw migration",
                "type": "markdown",
                "count": len(stats["lessons"]),
                "last_imported": datetime.now().isoformat()
            }
        ],
        "completeness_metrics": {
            "lessons_with_examples": 0,
            "lessons_with_images": 0,
            "patterns_documented": 0,
            "embeddings_coverage": 0
        },
        "quality_notes": "Initial migration from knowledge_raw/. Ready for enrichment.",
        "next_priorities": [
            "Create pattern entities from lesson content",
            "Identify and extract trading rules",
            "Add chart examples to lessons",
            "Generate embeddings for semantic search",
            "Build relationship graph"
        ]
    }

    metadata_path = target_dir / "_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(kb_metadata, f, ensure_ascii=False, indent=2)

    print("  ✅ KB metadata created")

    # Print summary
    print("\n" + "="*60)
    print("📈 MIGRATION SUMMARY")
    print("="*60)
    print(f"Total files processed: {stats['total_files']}")
    print(f"Successfully migrated: {stats['migrated']}")
    print(f"Errors: {stats['errors']}")
    print(f"\nBy category:")
    for cat, counts in stats["by_category"].items():
        if counts["total"] > 0:
            print(f"  {cat}: {counts['migrated']}/{counts['total']} ✅")

    print(f"\n✨ Knowledge base migrated to: {target_dir}")
    print(f"📍 Metadata at: {metadata_path}")

    return stats


if __name__ == "__main__":
    migrate_knowledge_base()
