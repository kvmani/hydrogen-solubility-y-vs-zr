"""Sphinx configuration for the hydrogen solubility documentation site."""

from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hydrogen_solubility import __version__  # noqa: E402

project = "Hydrogen Solubility Documentation"
author = "Hydrogen solubility contributors"
copyright = f"{_dt.datetime.now().year}, {author}"
release = __version__
version = __version__

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.bibtex",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
]

myst_enable_extensions = [
    "colon_fence",
    "dollarmath",
    "amsmath",
    "attrs_block",
    "attrs_inline",
    "substitution",
]
myst_fence_as_directive = ["mermaid"]
myst_heading_anchors = 3

autosectionlabel_prefix_document = True
autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = ["_build", ".DS_Store", "**/__pycache__/**"]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
master_doc = "index"
language = "en"
pygments_style = "sphinx"

html_theme = "furo"
html_title = project
html_baseurl = os.environ.get("HYDROGEN_SOLUBILITY_DOCS_BASEURL", "")
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_show_sourcelink = True
html_copy_source = False
html_last_updated_fmt = "%Y-%m-%d"
html_favicon = ""

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "light_css_variables": {
        "color-brand-primary": "#1f4e79",
        "color-brand-content": "#173958",
        "color-api-name": "#16324d",
        "color-api-pre-name": "#16324d",
        "color-sidebar-background": "#12263a",
        "color-sidebar-background-border": "#0b1b29",
        "color-sidebar-item-background": "#12263a",
        "color-sidebar-item-background--current": "#1f4e79",
        "color-sidebar-item-background--hover": "#183a58",
        "color-sidebar-item-expander-background": "#224e73",
        "color-sidebar-item-expander-background--hover": "#2c628c",
        "color-sidebar-link-text": "#edf4fb",
        "color-sidebar-link-text--top-level": "#ffe7b0",
        "color-sidebar-caption-text": "#c7d6e4",
        "color-sidebar-brand-text": "#ffffff",
        "color-sidebar-search-background": "#102335",
        "color-sidebar-search-background--focus": "#14314a",
        "color-sidebar-search-border": "#35516c",
        "color-sidebar-search-foreground": "#f5f8fb",
        "color-sidebar-search-icon": "#c5d6e7",
    },
}

bibtex_bibfiles = ["../literature/library.bib"]
bibtex_default_style = "alpha"
bibtex_reference_style = "author_year"

html_context = {
    "display_github": False,
    "current_year": _dt.datetime.now().year,
}

mathjax3_config = {
    "tex": {
        "packages": {"[+]": ["ams"]},
    }
}

numfig = True
nitpicky = False
