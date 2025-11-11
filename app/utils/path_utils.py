"""Path and string utility functions"""
import re


def generate_slug(text: str) -> str:
    """Generate a URL-friendly slug from text"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def normalize_path(path: str) -> str:
    """Normalize path separators and remove leading/trailing slashes"""
    if not path:
        return ""
    path = path.replace('\\', '/')
    path = path.strip('/')
    return path

