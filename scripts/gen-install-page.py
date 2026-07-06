#!/usr/bin/env python3
"""
Generate docs/install.html — the neutral, cross-package install-links hub,
rendered as a dependency tree. Roots sit at the top level; extension packages
nest under the package they extend.

Source of truth is the Dev Hub, NOT any repo's sfdx-project.json. We query the
latest *promoted* (released=true) version of every package and emit an install
card for it. A configured package with no promoted version renders as a greyed
"Coming soon" card automatically.

Usage:
    python3 scripts/gen-install-page.py            # writes docs/install.html
    python3 scripts/gen-install-page.py --check     # print, don't write

Requires the `sf` CLI authenticated to the Revecast Dev Hub (alias below).
"""

import json
import subprocess
import sys
import os
from datetime import date

DEV_HUB = "revecastinc"
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "install.html")

# ---------------------------------------------------------------------------
# Dependency forest. Each top-level entry is a root; `children` nest packages
# that EXTEND their parent. `depends` (str or list) renders as cross-dependency
# note flags — use it for dependencies that aren't the tree parent (e.g. Portal
# also needs Experience Components). `name` must match Package2Name exactly.
# A node with no promoted version renders "Coming soon". A node with children
# is a collapsible branch.
# ---------------------------------------------------------------------------
TREE = [
    {
        "name": "Revecast Base",
        "display": "Revecast Base",
        "icon": "\U0001f3d7️",
        "tagline": "Shared foundation for every Revecast product",
        "desc": "Shared base objects (Skill, Project Role, Person Skill, Skills Match) used across every Revecast product. The base layer everything else builds on.",
        "children": [
            {
                "name": "PSACore",
                "display": "Revecast PSA (PSACore)",
                "icon": "⚡",
                "tagline": "Time tracking, project management, scheduling, forecasting & invoicing",
                "desc": "The foundation for professional services automation in Salesforce. Includes the Timer for live tracking, the Schedule grid for capacity planning, and the Timesheet for review and approval.",
                "docs": "https://revecast.github.io/PSACore/",
                "children": [
                    {
                        "name": "PSA Setup Wizard",
                        "display": "PSA Admin Setup Wizard",
                        "icon": "\U0001f9f0",
                        "tagline": "Guided post-install configuration for a new PSA org",
                        "desc": "Walks admins through environment configuration, permission sets, project templates, and seed data so a team can start on day one.",
                        "docs": "https://revecast.github.io/PSACore/psa-setup-wizard-user-guide.html",
                        "depends": "Extends PSACore",
                    },
                    {
                        "name": "PSA PMT",
                        "display": "PSA PMT",
                        "icon": "\U0001f9e9",
                        "tagline": "Connect PSA to your project management tool (Jira)",
                        "desc": "Brings Jira projects, sprints, issues, and assignees into Salesforce automatically — and flows PSA time entries back to your forecast and reporting.",
                        "docs": "https://revecast.github.io/PSACore/pmt.html",
                        "depends": "Extends PSACore",
                    },
                    {
                        "name": "Revecast PSA Portal",
                        "display": "Revecast PSA Portal",
                        "icon": "\U0001f310",
                        "tagline": "Customer Experience Cloud portal for external users",
                        "desc": "Experience Cloud portal for Revecast PSA, for external Customer Community Plus users.",
                        "depends": ["Extends PSACore", "Also requires Revecast Experience Components"],
                    },
                    {
                        "name": "Revecast AI for PSA",
                        "display": "Revecast AI for PSA",
                        "icon": "\U0001f9e0",
                        "tagline": "AI assistant & agents for Revecast PSA",
                        "desc": "AI-powered assistance layered on top of Revecast PSA.",
                        "depends": "Extends PSACore",
                    },
                ],
            },
            {
                "name": "Revecast Recruiter",
                "display": "Revecast Recruiter",
                "icon": "\U0001f4bc",
                "tagline": "Applicant tracking, job board & candidate matching",
                "desc": "The “hire” side of Revecast — the core recruiting CRM: applicant tracking, candidate matching, and re-engagement for any industry.",
                "docs": "https://revecast.github.io/revecast-recruiter/",
                "depends": "Also requires Revecast Forms",
                "children": [
                    {
                        "name": "Revecast Job Board",
                        "display": "Revecast Job Board",
                        "icon": "\U0001faa7",
                        "tagline": "Public Experience Cloud job board for candidates",
                        "desc": "Experience Cloud (LWR) site — the public-facing job board where candidates browse and apply.",
                        "depends": "Extends Revecast Recruiter",
                    },
                    {
                        "name": "Maya",
                        "display": "Maya",
                        "icon": "\U0001f4ac",
                        "tagline": "AI candidate assistant (Agentforce)",
                        "desc": "Agentforce / Embedded Service bot that helps candidates find roles and answer questions on the job board.",
                        "depends": "Extends Revecast Recruiter",
                    },
                    {
                        "name": "Revecast HR Agent",
                        "display": "Revecast HR Agent",
                        "icon": "\U0001f9d1‍\U0001f4bb",
                        "tagline": "AI-powered recruiter assistant",
                        "desc": "AI assistant for recruiters — screening, matching, and workflow help inside Revecast Recruiter.",
                        "depends": "Extends Revecast Recruiter",
                    },
                ],
            },
        ],
    },
    {
        "name": "Revecast Connect",
        "display": "Revecast Connect",
        "icon": "\U0001f517",
        "tagline": "Integration platform for HR, finance & external systems",
        "desc": "The integration layer that keeps your Revecast system connected to the rest of your business — with AI-assisted integration building.",
        "docs": "connect.html",
    },
    {
        "name": "Revecast Forms",
        "display": "Revecast Forms",
        "icon": "\U0001f4dd",
        "tagline": "Native, dynamic form builder for Salesforce",
        "desc": "Create dynamic forms, capture submissions, and map responses to any object in real time — with conditional logic, multi-object mapping, and guest-user submissions.",
        "docs": "https://revecast.github.io/revecast-forms/",
    },
    {
        "name": "Revecast Kanban",
        "display": "Revecast Kanban",
        "icon": "\U0001f4cb",
        "tagline": "Configurable Kanban boards for any Salesforce object",
        "desc": "Turn any standard or custom object into a drag-and-drop Kanban board with a guided config wizard — no code required.",
        "docs": "https://revecast.github.io/Revecast-Kanban/",
    },
    {
        "name": "Revecast Reporting Engine",
        "display": "Revecast Reporting Engine",
        "icon": "\U0001f4ca",
        "tagline": "One-click, record-context-aware reports",
        "desc": "Drop a Lightning component on any record page for one-click access to the right reports, with record-context filters pre-applied.",
        "docs": "https://revecast.github.io/Revecast-Reporting-Engine/",
    },
    {
        "name": "Revecast Experience Components",
        "display": "Revecast Experience Components",
        "icon": "\U0001f9f1",
        "tagline": "Reusable LWR / Experience Cloud components",
        "desc": "A library of configurable components for Experience Cloud sites.",
    },
    {
        "name": "Revecast Orchestrate",
        "display": "Revecast Orchestrate",
        "icon": "\U0001f916",
        "tagline": "AI-powered, multi-org Salesforce delivery agent",
        "desc": "Persona-based session types (BUILD, DESIGN, REVIEW, DEPLOY, ASSESS, MEETING) with an AWS Fargate backend and session tracking.",
        "children": [
            {
                "name": "Revecast Orchestrate Connector",
                "display": "Orchestrate Connector",
                "icon": "\U0001f50c",
                "tagline": "External Client App for target orgs",
                "desc": "Connects a target Salesforce org to Revecast Orchestrate. Install in each org you want Orchestrate to manage.",
                "depends": "Extends Revecast Orchestrate",
            },
        ],
    },
]

