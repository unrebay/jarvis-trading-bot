#!/usr/bin/env python3
"""
Complete system diagnosis - check what's working and what's broken
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 CHECKING DEPENDENCIES")
    print("=" * 70)
    
    dependencies = {
        'telegram': 'python-telegram-bot',
        'anthropic': 'anthropic',
        'supabase': 'supabase',
        'PIL': 'pillow',
        'requests': 'requests',
        'yaml': 'PyYAML',
    }
    
    missing = []
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing.append(package)
    
    return len(missing) == 0, missing

def check_files():
    """Check if all required files exist"""
    print("\n🔍 CHECKING FILES")
    print("=" * 70)
    
    base_dir = Path("/sessions/tender-wizardly-gauss/mnt/jarvis-trading-bot")
    
    required_files = {
        "Bot entry point": "src/bot/main.py",
        "Telegram handler": "src/bot/telegram_handler.py",
        "Image handler": "src/bot/image_handler.py",
        "Chart annotator": "src/bot/chart_annotator.py",
        "Claude client": "src/bot/claude_client.py",
        "RAG search": "src/bot/rag_search.py",
        "Mentor prompt": "kb/prompts/mentor.md",
        "Image analyzer prompt": "kb/prompts/image_analyzer.md",
        "Chart annotator prompt": "kb/prompts/chart_annotator.md",
        "Environment file": ".env",
    }
    
    missing = []
    for name, path in required_files.items():
        full_path = base_dir / path
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  ✅ {name} ({size} bytes)")
        else:
            print(f"  ❌ {name} - MISSING at {path}")
            missing.append(path)
    
    return len(missing) == 0, missing

def check_env():
    """Check if environment variables are set"""
    print("\n🔍 CHECKING ENVIRONMENT")
    print("=" * 70)
    
    env_vars = {
        'TELEGRAM_BOT_TOKEN': '*..*..* (last 10 chars)',
        'ANTHROPIC_API_KEY': 'sk-ant-*..* (last 10 chars)',
        'SUPABASE_URL': 'https://*.supabase.co',
        'SUPABASE_ANON_KEY': 'eyJ0*..*',
    }
    
    missing = []
    for var, pattern in env_vars.items():
        value = os.getenv(var)
        if value:
            # Show last 10 chars only for security
            display = value[-10:] if len(value) > 10 else "***"
            print(f"  ✅ {var} = {display}")
        else:
            print(f"  ❌ {var} - NOT SET")
            missing.append(var)
    
    return len(missing) == 0, missing

def check_kb():
    """Check knowledge base integrity"""
    print("\n🔍 CHECKING KNOWLEDGE BASE")
    print("=" * 70)
    
    base_dir = Path("/sessions/tender-wizardly-gauss/mnt/jarvis-trading-bot")
    kb_dir = base_dir / "kb"
    
    # Count lessons
    lessons_dir = kb_dir / "lessons"
    lesson_count = len(list(lessons_dir.rglob("lesson_*.json")))
    print(f"  ✅ Lessons: {lesson_count}")
    
    # Count schemas
    schemas_dir = kb_dir / "schemas"
    schema_count = len(list(schemas_dir.glob("*.json")))
    print(f"  ✅ Schemas: {schema_count}")
    
    # Check metadata
    metadata_file = lessons_dir / "_metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)
        print(f"  ✅ KB Version: {metadata.get('version')}")
        print(f"  ✅ KB Last Updated: {metadata.get('last_updated')}")
    else:
        print(f"  ❌ KB Metadata missing")
    
    return True, []

def check_api_access():
    """Test basic API access"""
    print("\n🔍 CHECKING API ACCESS")
    print("=" * 70)
    
    issues = []
    
    # Check Anthropic
    try:
        from anthropic import Anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            client = Anthropic(api_key=api_key)
            # Don't make actual API call to save credits
            print("  ✅ Anthropic client initialized")
        else:
            print("  ⚠️  Anthropic API key not set")
            issues.append("ANTHROPIC_API_KEY not set")
    except Exception as e:
        print(f"  ❌ Anthropic error: {e}")
        issues.append(f"Anthropic: {e}")
    
    # Check Supabase
    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        if url and key:
            client = create_client(url, key)
            print("  ✅ Supabase client initialized")
        else:
            print("  ⚠️  Supabase credentials not set")
            issues.append("SUPABASE credentials not set")
    except Exception as e:
        print(f"  ❌ Supabase error: {e}")
        issues.append(f"Supabase: {e}")
    
    return len(issues) == 0, issues

def print_summary(all_checks):
    """Print final summary"""
    print("\n" + "=" * 70)
    print("📊 SYSTEM DIAGNOSIS SUMMARY")
    print("=" * 70)
    
    total_issues = sum(len(issues) for _, issues in all_checks.values())
    
    if total_issues == 0:
        print("\n✅ ALL SYSTEMS OPERATIONAL")
        print("\nBot is ready to use!")
    else:
        print(f"\n⚠️  FOUND {total_issues} ISSUES:")
        for check_name, (passed, issues) in all_checks.items():
            if not passed and issues:
                print(f"\n{check_name}:")
                for issue in issues:
                    print(f"  • {issue}")
    
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS:")
    print("=" * 70)
    
    issues_by_category = {}
    for check_name, (_, issues) in all_checks.items():
        if issues:
            issues_by_category[check_name] = issues
    
    if 'Dependencies' in issues_by_category:
        print("\n1. Install missing dependencies:")
        for pkg in issues_by_category['Dependencies']:
            print(f"   pip install {pkg} --break-system-packages")
    
    if 'Environment' in issues_by_category:
        print("\n2. Set environment variables in .env file:")
        print("   cp .env.example .env")
        print("   # Then edit .env with your API keys")
    
    if 'Files' in issues_by_category:
        print("\n3. Missing files - rebuild the project:")
        print("   python scripts/migrate_knowledge_base.py")
    
    print("\n" + "=" * 70)

def main():
    """Run all diagnostic checks"""
    print("\n" + "=" * 70)
    print("🔍 JARVIS SYSTEM DIAGNOSIS")
    print("=" * 70 + "\n")
    
    checks = {
        'Dependencies': check_dependencies(),
        'Files': check_files(),
        'Environment': check_env(),
        'Knowledge Base': check_kb(),
        'API Access': check_api_access(),
    }
    
    print_summary(checks)
    
    # Return exit code based on critical issues
    critical_issues = len(checks['Dependencies'][1]) + len(checks['Environment'][1])
    sys.exit(0 if critical_issues == 0 else 1)

if __name__ == "__main__":
    main()
