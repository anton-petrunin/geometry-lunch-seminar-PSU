 #!/usr/bin/env python3

from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, quote
import html
import re
import shutil

ROOT = Path(".")
INDEX = ROOT / "index.html"


def source_url(text):
    """Read the original URL stored by SingleFile."""
    m = re.search(
        r"Page saved with SingleFile.*?\burl:\s*(\S+)",
        text[:200000],
        re.I | re.S,
    )
    if m:
        return html.unescape(m.group(1).strip())

    # Fallback: canonical URL, if present
    m = re.search(
        r'<link[^>]+rel=["\'][^"\']*canonical[^"\']*["\'][^>]+href=["\']([^"\']+)',
        text[:200000],
        re.I,
    )
    if m:
        return html.unescape(m.group(1))

    return None


def normalize(url):
    """Ignore #fragment when matching pages."""
    p = urlsplit(html.unescape(url))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                       p.path, p.query, ""))


# Build: original URL -> local filename
url_to_file = {}

for path in ROOT.glob("*.html"):
    if path.name == "index.html":
        continue

    text = path.read_text(encoding="utf-8", errors="replace")
    url = source_url(text)

    if not url:
        print(f"NO URL: {path.name}")
        continue

    key = normalize(url)

    if key in url_to_file:
        print(f"DUPLICATE URL:")
        print(f"  {url_to_file[key]}")
        print(f"  {path.name}")
        continue

    url_to_file[key] = path.name

print(f"Found {len(url_to_file)} saved pages.")

text = INDEX.read_text(encoding="utf-8", errors="replace")
base_url = source_url(text)

if not base_url:
    raise SystemExit("Cannot find original URL in index.html")

count = 0

# Change href only in <a ...> tags.
pattern = re.compile(
    r'(<a\b[^>]*?\bhref\s*=\s*)(["\'])(.*?)(\2)',
    re.I | re.S,
)


def replace_link(m):
    global count

    prefix, quote_char, href, _ = m.groups()

    raw = html.unescape(href)

    # Leave mailto:, javascript:, etc. alone
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) \
            and not raw.startswith(("http:", "https:")):
        return m.group(0)

    absolute = urljoin(base_url, raw)
    parts = urlsplit(absolute)
    key = normalize(absolute)

    if key not in url_to_file:
        return m.group(0)

    local = quote(url_to_file[key])
    if parts.fragment:
        local += "#" + quote(parts.fragment)

    count += 1
    return prefix + quote_char + local + quote_char


new_text = pattern.sub(replace_link, text)

backup = INDEX.with_suffix(".html.bak")
if not backup.exists():
    shutil.copy2(INDEX, backup)

INDEX.write_text(new_text, encoding="utf-8")

print(f"Rewrote {count} links in index.html.")
print(f"Original saved as {backup.name}.")