INSTALL_PROD = "https://login.salesforce.com/packaging/installPackage.apexp?p0="
INSTALL_SBX = "https://test.salesforce.com/packaging/installPackage.apexp?p0="


def latest_promoted():
    """Return {package2name: {ver, id}} for the highest released version each."""
    out = subprocess.run(
        ["sf", "package", "version", "list", "--target-dev-hub", DEV_HUB,
         "--released", "--json"],
        capture_output=True, text=True, check=True,
    )
    rows = json.loads(out.stdout)["result"]
    best = {}
    for v in rows:
        pkg = v["Package2Name"]
        key = (v["MajorVersion"], v["MinorVersion"], v["PatchVersion"], v["BuildNumber"])
        if pkg not in best or key > best[pkg][0]:
            ver = "%d.%d.%d" % (v["MajorVersion"], v["MinorVersion"], v["PatchVersion"])
            best[pkg] = (key, {"ver": ver, "id": v["SubscriberPackageVersionId"]})
    return {k: val for k, (key, val) in best.items()}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def flags_html(node):
    """Render note + dependency flags. `depends` may be a str or list."""
    items = []
    if node.get("note"):
        items.append(("flag-first", node["note"]))
    deps = node.get("depends")
    if isinstance(deps, str):
        deps = [deps]
    for d in (deps or []):
        items.append(("flag-dep", d))
    if not items:
        return ""
    spans = "".join(
        f'<span class="install-flag {cls}">{esc(t)}</span>' for cls, t in items
    )
    return f'<div class="install-flags">{spans}</div>'


