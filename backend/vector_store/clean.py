import json 
import os 
import sys
from pathlib import Path

# Configure stdout to use UTF-8 encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

base_dir = Path(__file__).resolve().parent

quran_json = base_dir / "backend" / "vector_store" / "storage" / "quran" / "new_quran_translation_ru_en.json"
tafsir_json = base_dir / "backend" / "vector_store" / "storage" / "tafsir" / "most_final_final_db_with_ru.json"

keys_to_remove = [
    "As-Saadi_tafsir_source",
    "Ibni_kathir_quran_tafsir",
    "Ibni_kathir_tafsir_source",
    "abu_Adil_tafsir", 
    "abu_Adil_tafsir_source",
    "As_Saadi_Tafseer",
    "ru_translation"
]

files_to_clean = [
    ("Quran JSON", quran_json),
    ("Tafsir JSON", tafsir_json)
]

for label, file_path in files_to_clean:
    if not file_path.exists():
        print(f"⚠ File not found at path: {file_path}")
        continue

    print(f"🔄 Cleaning {label}: {file_path.name} ...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        removed_count = 0
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Check both 'meta_data' and 'metadata' dictionaries
                    for meta_key in ['meta_data', 'metadata']:
                        if meta_key in item and isinstance(item[meta_key], dict):
                            for k in keys_to_remove:
                                if item[meta_key].pop(k, None) is not None:
                                    removed_count += 1
                    # Also pop top level keys if present
                    for k in keys_to_remove:
                        if item.pop(k, None) is not None:
                            removed_count += 1

        print(f"   Removed {removed_count} unneeded metadata fields.")
        print(f"💾 Saving updated {label} ...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Successfully updated {file_path.name}")

    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")

print("\n🎉 Cleaning finished.")


