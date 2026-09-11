"""Conservative syntax guard; passing does not verify a source's authenticity."""
import re


def valid_source_reference(value):
    if not isinstance(value, str) or value != value.strip() or len(value.strip()) < 8:
        return False
    normalized = re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()
    placeholders = {'real source or evidence here', 'your verified evidence source',
                    'todo', 'tbd', 'test', 'placeholder', 'n a', 'na', 'none', 'null',
                    'unknown', 'source', 'evidence', 'not available'}
    return (normalized not in placeholders
            and not re.search(r'\b(todo|tbd|placeholder)\b', normalized)
            and not normalized.startswith(('test only', 'real source or evidence here',
                                           'your verified evidence source'))
            and len(set(normalized.replace(' ', ''))) >= 4)
