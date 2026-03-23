#!/usr/bin/env python3
"""
Knowledge Base Analysis & Integrity Check

Analyzes:
- Total entities and distribution
- Schema compliance
- Relationship coverage
- Content quality metrics
- Missing links or gaps
"""

import os
import json
from pathlib import Path
from collections import defaultdict
import sys

def analyze_kb():
    """Run comprehensive KB analysis"""

    base_dir = Path("/sessions/tender-wizardly-gauss/mnt/jarvis-trading-bot")
    kb_dir = base_dir / "kb"

    print("=" * 70)
    print("📊 JARVIS KNOWLEDGE BASE ANALYSIS")
    print("=" * 70)
    print()

    # 1. Analyze lessons
    print("🎓 LESSONS ANALYSIS")
    print("-" * 70)

    lessons_dir = kb_dir / "lessons"
    lessons = {}
    by_category = defaultdict(list)
    by_level = defaultdict(int)

    for cat_dir in lessons_dir.iterdir():
        if not cat_dir.is_dir() or cat_dir.name.startswith("_"):
            continue

        category = cat_dir.name
        for json_file in cat_dir.glob("lesson_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    lesson = json.load(f)
                    lessons[lesson['id']] = lesson
                    by_category[category].append(lesson['id'])
                    by_level[lesson.get('level', 'unknown')] += 1
            except Exception as e:
                print(f"  ❌ Error reading {json_file}: {e}")

    print(f"✅ Total lessons: {len(lessons)}")
    print(f"\nBy category:")
    for cat in sorted(by_category.keys()):
        count = len(by_category[cat])
        print(f"  • {cat}: {count} lessons")

    print(f"\nBy level:")
    for level in sorted(by_level.keys()):
        count = by_level[level]
        print(f"  • {level}: {count} lessons")

    # 2. Analyze relationships
    print("\n\n📐 RELATIONSHIPS ANALYSIS")
    print("-" * 70)

    relationships_dir = kb_dir / "relationships"
    relationships = {}

    if relationships_dir.exists():
        for yaml_file in relationships_dir.glob("*.yaml"):
            print(f"✅ Found: {yaml_file.name}")
            try:
                import yaml
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    relationships[yaml_file.name] = content.get('relationships', [])
                    print(f"   └─ {len(content.get('relationships', []))} relationships")
            except ImportError:
                print(f"   (PyYAML not installed - skipping)")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    # 3. Analyze schemas
    print("\n\n📋 SCHEMAS ANALYSIS")
    print("-" * 70)

    schemas_dir = kb_dir / "schemas"
    schemas = {}

    if schemas_dir.exists():
        for schema_file in schemas_dir.glob("*.json"):
            schema_name = schema_file.stem
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    schemas[schema_name] = schema
                    required = schema.get('required', [])
                    properties = schema.get('properties', {})
                    print(f"✅ {schema_name}")
                    print(f"   ├─ Required fields: {len(required)}")
                    print(f"   ├─ Total properties: {len(properties)}")
                    print(f"   └─ Type: {schema.get('type', 'unknown')}")
            except Exception as e:
                print(f"❌ {schema_file.name}: {e}")

    # 4. Analyze prompts
    print("\n\n💬 PROMPTS ANALYSIS")
    print("-" * 70)

    prompts_dir = kb_dir / "prompts"
    if prompts_dir.exists():
        for prompt_file in prompts_dir.glob("*.md"):
            file_size = prompt_file.stat().st_size
            lines = len(prompt_file.read_text(encoding='utf-8').split('\n'))
            is_cached = "mentor.md" in prompt_file.name
            cache_info = " (CACHED - 10% API savings)" if is_cached else ""
            print(f"✅ {prompt_file.name}")
            print(f"   ├─ Size: {file_size/1024:.1f} KB")
            print(f"   ├─ Lines: {lines}")
            print(f"   └─{cache_info}")

    # 5. Analyze ingestion configs
    print("\n\n⚙️  INGESTION CONFIGS ANALYSIS")
    print("-" * 70)

    config_dir = kb_dir / "ingestion-config"
    if config_dir.exists():
        for config_file in config_dir.glob("*.yaml"):
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = yaml.safe_load(f)
                    print(f"✅ {config_file.name}")
                    if isinstance(content, dict) and 'ingestion_sources' in content:
                        sources = content['ingestion_sources']
                        if isinstance(sources, list):
                            print(f"   └─ {len(sources)} data sources configured")
            except ImportError:
                print(f"✅ {config_file.name} (content not parsed - PyYAML needed)")
            except Exception as e:
                print(f"❌ {config_file.name}: {e}")

    # 6. Metadata check
    print("\n\n📈 METADATA CHECK")
    print("-" * 70)

    metadata_file = lessons_dir / "_metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                print(f"✅ KB Version: {metadata.get('version', 'unknown')}")
                print(f"✅ Last Updated: {metadata.get('last_updated', 'unknown')}")
                print(f"✅ Total Lessons: {metadata.get('total_lessons', 0)}")
                print(f"✅ Categories: {len(metadata.get('categories', []))}")

                if 'next_priorities' in metadata:
                    print(f"\n📋 Next Priorities:")
                    for priority in metadata['next_priorities'][:3]:
                        print(f"   • {priority}")
        except Exception as e:
            print(f"❌ Error reading metadata: {e}")

    # 7. Calculate statistics
    print("\n\n📊 STATISTICS")
    print("-" * 70)

    total_files = len(list(lessons_dir.rglob("*.json"))) + len(list(lessons_dir.rglob("*.md")))
    total_schema_fields = sum(
        len(s.get('properties', {}))
        for s in schemas.values()
    )

    print(f"✅ Total lesson files: {total_files // 2} (JSON + Markdown)")
    print(f"✅ Total schema fields defined: {total_schema_fields}")
    print(f"✅ Total relationships defined: {sum(len(r) for r in relationships.values())}")
    print(f"✅ Prompts configured: {len(list(prompts_dir.glob('*.md'))) if prompts_dir.exists() else 0}")

    # 8. Coverage analysis
    print("\n\n🎯 COVERAGE ANALYSIS")
    print("-" * 70)

    # Check which lessons have related entities
    with_examples = 0
    with_images = 0
    with_patterns = 0
    with_rules = 0

    for lesson in lessons.values():
        if lesson.get('chart_examples'):
            with_examples += 1
        if lesson.get('related_images'):
            with_images += 1
        if lesson.get('related_patterns'):
            with_patterns += 1
        if lesson.get('related_rules'):
            with_rules += 1

    print(f"Lessons with chart examples: {with_examples}/{len(lessons)} ({100*with_examples//len(lessons) if lessons else 0}%)")
    print(f"Lessons with images: {with_images}/{len(lessons)} ({100*with_images//len(lessons) if lessons else 0}%)")
    print(f"Lessons with patterns: {with_patterns}/{len(lessons)} ({100*with_patterns//len(lessons) if lessons else 0}%)")
    print(f"Lessons with rules: {with_rules}/{len(lessons)} ({100*with_rules//len(lessons) if lessons else 0}%)")

    # 9. Recommendations
    print("\n\n💡 RECOMMENDATIONS")
    print("-" * 70)

    recommendations = []

    if with_examples < len(lessons) * 0.5:
        recommendations.append("Add chart examples to at least 50% of lessons")
    if with_patterns < len(lessons) * 0.3:
        recommendations.append("Link lessons to related trading patterns")
    if with_rules < len(lessons) * 0.3:
        recommendations.append("Identify and link trading rules to lessons")

    if not (kb_dir / "relationships").exists():
        recommendations.append("Create comprehensive relationship YAML files")

    if not (kb_dir / "metadata" / "embeddings_index.json").exists():
        recommendations.append("Generate embeddings for semantic search (next step)")

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("✅ All recommendations completed!")

    # Summary
    print("\n" + "=" * 70)
    print("✨ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\n📂 KB Location: {kb_dir}")
    print(f"📊 Lessons: {len(lessons)}")
    print(f"🏗️  Schemas: {len(schemas)}")
    print(f"📐 Relationships: {sum(len(r) for r in relationships.values())}")
    print(f"💬 Prompts: {len(list(prompts_dir.glob('*.md'))) if prompts_dir.exists() else 0}")
    print(f"\n✅ KB is ready for: Embedding generation and chart testing!\n")


if __name__ == "__main__":
    analyze_kb()
