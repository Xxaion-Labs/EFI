#!/usr/bin/env python3
import argparse, hashlib, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

class Scan(HTMLParser):
    def __init__(self): super().__init__(); self.refs=[]; self.imgs=[]; self.scripts=[]; self.styles=[]; self.titles=0; self.viewports=0; self.h1=0
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='a' and d.get('href'): self.refs.append(('href',d['href']))
        if tag in ('img','script') and d.get('src'): self.refs.append(('src',d['src']))
        if tag=='link' and d.get('href'): self.refs.append(('href',d['href']))
        if tag=='img': self.imgs.append(d)
        if tag=='script' and d.get('src'): self.scripts.append(d['src'])
        if tag=='link' and d.get('rel')=='stylesheet': self.styles.append(d.get('href',''))
        if tag=='title': self.titles+=1
        if tag=='meta' and d.get('name')=='viewport': self.viewports+=1
        if tag=='h1': self.h1+=1

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('repo'); ap.add_argument('--site',default='_site'); ap.add_argument('--json',action='store_true')
    a=ap.parse_args(); repo=Path(a.repo).resolve(); site=(repo/a.site).resolve(); errors=[]; warnings=[]
    cfg=json.loads((repo/'site/PAGES.json').read_text(encoding='utf-8')); manifest=json.loads((site/'build-manifest.json').read_text(encoding='utf-8')) if (site/'build-manifest.json').exists() else None
    grammar_path=repo/cfg.get('visual_grammar','site/VISUAL-GRAMMAR.json')
    if not grammar_path.exists(): errors.append('VISUAL_GRAMMAR_MISSING '+str(grammar_path.relative_to(repo)))
    else:
        grammar=json.loads(grammar_path.read_text(encoding='utf-8'))
        if grammar.get('layout',{}).get('left_sidebar') is not False: errors.append('LEFT_SIDEBAR_GRAMMAR_FORBIDDEN')
        if grammar.get('layout',{}).get('top_nav') is not True: errors.append('TOP_NAV_GRAMMAR_REQUIRED')
        if grammar.get('layout',{}).get('route_cards') is not False: errors.append('DUPLICATE_PRIMARY_ROUTE_LATTICE_GRAMMAR_FORBIDDEN')
        if cfg.get('features',{}).get('route_cards') is not False: errors.append('DUPLICATE_PRIMARY_ROUTE_LATTICE_CONFIG_FORBIDDEN')
    base=manifest.get('base_path','') if manifest else ''
    required=['index.html','404.html','theme/site.css','theme/site.js','search-index.json','sitemap.xml','robots.txt','site.webmanifest','build-manifest.json','.nojekyll']
    for rel in required:
        if not (site/rel).exists(): errors.append('SITE_MISSING '+rel)
    if (site/'service-worker.js').exists(): errors.append('SERVICE_WORKER_FORBIDDEN freshness law')
    site_css=(site/'theme/site.css').read_text(encoding='utf-8',errors='replace') if (site/'theme/site.css').exists() else ''
    if '--efi-hero-frame' in site_css or '.efi-hero-split::before' in site_css: errors.append('HOME_INTRO_BACKGROUND_FRAME_CSS_FORBIDDEN')
    total_nonmedia=0
    for p in site.rglob('*'):
        if not p.is_file(): continue
        if p.suffix.lower() in {'.html','.css','.js','.json','.xml','.txt'}: total_nonmedia+=p.stat().st_size
    b=cfg['budgets']
    if (site/'theme/site.css').exists() and (site/'theme/site.css').stat().st_size>b['css_bytes']: errors.append('CSS_BUDGET')
    if (site/'theme/site.js').exists() and (site/'theme/site.js').stat().st_size>b['js_bytes']: errors.append('JS_BUDGET')
    if total_nonmedia>b['total_generated_nonmedia_bytes']: errors.append('NONMEDIA_BUDGET')
    html_files=list(site.rglob('*.html'))
    for p in html_files:
        if p.stat().st_size>b['html_bytes_per_page']: errors.append('HTML_BUDGET '+p.relative_to(site).as_posix())
        raw=p.read_text(encoding='utf-8',errors='replace')
        if 'class="rail"' in raw or '<aside class="rail"' in raw: errors.append('LEFT_SIDEBAR_PRESENT '+p.relative_to(site).as_posix())
        if 'id="site-nav"' not in raw: errors.append('TOP_NAV_MISSING '+p.relative_to(site).as_posix())
        if 'route-lattice' in raw or 'class="route-card"' in raw: errors.append('DUPLICATE_PRIMARY_ROUTE_LATTICE_PRESENT '+p.relative_to(site).as_posix())
        if p.relative_to(site).as_posix()=='index.html':
            if '## EFI in one sentence' in raw or '**A persistent personal intelligence' in raw: errors.append('HOME_INTRO_RAW_MARKDOWN_LEAK')
            if 'class="efi-hero-split"' not in raw: errors.append('HOME_INTRO_COMPONENT_MISSING')
            if 'class="efi-hero-split" data-efi-frame=' in raw or '--efi-hero-frame' in raw: errors.append('HOME_INTRO_BACKGROUND_FRAME_FORBIDDEN')
        sc=Scan(); sc.feed(raw)
        if not sc.titles: errors.append('TITLE_MISSING '+p.relative_to(site).as_posix())
        if not sc.viewports: errors.append('VIEWPORT_MISSING '+p.relative_to(site).as_posix())
        if p.name!='404.html' and not sc.h1: warnings.append('H1_MISSING '+p.relative_to(site).as_posix())
        for img in sc.imgs:
            if 'alt' not in img: errors.append('IMG_ALT_MISSING '+p.relative_to(site).as_posix())
        for u in sc.scripts+sc.styles:
            if re.match(r'^https?://',u): errors.append('THIRD_PARTY_RUNTIME '+u)
        for kind,u in sc.refs:
            if not u or u.startswith(('#','mailto:','tel:','data:','https://','http://')): continue
            path=u.split('#',1)[0].split('?',1)[0]
            if base and path.startswith(base+'/'): path=path[len(base)+1:]
            elif base and path==base+'/': path=''
            elif path.startswith('/'): path=path[1:]
            if not path: target=site/'index.html'
            elif path.endswith('/'): target=site/path/'index.html'
            else: target=site/path
            if not target.exists(): errors.append(f'BROKEN_SITE_REF {p.relative_to(site)} -> {u}')
    if manifest:
        for rel,h in manifest.get('outputs',{}).items():
            p=site/rel
            if not p.exists(): errors.append('MANIFEST_OUTPUT_MISSING '+rel)
            elif sha(p)!=h: errors.append('BUILD_HASH_DRIFT '+rel)
        src_map={r['source']:r for r in manifest.get('routes',[])}
        for src,r in src_map.items():
            p=repo/src
            if not p.exists(): errors.append('SOURCE_MISSING '+src)
            elif sha(p)!=r['source_sha256']: errors.append('SOURCE_HASH_DRIFT '+src)
    wf=(repo/'.github/workflows/pages.yml').read_text(encoding='utf-8',errors='replace') if (repo/'.github/workflows/pages.yml').exists() else ''
    lock=json.loads((repo/'site/PAGES-PLATFORM-LOCK.json').read_text(encoding='utf-8')) if (repo/'site/PAGES-PLATFORM-LOCK.json').exists() else {'github_actions':{}}
    for action in lock.get('github_actions',{}).values():
        if action not in wf: errors.append('WORKFLOW_LOCK_MISMATCH '+action)
    result={'ok':not errors,'errors':sorted(set(errors)),'warnings':sorted(set(warnings)),'html_pages':len(html_files),'nonmedia_bytes':total_nonmedia}
    print(json.dumps(result,indent=2) if a.json else '\n'.join([f"OK={result['ok']} PAGES={len(html_files)} NONMEDIA={total_nonmedia}"]+result['errors']+result['warnings']))
    sys.exit(0 if not errors else 2)
if __name__=='__main__': main()
