import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Iterator, Tuple

ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

def read_text_safe(path: Path) -> str:
    """Read a text file trying multiple common encodings."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
            
    # Final fallback with replace
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Load CSV into list of dictionaries with encoding fallback."""
    if not path.exists():
        return []
        
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                reader = csv.DictReader(f)
                return list(reader)
        except (UnicodeDecodeError, UnicodeError):
            continue
            
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_json_safe(path: Path) -> Any:
    """Load JSON from a file with encoding fallback."""
    text = read_text_safe(path)
    return json.loads(text)

def parse_sql_inserts(sql_text: str) -> List[Dict[str, Any]]:
    """
    Parse SQLite INSERT statements of the form:
    INSERT INTO table_name VALUES ('res_id', 'origin', 'collection', '{"json":...}', 'updated_at');
    Returns list of dicts: {'table': table, 'resource_id': ..., 'origin_system': ..., 'collection_name': ..., 'record_json': dict, 'updated_at': ...}
    """
    records = []
    # Pattern for insert into table VALUES ('...', '...', '...', '{...}', '...')
    # Universal schema: resource_id, origin_system, collection_name, record_json, updated_at
    insert_pattern = re.compile(
        r"INSERT\s+INTO\s+([`\"]?\w+[`\"]?)\s+VALUES\s*\((.*?)\);",
        re.DOTALL | re.IGNORECASE
    )
    
    for match in insert_pattern.finditer(sql_text):
        table_name = match.group(1).strip("`\"")
        vals_str = match.group(2).strip()
        
        # Split SQL values taking into account quotes and json strings
        tokens = []
        in_quote = False
        quote_char = ""
        current = []
        escaped = False
        
        for char in vals_str:
            if escaped:
                current.append(char)
                escaped = False
            elif char == "\\":
                current.append(char)
                escaped = True
            elif char in ("'", '"'):
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif quote_char == char:
                    in_quote = False
                current.append(char)
            elif char == "," and not in_quote:
                tokens.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            tokens.append("".join(current).strip())
            
        if len(tokens) >= 5:
            res_id = tokens[0].strip("'\"")
            origin = tokens[1].strip("'\"")
            collection = tokens[2].strip("'\"")
            raw_json = tokens[3].strip()
            if (raw_json.startswith("'") and raw_json.endswith("'")) or (raw_json.startswith('"') and raw_json.endswith('"')):
                raw_json = raw_json[1:-1]
            raw_json = raw_json.replace("''", "'").replace('\\"', '"')
            
            parsed_json = {}
            try:
                parsed_json = json.loads(raw_json)
            except Exception:
                pass
                
            updated_at = tokens[4].strip("'\"")
            
            records.append({
                "table": table_name,
                "resource_id": res_id,
                "origin_system": origin,
                "collection_name": collection,
                "record": parsed_json,
                "raw_json": raw_json,
                "updated_at": updated_at
            })
            
    return records
