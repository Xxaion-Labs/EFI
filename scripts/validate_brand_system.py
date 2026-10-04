#!/usr/bin/env python3
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
errors=[]
required=[
 "docs/VISUAL-SYSTEM.md","site/DESIGN-TOKENS.json","site/VISUAL-GRAMMAR.json",
 "skills/README.md","skills/efi-visual-system/SKILL.md",
 "skills/efi-visual-system/agents/openai.yaml","skills/efi-visual-system/assets/icon.svg",
 "skills/efi-visual-system/references/brand-contract.md",
 "skills/efi-visual-system/references/surface-recipes.md"
]
for rel in required:
    if not (ROOT/rel).exists(): errors.append("MISSING "+rel)
tokens=json.loads((ROOT/"site/DESIGN-TOKENS.json").read_text(encoding="utf-8"))
for key,val in {"acid":"#A8FF00","violet":"#A855FF","orange":"#FF8A00","magenta":"#FF00E6","cyan":"#00D4FF","void":"#050505"}.items():
    if tokens.get("palette",{}).get(key)!=val: errors.append("PALETTE_DRIFT "+key)
grammar=json.loads((ROOT/"site/VISUAL-GRAMMAR.json").read_text(encoding="utf-8"))
if grammar.get("schema")!="efi.visual-grammar.v2": errors.append("VISUAL_GRAMMAR_VERSION")
if grammar.get("calling_card",{}).get("slogan")!="ONE_FIELD_ONE_VISUAL_LANGUAGE_ANY_SURFACE": errors.append("CALLING_CARD_MISSING")
for mode in ("github_readme","github_pages","skill_ui","artifact_document","artifact_presentation","social_graphic","cli_terminal"):
    if mode not in grammar.get("surface_modes",{}): errors.append("SURFACE_MODE_MISSING "+mode)
if "skills/README.md" not in grammar.get("page_roles",{}): errors.append("SKILLS_PAGE_ROLE_MISSING")
pages=json.loads((ROOT/"site/PAGES.json").read_text(encoding="utf-8"))
if not any(r.get("route")=="/skills/" and r.get("source")=="skills/README.md" for r in pages.get("routes",[])): errors.append("SKILLS_ROUTE_MISSING")
skill=(ROOT/"skills/efi-visual-system/SKILL.md").read_text(encoding="utf-8")
if not re.match(r"^---\nname: efi-visual-system\ndescription: .+?\n---\n",skill,re.S): errors.append("SKILL_FRONTMATTER_INVALID")
if "Never use visual intensity to imply a stronger technical claim" not in skill: errors.append("SKILL_PROOF_BOUNDARY_MISSING")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
for needle in ("skills/README.md","docs/VISUAL-SYSTEM.md","site/VISUAL-GRAMMAR.json"):
    if needle not in readme: errors.append("README_BRAND_ROUTE_MISSING "+needle)
base=(ROOT/"site/theme/base.html").read_text(encoding="utf-8")
css=(ROOT/"site/theme/site.css").read_text(encoding="utf-8")
if 'class="efi-systembar"' not in base: errors.append("SYSTEMBAR_MISSING")
if "EFI CALLING-CARD KERNEL v2" not in css: errors.append("CALLING_CARD_CSS_MISSING")
if errors:
    print(json.dumps({"ok":False,"errors":errors},indent=2)); raise SystemExit(2)
print(json.dumps({"ok":True,"status":"PASS_EFI_VISUAL_SYSTEM_V2","surfaces":7},indent=2))
