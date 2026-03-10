"""
Fetches language byte counts across all non-forked public repos for GH_USERNAME,
computes percentages, and rewrites the <!-- LANGUAGES_START --> ... <!-- LANGUAGES_END -->
block inside README.md with monochrome progress-bar badges.
"""

import os
import re
import requests

USERNAME = os.environ["GH_USERNAME"]
TOKEN    = os.environ["GH_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# Languages to exclude from the display (markup, config, etc.)
EXCLUDE = {
    "HTML", "CSS", "Makefile", "CMake", "Shell",
    "Batchfile", "PowerShell", "Dockerfile", "YAML",
    "JSON", "XML", "Markdown", "Text",
}

# Max languages to show
TOP_N = 8


def get_repos():
    repos, page = [], 1
    while True:
        r = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "type": "owner"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return [r for r in repos if not r["fork"]]


def get_languages(repo_name):
    r = requests.get(
        f"https://api.github.com/repos/{USERNAME}/{repo_name}/languages",
        headers=HEADERS,
    )
    r.raise_for_status()
    return r.json()


def build_bar(percent: float, width: int = 28) -> str:
    """Return a unicode block progress bar."""
    filled = round(percent / 100 * width)
    return "█" * filled + "░" * (width - filled)


def build_language_block(lang_data: dict) -> str:
    total = sum(lang_data.values())
    if total == 0:
        return "<!-- no language data -->"

    lines = ["<!-- LANGUAGES_START -->"]
    lines.append("")
    lines.append("### Languages")
    lines.append("")
    lines.append("```")
    lines.append(f"{'Language':<18} {'Bar':<30} {'%':>6}   {'Bytes':>10}")
    lines.append("─" * 70)

    for lang, count in lang_data.items():
        pct = count / total * 100
        bar = build_bar(pct)
        lines.append(f"{lang:<18} {bar:<30} {pct:>5.1f}%   {count:>10,}")

    lines.append("```")
    lines.append("")
    lines.append(
        f'<sub>Pulled live from my repos via GitHub Actions · '
        f'last updated by workflow run</sub>'
    )
    lines.append("")
    lines.append("<!-- LANGUAGES_END -->")
    return "\n".join(lines)


def update_readme(block: str):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- LANGUAGES_START -->.*?<!-- LANGUAGES_END -->"
    new_content = re.sub(pattern, block, content, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("README.md updated.")


def main():
    print(f"Fetching repos for {USERNAME}...")
    repos = get_repos()
    print(f"Found {len(repos)} non-forked repos.")

    totals: dict[str, int] = {}
    for repo in repos:
        langs = get_languages(repo["name"])
        for lang, count in langs.items():
            if lang not in EXCLUDE:
                totals[lang] = totals.get(lang, 0) + count

    # Sort by byte count descending, take top N
    sorted_langs = dict(
        sorted(totals.items(), key=lambda x: x[1], reverse=True)[:TOP_N]
    )

    print("Top languages:", sorted_langs)
    block = build_language_block(sorted_langs)
    update_readme(block)


if __name__ == "__main__":
    main()
