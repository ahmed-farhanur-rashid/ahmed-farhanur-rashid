import os
import re
import sys
import urllib.request
import json

USERNAME = "ahmed-farhanur-rashid"
README_PATH = "README.md"
START_MARKER = "<!--STACK:START-->"
END_MARKER = "<!--STACK:END-->"
TOP_N = 10

TOKEN = os.environ.get("GITHUB_TOKEN", "")

SKILL_ICON_SLUGS = {
    "Python": "py",
    "C++": "cpp",
    "C": "c",
    "Java": "java",
    "Kotlin": "kotlin",
    "Rust": "rust",
    "JavaScript": "js",
    "TypeScript": "ts",
    "HTML": "html",
    "CSS": "css",
    "Shell": "bash",
    "Dockerfile": "docker",
    "Go": "go",
    "C#": "cs",
    "Swift": "swift",
    "PHP": "php",
    "Ruby": "ruby",
    "Vue": "vue",
    "CMake": "cmake",
    "R": "r",
    "Lua": "lua",
    "Scala": "scala",
    "Dart": "dart",
    "Haskell": "haskell",
}
# skillicons.dev has no dedicated Jupyter Notebook icon, so it never
# renders as an icon regardless of ranking. It is excluded from the
# byte-based ranking entirely rather than guessing a correction factor
# with no ground truth to calibrate against - notebook JSON bloat
# (embedded outputs, images) varies too much per-repo to fake a number.
EXCLUDED_FROM_RANKING = {"Jupyter Notebook"}


def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_all_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}"
        batch = api_get(url)
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return [r for r in repos if not r.get("fork")]


def aggregate_languages(repos):
    totals = {}
    for r in repos:
        url = r["languages_url"]
        try:
            langs = api_get(url)
        except Exception:
            continue
        for lang, byte_count in langs.items():
            if lang in EXCLUDED_FROM_RANKING:
                continue
            totals[lang] = totals.get(lang, 0) + byte_count
    return totals


def build_block(totals):
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [(lang, count) for lang, count in ranked if count > 0]

    slugs = []
    for lang, _ in ranked:
        slug = SKILL_ICON_SLUGS.get(lang)
        if slug and slug not in slugs:
            slugs.append(slug)
        if len(slugs) >= TOP_N:
            break

    if not slugs:
        return "<sub>Stack detection unavailable.</sub>"

    icon_list = ",".join(slugs)
    return (
        '<p align="left">\n'
        f'  <img src="https://skillicons.dev/icons?i={icon_list}" alt="stack" />\n'
        "</p>"
    )


def update_readme(block):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{block}\n{END_MARKER}"

    if not pattern.search(content):
        print("Markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    new_content = pattern.sub(replacement, content)

    if new_content == content:
        print("No changes needed.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("README updated.")
    return True


if __name__ == "__main__":
    repos = get_all_repos()
    totals = aggregate_languages(repos)
    block = build_block(totals)
    update_readme(block)