def render_card(node, gaged, has_children):
    ga = gaged.get(node["name"])
    icon = node["icon"]
    display = esc(node["display"])
    tagline = esc(node["tagline"])
    desc = esc(node["desc"])
    flags = flags_html(node)
    toggle = (
        '<button class="collapse-toggle" type="button" aria-label="Collapse">▾</button>'
        if has_children else '<span class="collapse-spacer"></span>'
    )
    if not ga:
        return f"""<div class="install-card is-soon">
        <div class="install-card-header">
          {toggle}
          <div class="install-icon">{icon}</div>
          <div class="install-title">{display}
            <span>{tagline}</span>
          </div>
          <span class="ver-badge ver-soon">Coming soon</span>
        </div>
        <p class="install-desc">{desc}</p>
        {flags}
      </div>"""
    ver, pid = ga["ver"], ga["id"]
    docs = ""
    if node.get("docs"):
        docs = f'<a class="btn-ghost" href="{node["docs"]}">Docs</a>'
    cli = f"sf package install --package {pid} --wait 10 --target-org &lt;alias&gt;"
    return f"""<div class="install-card">
        <div class="install-card-header">
          {toggle}
          <div class="install-icon">{icon}</div>
          <div class="install-title">{display}
            <span>{tagline}</span>
          </div>
          <span class="ver-badge">v{ver}</span>
        </div>
        <p class="install-desc">{desc}</p>
        {flags}
        <div class="install-btns">
          <a class="btn-prod" href="{INSTALL_PROD}{pid}">&#9660; Install in Production</a>
          <a class="btn-sbx" href="{INSTALL_SBX}{pid}">&#9660; Install in Sandbox</a>
          {docs}
        </div>
        <div class="install-cli"><code>{cli}</code><button class="copy-btn" type="button" data-cli="{cli}">Copy</button></div>
        <div class="install-id">Package Id: <code>{pid}</code></div>
      </div>"""


def render_node(node, gaged):
    children = node.get("children", [])
    card = render_card(node, gaged, bool(children))
    if children:
        kids = "\n".join(render_node(c, gaged) for c in children)
        return f"""<div class="tree-node">
      {card}
      <div class="tree-children">
{kids}
      </div>
    </div>"""
    return f"""<div class="tree-node">
      {card}
    </div>"""


