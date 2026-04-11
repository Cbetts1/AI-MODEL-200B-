"""aura/tools/website_generator.py — Static website scaffolder.

Generates a complete static website (HTML + CSS + JavaScript) from a
description.  Output is saved to ``~/.aura/websites/<name>/`` so it can
be opened directly in a browser or deployed to any static host (GitHub Pages,
Netlify, Vercel, S3, etc.).

Usage
-----
    /tool website_generator help
    /tool website_generator create name="MyPortfolio" type=portfolio \\
        title="Jane Smith — Developer" color="#4f46e5"
    /tool website_generator create name="CafeMenu" type=landing \\
        title="Blue Parrot Café" tagline="Coffee with soul"
    /tool website_generator list
    /tool website_generator show MyPortfolio

Site types
----------
  portfolio  — Personal portfolio / CV page with sections for About, Skills,
               Projects, and Contact
  landing    — Marketing landing page with hero, features, and CTA sections
  docs       — Simple documentation / README page
  blog       — Minimal blog / article page
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Dict

from .registry import Tool

_WEBSITES_DIR = Path.home() / ".aura" / "websites"

# ── HTML templates ─────────────────────────────────────────────────────────────

_BASE_CSS = """\
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --primary: {color};
  --bg: #0f172a;
  --surface: #1e293b;
  --text: #f1f5f9;
  --muted: #94a3b8;
  --radius: 0.75rem;
  --font: 'Inter', system-ui, sans-serif;
}}
body {{ background: var(--bg); color: var(--text); font-family: var(--font);
       line-height: 1.7; min-height: 100vh; }}
