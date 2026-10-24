import re
import hashlib
import unicodedata
from typing import Literal

def normalize_text(text: str) -> str:
    """Normalize whitespace and unicode lookalikes."""
    if not text:
        return ""
    # NFKC normalizes unicode characters to standard equivalents
    text = unicodedata.normalize("NFKC", text)
    # Collapse multiple whitespaces
    return " ".join(text.strip().split())

def normalize_email(email: str, strip_gmail_tags: bool = True) -> str:
    """
    Normalize email:
    - trim and lowercase
    - unicode normalization
    - for gmail.com / googlemail.com: remove dots in username and strip +tags
    """
    if not email:
        return ""
    email = normalize_text(email).lower()
    if "@" not in email:
        return email
    
    parts = email.split("@", 1)
    user, domain = parts[0], parts[1]
    
    if strip_gmail_tags and domain in ("gmail.com", "googlemail.com"):
        user = user.split("+", 1)[0]
        user = user.replace(".", "")
    elif "+" in user:
        # Standard tag stripping if needed
        user = user.split("+", 1)[0]
        
    return f"{user}@{domain}"

def normalize_phone(phone: str) -> str:
    """
    Normalize phone number towards E.164-compatible digit string:
    - preserves leading '+' if present
    - removes dashes, spaces, parentheses, dots
    """
    if not phone:
        return ""
    phone = normalize_text(phone)
    has_plus = phone.startswith("+")
    digits = re.sub(r"\D", "", phone)
    if has_plus:
        return f"+{digits}"
    return digits

def generate_hashes(value: str) -> dict[str, str]:
    """Generate MD5, SHA-1, and SHA-256 for a normalized string value."""
    if not value:
        return {}
    data = value.encode("utf-8")
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }

def is_partial_mask(text: str) -> bool:
    """
    Detect whether a value represents a masked identifier:
    e.g. 'j***@gmail.com', '****1234', 'a***i@yahoo.com', '***-***-1234'.
    """
    if not text:
        return False
    return "*" in text or "•" in text or "x" * 3 in text.lower()

def matches_mask(masked: str, candidate: str) -> bool:
    """
    Check if a candidate identifier matches a masked pattern.
    e.g. 'j***@gmail.com' matches 'john.doe@gmail.com'
    """
    if not masked or not candidate:
        return False
    if not is_partial_mask(masked):
        return masked.lower() == candidate.lower()
    
    # Escape special regex chars except *
    pattern = "^"
    for char in masked:
        if char in ("*", "•"):
            pattern += ".*"
        else:
            pattern += re.escape(char)
    pattern += "$"
    
    try:
        return bool(re.match(pattern, candidate, re.IGNORECASE))
    except re.error:
        return False

def generate_all_variants(identifier: str, id_type: Literal["email", "phone", "user_id", "name", "other"]) -> set[str]:
    """
    Precompute all matching variants: raw, normalized, case variations, and cryptographic hashes.
    """
    variants: set[str] = set()
    if not identifier:
        return variants
        
    raw = identifier.strip()
    variants.add(raw)
    variants.add(raw.lower())
    variants.add(raw.upper())
    
    if id_type == "email":
        norm = normalize_email(raw)
        variants.add(norm)
        # Add hashes of normalized and raw
        for h in generate_hashes(norm).values():
            variants.add(h)
        for h in generate_hashes(raw.lower()).values():
            variants.add(h)
    elif id_type == "phone":
        norm = normalize_phone(raw)
        variants.add(norm)
        # Also add digit-only variant without '+'
        digits = norm.lstrip("+")
        variants.add(digits)
    elif id_type in ("user_id", "other"):
        norm = normalize_text(raw).lower()
        variants.add(norm)
        for h in generate_hashes(norm).values():
            variants.add(h)
            
    return {v for v in variants if v}