def build(gaged):
    updated = date.today().isoformat()
    tree = "\n".join(render_node(n, gaged) for n in TREE)
    return TEMPLATE.format(updated=updated, tree=tree)


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Install Revecast Packages | Revecast</title>
  <link rel="stylesheet" href="shared/style.css">
  <style>
    .pkg-tree {{ margin-top: 8px; }}
    .tree-node {{ position: relative; }}
    .tree-children {{
      margin-left: 21px;
      padding-left: 22px;
      border-left: 1.5px solid var(--border);
    }}
    .tree-node.collapsed > .tree-children {{ display: none; }}
    /* horizontal connector from parent rail into each child card */
    .tree-children > .tree-node > .install-card::before {{
      content: "";
      position: absolute;
      left: -22px;
      top: 38px;
      width: 20px;
      height: 1.5px;
      background: var(--border);
    }}
    .install-card {{
      position: relative;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px 22px;
      margin-bottom: 14px;
      display: flex;
      flex-direction: column;
      gap: 11px;
    }}
    .install-card.is-soon {{ opacity: .6; }}
    .install-card-header {{ display: flex; align-items: center; gap: 11px; }}
    .collapse-toggle {{
      flex-shrink: 0;
      width: 22px; height: 22px;
      display: flex; align-items: center; justify-content: center;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--text-muted);
      font-size: 11px;
      cursor: pointer;
      transition: transform .15s, color .15s, border-color .15s;
    }}
    .collapse-toggle:hover {{ color: var(--text); border-color: var(--accent); }}
    .tree-node.collapsed > .install-card .collapse-toggle {{ transform: rotate(-90deg); }}
    .collapse-spacer {{ flex-shrink: 0; width: 22px; }}
    .install-icon {{
      font-size: 22px;
      width: 42px; height: 42px;
      display: flex; align-items: center; justify-content: center;
      background: var(--accent-soft);
      border-radius: 8px;
      flex-shrink: 0;
    }}
    .install-title {{ font-size: 16px; font-weight: 700; color: var(--text); flex: 1; }}
    .install-title span {{ display: block; font-size: 12px; font-weight: 400; color: var(--text-muted); margin-top: 2px; }}
    .ver-badge {{
      flex-shrink: 0;
      font-size: 12px; font-weight: 700;
      font-family: var(--font-mono);
      color: var(--green);
      background: rgba(34,197,94,.12);
      border: 1px solid rgba(34,197,94,.3);
      padding: 3px 10px; border-radius: 999px;
    }}
    .ver-badge.ver-soon {{ color: var(--text-dim); background: var(--bg-surface); border-color: var(--border); }}
    .install-desc {{ margin: 0; font-size: 13.5px; color: var(--text-muted); padding-left: 33px; }}
    .install-flags {{ display: flex; flex-wrap: wrap; gap: 6px; padding-left: 33px; }}
    .install-flag {{
      font-size: 11px; font-weight: 600;
      padding: 3px 9px; border-radius: 4px;
    }}
    .flag-first {{ background: rgba(34,197,94,.12); color: var(--green); border: 1px solid rgba(34,197,94,.25); }}
    .flag-dep {{ background: var(--rc-blue-soft); color: var(--rc-blue-hover); border: 1px solid var(--rc-blue-border); }}
    .install-btns {{ display: flex; flex-wrap: wrap; gap: 8px; padding-left: 33px; }}
    .install-btns a {{ font-size: 13px; font-weight: 600; padding: 7px 14px; border-radius: 5px; text-decoration: none; }}
    .btn-prod {{ background: var(--rc-blue); color: #fff; }}
    .btn-prod:hover {{ background: var(--rc-blue-hover); text-decoration: none; }}
    .btn-sbx {{ background: var(--accent-soft); color: var(--accent-hover); border: 1px solid var(--rc-blue-border); }}
    .btn-sbx:hover {{ background: rgba(12,131,223,.2); text-decoration: none; }}
    .btn-ghost {{ background: transparent; color: var(--text-muted); border: 1px solid var(--border); }}
    .btn-ghost:hover {{ color: var(--text); text-decoration: none; }}
    .install-cli {{
      display: flex; align-items: center; gap: 8px;
      margin-left: 33px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--text-muted);
      overflow-x: auto;
    }}
    .install-cli code {{ flex: 1; white-space: nowrap; background: none; padding: 0; }}
    .copy-btn {{
      flex-shrink: 0;
      font-size: 11px; font-weight: 600;
      background: var(--bg-card);
      color: var(--text-muted);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 3px 9px; cursor: pointer;
    }}
    .copy-btn:hover {{ color: var(--text); border-color: var(--accent); }}
    .install-id {{ font-size: 11px; color: var(--text-dim); padding-left: 33px; }}
    .install-id code {{ font-size: 11px; color: var(--text-muted); background: none; padding: 0; }}
    .updated-note {{ font-size: 12px; color: var(--text-dim); margin-top: -8px; }}
    .tree-tools {{ display: flex; gap: 8px; margin: 4px 0 18px; }}
    .tree-tools button {{
      font-size: 12px; font-weight: 600;
      background: var(--bg-card); color: var(--text-muted);
      border: 1px solid var(--border); border-radius: 5px;
      padding: 5px 11px; cursor: pointer;
    }}
    .tree-tools button:hover {{ color: var(--text); border-color: var(--accent); }}
    @media (max-width: 768px) {{
      .tree-children {{ margin-left: 10px; padding-left: 12px; }}
      .tree-children > .tree-node > .install-card::before {{ left: -12px; width: 10px; }}
      .install-desc, .install-btns, .install-cli, .install-id, .install-flags {{ padding-left: 0; margin-left: 0; }}
    }}
  </style>
</head>
<body>

<nav class="sidebar">
  <div class="sidebar-brand">
    <a href="index.html"><img src="shared/logo.svg" alt="Revecast" class="sidebar-logo"></a>
    <a class="logo" href="index.html">Revecast</a>
    <div class="badge">Documentation</div>
  </div>
  <div class="sidebar-nav">
    <a href="index.html"><span class="icon">&#127968;</span> Home</a>
    <a href="system.html"><span class="icon">&#128260;</span> The Revecast System</a>
    <a href="install.html" class="active"><span class="icon">&#128230;</span> Install &amp; Downloads</a>

    <div class="nav-section">Community</div>
    <a href="feedback/"><span class="icon">&#128161;</span> Feature Requests</a>

    <div class="nav-section">Products</div>
    <a href="https://revecast.github.io/PSACore/"><span class="icon">&#9889;</span> Revecast PSA</a>
    <a href="https://revecast.github.io/revecast-recruiter/"><span class="icon">&#128188;</span> Revecast Recruiter</a>
    <a href="https://revecast.github.io/revecast-forms/"><span class="icon">&#128221;</span> Revecast Forms</a>
    <a href="https://revecast.github.io/Revecast-Kanban/"><span class="icon">&#128203;</span> Revecast Kanban</a>
    <a href="connect.html"><span class="icon">&#128279;</span> Revecast Connect</a>
    <a href="https://revecast.github.io/Revecast-Reporting-Engine/"><span class="icon">&#128202;</span> Reporting Engine</a>
  </div>
</nav>

<div class="main">
  <div class="topbar">
    <button type="button" class="hamburger" aria-label="Menu"><span></span><span></span><span></span></button>
    <div class="topbar-title"><strong>Revecast</strong> &mdash; Install &amp; Downloads</div>
    <div class="topbar-meta"></div>
  </div>

  <div class="content">
    <div class="page-hero">
      <h1>Install Revecast Packages
        <span class="subtitle">Latest released versions of every Revecast package, shown as a dependency tree with production and sandbox install links.</span>
      </h1>
    </div>

    <p class="updated-note">Latest promoted (GA) versions from the Revecast Dev Hub. Last updated {updated}.</p>

    <div class="alert alert-info">
      <span class="alert-icon">&#128161;</span>
      <p>Packages are nested by dependency &mdash; install a parent before its children. Extension packages (Setup Wizard, PMT, Portal, AI) sit under <strong>PSACore</strong>. Blue tags call out additional dependencies beyond the parent.</p>
    </div>

    <div class="tree-tools">
      <button type="button" id="expand-all">Expand all</button>
      <button type="button" id="collapse-all">Collapse all</button>
    </div>

    <div class="pkg-tree">
{tree}
    </div>

  </div>
</div>

<script src="shared/nav.js"></script>
<script>
  document.querySelectorAll('.collapse-toggle').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      btn.closest('.tree-node').classList.toggle('collapsed');
    }});
  }});
  var ea = document.getElementById('expand-all');
  var ca = document.getElementById('collapse-all');
  if (ea) ea.addEventListener('click', function () {{
    document.querySelectorAll('.tree-node.collapsed').forEach(function (n) {{ n.classList.remove('collapsed'); }});
  }});
  if (ca) ca.addEventListener('click', function () {{
    document.querySelectorAll('.tree-children').forEach(function (c) {{ c.parentElement.classList.add('collapsed'); }});
  }});
  document.querySelectorAll('.copy-btn').forEach(function (b) {{
    b.addEventListener('click', function () {{
      navigator.clipboard.writeText(b.getAttribute('data-cli').replace('&lt;', '<').replace('&gt;', '>'));
      var t = b.textContent; b.textContent = 'Copied'; setTimeout(function () {{ b.textContent = t; }}, 1200);
    }});
  }});
</script>
</body>
</html>
"""


def main():
    gaged = latest_promoted()
    html = build(gaged)
    if "--check" in sys.argv:
        sys.stdout.write(html)
        return
    with open(OUT, "w") as f:
        f.write(html)
    print("wrote", os.path.relpath(OUT))

    def show(nodes, depth=0):
        for n in nodes:
            ga = gaged.get(n["name"])
            tag = "GA v" + ga["ver"] if ga else "coming soon"
            print(f"  {'  ' * depth}{tag:<14} {n['name']}")
            show(n.get("children", []), depth + 1)
    show(TREE)


if __name__ == "__main__":
    main()