a {{ color: var(--primary); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }}
header {{ background: var(--surface); padding: 1.5rem 0; border-bottom: 1px solid #334155; }}
header h1 {{ font-size: 1.75rem; color: var(--primary); }}
header p {{ color: var(--muted); margin-top: 0.25rem; }}
nav {{ margin-top: 0.75rem; }}
nav a {{ margin-right: 1.5rem; color: var(--muted); font-size: 0.9rem; }}
nav a:hover {{ color: var(--text); }}
.hero {{ padding: 5rem 0 3rem; text-align: center; }}
.hero h2 {{ font-size: 3rem; font-weight: 800; line-height: 1.2; }}
.hero h2 span {{ color: var(--primary); }}
.hero p {{ color: var(--muted); font-size: 1.25rem; margin: 1.5rem auto; max-width: 600px; }}
.btn {{ display: inline-block; background: var(--primary); color: #fff;
        padding: 0.75rem 2rem; border-radius: var(--radius); font-weight: 600;
        transition: opacity 0.2s; }}
.btn:hover {{ opacity: 0.85; text-decoration: none; }}
section {{ padding: 4rem 0; }}
section h3 {{ font-size: 1.75rem; margin-bottom: 2rem; }}
.grid {{ display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }}
.card {{ background: var(--surface); border-radius: var(--radius); padding: 1.5rem;
         border: 1px solid #334155; }}
.card h4 {{ color: var(--primary); margin-bottom: 0.5rem; }}
.card p {{ color: var(--muted); font-size: 0.95rem; }}
footer {{ border-top: 1px solid #334155; padding: 2rem 0; text-align: center;
          color: var(--muted); font-size: 0.85rem; }}
"""

_PORTFOLIO_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header>
    <div class="container">
      <h1>{title}</h1>
      <p>{tagline}</p>
      <nav>
        <a href="#about">About</a>
        <a href="#skills">Skills</a>
        <a href="#projects">Projects</a>
        <a href="#contact">Contact</a>
      </nav>
    </div>
  </header>

  <section id="about">
    <div class="container">
      <h3>👋 About Me</h3>
      <p>{about}</p>
    </div>
  </section>

  <section id="skills">
    <div class="container">
      <h3>🛠 Skills</h3>
      <div class="grid">
        {skills_cards}
      </div>
    </div>
  </section>

  <section id="projects">
    <div class="container">
      <h3>🚀 Projects</h3>
      <div class="grid">
        <div class="card">
          <h4>Project One</h4>
          <p>Describe your first project here — what it does and the tech stack used.</p>
        </div>
        <div class="card">
          <h4>Project Two</h4>
          <p>Describe your second project here — what problem it solves and your role.</p>
        </div>
        <div class="card">
          <h4>Project Three</h4>
          <p>Describe your third project here — any metrics, outcomes, or links.</p>
        </div>
      </div>
    </div>
  </section>

  <section id="contact">
    <div class="container">
      <h3>📬 Contact</h3>
      <p>{contact}</p>
    </div>
  </section>

  <footer>
    <div class="container">
      <p>Built with ❤️ using AURA — AI Unified Reasoning Architecture</p>
    </div>
  </footer>
</body>
</html>
"""

_LANDING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header>
    <div class="container">
      <h1>{title}</h1>
    </div>
  </header>

  <div class="hero">
    <div class="container">
      <h2>{title_split}</h2>
      <p>{tagline}</p>
      <a href="#features" class="btn">Learn More</a>
    </div>
  </div>

  <section id="features">
    <div class="container">
      <h3>✨ Features</h3>
      <div class="grid">
        <div class="card">
          <h4>Feature One</h4>
          <p>Describe the first key feature of your product or service here.</p>
        </div>
        <div class="card">
          <h4>Feature Two</h4>
          <p>Describe the second key feature — focus on the user benefit.</p>
        </div>
        <div class="card">
          <h4>Feature Three</h4>
          <p>Describe the third key feature — keep it concise and compelling.</p>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="container" style="text-align:center; padding: 3rem 0;">
      <h3>Ready to get started?</h3>
      <p style="color: var(--muted); margin: 1rem 0;">
        {contact}
      </p>
      <a href="mailto:{email}" class="btn">Get In Touch</a>
    </div>
  </section>

  <footer>
    <div class="container">
      <p>© 2025 {title} · Built with AURA</p>
    </div>
  </footer>
</body>
</html>
"""


def _parse_kv(args: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    try:
        tokens = shlex.split(args)
    except ValueError:
        tokens = args.split()
    for token in tokens:
        if "=" in token:
            k, _, v = token.partition("=")
            result[k.strip().lower()] = v.strip().strip('"').strip("'")
    return result


def _skill_cards(skills_raw: str) -> str:
    skills = [s.strip() for s in re.split(r"[,;]", skills_raw) if s.strip()]
    if not skills:
        skills = ["Add your skills here"]
    return "\n        ".join(
        f'<div class="card"><h4>{s}</h4><p>Proficient</p></div>'
        for s in skills
    )


class WebsiteGeneratorTool(Tool):
    """Scaffold a complete static website (HTML + CSS) from a description."""

    name = "website_generator"
    description = (
        "Generate a static website.  "
        "Usage: /tool website_generator create name=\"MySite\" type=portfolio "
        "title=\"My Name\" tagline=\"Tagline\" color=\"#4f46e5\""
    )

    def run(self, args: str) -> str:
        parts = args.strip().split(None, 1)
        if not parts or parts[0].lower() in ("help", ""):
            return self._help()

        subcmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if subcmd == "create":
            return self._create(rest)
        if subcmd == "list":
            return self._list()
        if subcmd == "show":
            return self._show(rest.strip())
        return self._help()

    # ── private ────────────────────────────────────────────────────────────────

    def _create(self, args: str) -> str:
        kv = _parse_kv(args)
        name = kv.get("name", "MyWebsite")
        site_type = kv.get("type", "landing").lower()
        title = kv.get("title", name)
        tagline = kv.get("tagline", "Built with AURA")
        color = kv.get("color", "#4f46e5")
        about = kv.get("about", "A passionate professional building great things.")
        skills_raw = kv.get("skills", "HTML,CSS,JavaScript,Python")
        contact = kv.get("contact", "Get in touch to collaborate on your next project.")
        email = kv.get("email", "hello@example.com")

        css = _BASE_CSS.format(color=color)

        if site_type == "portfolio":
            skills_cards = _skill_cards(skills_raw)
            html = _PORTFOLIO_HTML.format(
                title=title,
                tagline=tagline,
                about=about,
                skills_cards=skills_cards,
                contact=contact,
            )
        else:
            # landing (default)
            words = title.split()
            mid = max(1, len(words) // 2)
            title_split = " ".join(words[:mid]) + f" <span>{' '.join(words[mid:])}</span>"
            html = _LANDING_HTML.format(
                title=title,
                title_split=title_split,
                tagline=tagline,
                contact=contact,
                email=email,
            )

        # Save
        safe = re.sub(r"[^\w-]", "_", name)
        site_dir = _WEBSITES_DIR / safe
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(html, encoding="utf-8")
        (site_dir / "style.css").write_text(css, encoding="utf-8")

        return (
            f"🌐 **Website '{name}' generated!** (type: {site_type})\n\n"
            f"📂 Saved to: `{site_dir}/`\n"
            f"  • `index.html` — main page\n"
            f"  • `style.css`  — dark-mode styles\n\n"
            f"Open `index.html` in a browser, or deploy the folder to GitHub Pages, "
            f"Netlify, or any static host.\n\n"
            f"---\n\n"
            f"💡 **To customise:**\n"
            f"  - Edit `{site_dir}/index.html` to update content\n"
            f"  - Change `--primary` in `style.css` to adjust the accent color\n"
            f"  - Add images to the folder and reference them in the HTML"
        )

    def _list(self) -> str:
        _WEBSITES_DIR.mkdir(parents=True, exist_ok=True)
        dirs = [d for d in sorted(_WEBSITES_DIR.iterdir()) if d.is_dir()]
        if not dirs:
            return "📂 No websites generated yet.  Use `/tool website_generator create ...`"
        lines = ["🌐 Generated websites:"]
        for d in dirs:
            lines.append(f"  • {d.name}/")
        return "\n".join(lines)

    def _show(self, name: str) -> str:
        if not name:
            return "⚠️  Usage: /tool website_generator show <name>"
        site_dir = _WEBSITES_DIR / name
        if not site_dir.exists():
            return f"⚠️  Website '{name}' not found.  Use 'list' to see available sites."
        index = site_dir / "index.html"
        if not index.exists():
            return f"⚠️  index.html not found in '{name}'."
        return index.read_text(encoding="utf-8")

    @staticmethod
    def _help() -> str:
        return (
            "🌐 **Website Generator** — scaffold complete static websites.\n\n"
            "  **Portfolio site:**\n"
            "  ```\n"
            "  /tool website_generator create name=\"MyPortfolio\" type=portfolio \\\n"
            "    title=\"Jane Smith\" tagline=\"Full-Stack Developer\" \\\n"
            "    skills=\"Python,React,Docker\" color=\"#4f46e5\"\n"
            "  ```\n\n"
            "  **Landing page:**\n"
            "  ```\n"
            "  /tool website_generator create name=\"MyCafe\" type=landing \\\n"
            "    title=\"Blue Parrot Café\" tagline=\"Coffee with soul\" \\\n"
            "    email=\"hello@cafe.com\"\n"
            "  ```\n\n"
            "  **List sites:** `/tool website_generator list`\n\n"
            "  **Show HTML:** `/tool website_generator show <name>`\n\n"
            "  **Types:** `portfolio`, `landing`"
        )
