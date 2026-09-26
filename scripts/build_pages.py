#!/usr/bin/env python3
import argparse, hashlib, html, json, os, re, shutil
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

try:
    import markdown as _markdown
except Exception:
    _markdown=None

LINK_RE=re.compile(r'(!?)\[([^\]]*)\]\(([^)]+)\)')
HTML_SRC_RE=re.compile(r'(?P<prefix>\b(?:src|href)=["\'])(?P<url>[^"\']+)(?P<suffix>["\'])',re.I)
HEADING_RE=re.compile(r'^(#{1,6})\s+(.+?)\s*$')
TAG_RE=re.compile(r'<[^>]+>')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean_base_path(v):
    v=(v or '').strip()
    if not v or v=='/': return ''
    return '/'+v.strip('/')
def join_url(base,route):
    base=clean_base_path(base)
    if route=='/': return (base or '')+'/'
    return (base or '')+'/'+route.strip('/')+'/'
def slugify(s):
    s=TAG_RE.sub('',s); s=re.sub(r'[`*_~]','',s).lower(); s=re.sub(r'[^a-z0-9 -]','',s); s=re.sub(r'[\s-]+','-',s).strip('-')
    return s or 'section'
def inline(s):
    s=re.sub(r'`([^`]+)`',lambda m:f'<code>{html.escape(m.group(1))}</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<em>\1</em>',s)
    return s
def simple_markdown(text):
    lines=text.splitlines(); out=[]; para=[]; in_code=False; code=[]; in_ul=False; in_ol=False; table=None
    def flush_para():
        nonlocal para
        if para: out.append('<p>'+inline(' '.join(x.strip() for x in para))+'</p>'); para=[]
    def close_lists():
        nonlocal in_ul,in_ol
        if in_ul: out.append('</ul>'); in_ul=False
        if in_ol: out.append('</ol>'); in_ol=False
    i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('```'):
            flush_para(); close_lists()
            if not in_code:
                in_code=True; code=[]
            else:
                out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>'); in_code=False
            i+=1; continue
        if in_code: code.append(line); i+=1; continue
        if line.startswith('|') and i+1<len(lines) and re.match(r'^\s*\|?\s*:?-+',lines[i+1]):
            flush_para(); close_lists(); headers=[x.strip() for x in line.strip('|').split('|')]
            i+=2; rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                rows.append([x.strip() for x in lines[i].strip('|').split('|')]); i+=1
            out.append('<table><thead><tr>'+''.join(f'<th>{inline(x)}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{inline(x)}</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'); continue
        m=HEADING_RE.match(line)
        if m:
            flush_para(); close_lists(); level=len(m.group(1)); title=inline(m.group(2)); out.append(f'<h{level} id="{slugify(m.group(2))}">{title}</h{level}>'); i+=1; continue
        if line.strip() in ('---','***','___'):
            flush_para(); close_lists(); out.append('<hr>'); i+=1; continue
        if re.match(r'^\s*[-*+]\s+',line):
            flush_para()
            if in_ol: out.append('</ol>'); in_ol=False
            if not in_ul: out.append('<ul>'); in_ul=True
            out.append('<li>'+inline(re.sub(r'^\s*[-*+]\s+','',line))+'</li>'); i+=1; continue
        if re.match(r'^\s*\d+\.\s+',line):
            flush_para()
            if in_ul: out.append('</ul>'); in_ul=False
            if not in_ol: out.append('<ol>'); in_ol=True
            out.append('<li>'+inline(re.sub(r'^\s*\d+\.\s+','',line))+'</li>'); i+=1; continue
        if line.startswith('>'):
            flush_para(); close_lists(); out.append('<blockquote>'+inline(line[1:].strip())+'</blockquote>'); i+=1; continue
        if line.lstrip().startswith('<'):
            flush_para(); close_lists(); out.append(line); i+=1; continue
        if not line.strip(): flush_para(); close_lists(); i+=1; continue
        para.append(line); i+=1
    flush_para(); close_lists()
    if in_code: out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(out)

def compile_tokens(tokens):
    p=tokens['palette']; t=tokens['typography']; g=tokens['geometry']; e=tokens['effects']
    return ':root{'+ ';'.join([
        f'--void:{p["void"]}',f'--panel:{p["panel"]}',f'--panel-2:{p["panel_2"]}',f'--text:{p["text"]}',f'--muted:{p["muted"]}',f'--acid:{p["acid"]}',f'--violet:{p["violet"]}',f'--orange:{p["orange"]}',f'--magenta:{p["magenta"]}',f'--cyan:{p["cyan"]}',f'--line:{p["line"]}',f'--body:{t["body_stack"]}',f'--mono:{t["mono_stack"]}',f'--base:{t["base_px"]}px',f'--line-height:{t["line_height"]}',f'--content-max:{g["content_max_px"]}px',f'--reading-max:{g["reading_max_px"]}px',f'--glow-soft:{e["glow_soft"]}',f'--glow-violet:{e["glow_violet"]}',f'--glow-orange:{e["glow_orange"]}'
    ])+'}'
def extract_description(md):
    txt=[]
    for line in md.splitlines():
        s=line.strip()
        if not s or s.startswith(('#','<','```','---','|','[!')): continue
        s=re.sub(r'[*_`>#]','',s); s=re.sub(r'\[[^\]]+\]\([^)]+\)','',s)
        if s: txt.append(s)
        if sum(map(len,txt))>180: break
    return html.unescape(' '.join(txt))[:220] or 'EFI — Extracortical Field Intelligence and Field Computing.'
def text_only(s):
    s=TAG_RE.sub(' ',s); s=re.sub(r'[`*_>#|\[\]()!-]',' ',s); return re.sub(r'\s+',' ',s).strip()

def unique(seq):
    out=[]; seen=set()
    for x in seq:
        if x not in seen: seen.add(x); out.append(x)
    return out

def grammar_asset_pool(grammar,surface,kind):
    roles=grammar.get('page_roles',{}).get(surface,{})
    role_names=roles.get(kind,[])
    bank=grammar.get('asset_roles',{}).get({'frames':'frames','markers':'markers','dividers':'dividers'}[kind],{})
    return unique([asset for role in role_names for asset in bank.get(role,[])])

def decorate_html(body,grammar,surface,base_path):
    frame_pool=grammar_asset_pool(grammar,surface,'frames')
    marker_pool=grammar_asset_pool(grammar,surface,'markers')
    fi=0
    def wrap(tag,text):
        nonlocal fi
        if not frame_pool: return text
        pat=re.compile(rf'(<{tag}\b[^>]*>.*?</{tag}>)',re.I|re.S)
        def repl(m):
            nonlocal fi
            asset=frame_pool[fi%len(frame_pool)]; fi+=1
            # Preserve the semantic frame slot and deterministic family assignment,
            # but do not paint the frame asset into the runtime UI.
            return f'<div class="efi-frame efi-frame--{tag}" data-efi-frame="{html.escape(Path(asset).stem,quote=True)}"><div class="efi-frame__content">{m.group(1)}</div></div>'
        return pat.sub(repl,text)
    for tag in grammar.get('build_projection',{}).get('frame_block_tags',['table','blockquote','pre']):
        body=wrap(tag,body)
    if grammar.get('build_projection',{}).get('decorate_unordered_lists',True) and marker_pool:
        mi=0
        def list_repl(m):
            nonlocal mi
            asset=marker_pool[mi%len(marker_pool)]; mi+=1
            url=join_url(base_path,asset).rstrip('/')
            return f'<ul class="efi-list" data-efi-marker="{html.escape(Path(asset).stem,quote=True)}" style="--efi-marker:url({html.escape(url,quote=True)})">'
        body=re.sub(r'<ul>',list_repl,body,flags=re.I)
    return body

def extract_home_intro(md2, route):
    """Lift the canonical README split-intro out of raw HTML before page Markdown render."""
    if route!='/': return md2,None
    pat=re.compile(
        r'<table>\s*<tr>\s*'
        r'<td\s+width=["\']42%["\']\s+align=["\']center["\']>\s*(?P<mark>.*?)\s*</td>\s*'
        r'<td\s+width=["\']58%["\']>\s*(?P<body>## EFI in one sentence.*?)\s*</td>\s*'
        r'</tr>\s*</table>',
        re.I|re.S
    )
    m=pat.search(md2)
    if not m: raise SystemExit('HOME_INTRO_PROJECTION_MISSING')
    token='EFI_HOME_SPLIT_INTRO_TOKEN'
    out=md2[:m.start()]+token+md2[m.end():]
    return out,{'mark':m.group('mark').strip(),'body':m.group('body').strip(),'token':token}

def render_home_intro(hero, renderer, grammar, base_path):
    if not hero: return None
    if renderer=='markdown':
        if not _markdown: raise SystemExit('MARKDOWN_DEPENDENCY_MISSING install site/requirements-pages.txt or use --renderer simple')
        copy_html=_markdown.markdown(hero['body'],extensions=['extra','tables','fenced_code','sane_lists','toc'],output_format='html5')
    else:
        copy_html=simple_markdown(hero['body'])
    return (
        '<section class="efi-hero-split">'
        f'<div class="efi-hero-mark">{hero["mark"]}</div>'
        f'<div class="efi-hero-copy"><div class="efi-hero-copy__markdown">{copy_html}</div></div>'
        '</section>'
    )

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('repo'); ap.add_argument('--out',default='_site'); ap.add_argument('--base-path',default=''); ap.add_argument('--base-url',default=''); ap.add_argument('--renderer',choices=['auto','simple','markdown'],default='auto')
    a=ap.parse_args(); repo=Path(a.repo).resolve(); out=(repo/a.out).resolve(); base_path=clean_base_path(a.base_path); base_url=(a.base_url or '').rstrip('/')
    cfg=json.loads((repo/'site/PAGES.json').read_text(encoding='utf-8')); tokens=json.loads((repo/'site/DESIGN-TOKENS.json').read_text(encoding='utf-8')); grammar=json.loads((repo/cfg.get('visual_grammar','site/VISUAL-GRAMMAR.json')).read_text(encoding='utf-8'))
    template=(repo/'site/theme/base.html').read_text(encoding='utf-8'); css=(repo/'site/theme/site.css').read_text(encoding='utf-8').replace('{{TOKENS_CSS}}',compile_tokens(tokens)); js=(repo/'site/theme/site.js').read_text(encoding='utf-8')
    if out.exists(): shutil.rmtree(out)
    (out/'theme').mkdir(parents=True); (out/'theme/site.css').write_text(css,encoding='utf-8'); (out/'theme/site.js').write_text(js,encoding='utf-8'); (out/'.nojekyll').write_text('',encoding='utf-8')
    routes=sorted(cfg['routes'],key=lambda x:x['order']); source_to_route={str(PurePosixPath(x['source'])):x['route'] for x in routes}
    copied=set()
    def copy_local(rel):
        rel=str(PurePosixPath(rel)); src=repo/rel
        if not src.exists() or not src.is_file(): return False
        dst=out/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); copied.add(rel); return True
    for asset in cfg.get('theme_assets',[]): copy_local(asset)
    def collect_assets(node):
        if isinstance(node,str) and node.startswith('assets/'): return [node]
        if isinstance(node,list): return [y for x in node for y in collect_assets(x)]
        if isinstance(node,dict): return [y for x in node.values() for y in collect_assets(x)]
        return []
    for asset in unique(collect_assets(grammar.get('asset_roles',{}))): copy_local(asset)
    favicon=join_url(base_path,'assets/brand/efi-sigil.png').rstrip('/')
    endmark=join_url(base_path,'assets/ui/accents/accent-star-end.png').rstrip('/') if (repo/'assets/ui/accents/accent-star-end.png').exists() else favicon
    primary=''.join(f'<a href="{join_url(base_path,r["route"])}" data-route="{html.escape(r["route"])}">{html.escape(r["nav"])}</a>' for r in routes if r['group']=='primary')
    reference=''.join(f'<a href="{join_url(base_path,r["route"])}" data-route="{html.escape(r["route"])}">{html.escape(r["nav"])}</a>' for r in routes if r['group']=='reference')
    manifest_routes=[]; search=[]
    for r in routes:
        src=repo/r['source']
        if not src.exists(): raise SystemExit(f'PAGES_SOURCE_MISSING {r["source"]}')
        md=src.read_text(encoding='utf-8',errors='replace')
        src_parent=PurePosixPath(r['source']).parent
        def repl(m):
            bang,label,target=m.groups(); target=target.strip(); parts=urlsplit(target)
            if parts.scheme or target.startswith(('#','mailto:','tel:')): return m.group(0)
            path=parts.path
            if not path: return m.group(0)
            resolved=str((src_parent/PurePosixPath(path)).as_posix())
            while resolved.startswith('./'): resolved=resolved[2:]
            seg=[]
            for p in resolved.split('/'):
                if p=='..':
                    if seg: seg.pop()
                elif p not in ('','.'): seg.append(p)
            resolved='/'.join(seg)
            frag=('#'+parts.fragment) if parts.fragment else ''
            if bang:
                if copy_local(resolved): return f'![{label}]({join_url(base_path,resolved).rstrip("/")}{frag})'
                return m.group(0)
            if resolved in source_to_route: return f'[{label}]({join_url(base_path,source_to_route[resolved])}{frag})'
            if (repo/resolved).exists(): return f'[{label}](https://github.com/{cfg["repository"]}/blob/main/{resolved}{frag})'
            return m.group(0)
        md2=LINK_RE.sub(repl,md)
        def htmlref(m):
            u=m.group('url'); parts=urlsplit(u)
            if parts.scheme or u.startswith(('#','data:')): return m.group(0)
            path=parts.path; resolved=str((src_parent/PurePosixPath(path)).as_posix()); seg=[]
            for p in resolved.split('/'):
                if p=='..':
                    if seg: seg.pop()
                elif p not in ('','.'): seg.append(p)
            resolved='/'.join(seg); frag=('#'+parts.fragment) if parts.fragment else ''
            if resolved in source_to_route: new=join_url(base_path,source_to_route[resolved])+frag
            elif copy_local(resolved): new=join_url(base_path,resolved).rstrip('/')+frag
            else: return m.group(0)
            return m.group('prefix')+new+m.group('suffix')
        md2=HTML_SRC_RE.sub(htmlref,md2)
        md2,home_intro=extract_home_intro(md2,r['route'])
        # GitHub-authored source commonly uses raw HTML containers around Markdown.
        # Python-Markdown only parses Markdown inside block HTML when the container
        # opts in. Add that opt-in mechanically so the Pages projection preserves
        # the canonical repo surface instead of leaking literal Markdown syntax.
        md2=re.sub(r'<div\s+align=["\']center["\']>', '<div align="center" markdown="1">', md2, flags=re.I)
        md2=re.sub(r'<td(?P<attrs>\s+[^>]*)>', lambda m: '<td'+m.group('attrs')+' markdown="1">' if 'markdown=' not in m.group(0).lower() else m.group(0), md2, flags=re.I)
        renderer=a.renderer
        if renderer=='auto': renderer='markdown' if _markdown else 'simple'
        if renderer=='markdown':
            if not _markdown: raise SystemExit('MARKDOWN_DEPENDENCY_MISSING install site/requirements-pages.txt or use --renderer simple')
            body=_markdown.markdown(md2,extensions=['extra','tables','fenced_code','sane_lists','toc'],output_format='html5')
        else: body=simple_markdown(md2)
        body=decorate_html(body,grammar,r['surface_recipe'],base_path)
        if home_intro:
            hero_html=render_home_intro(home_intro,renderer,grammar,base_path)
            body=body.replace('<p>'+home_intro['token']+'</p>',hero_html).replace(home_intro['token'],hero_html)
        if not re.search(r'<h1\b',body,re.I):
            body=f'<h1 class="sr-only">{html.escape(r["title"])}</h1>'+body
        desc=extract_description(md); route_url=join_url(base_path,r['route']); canonical=(base_url+('/' if r['route']=='/' else r['route'])) if base_url else route_url
        og=(base_url if base_url else base_path)+('/assets/brand/efi-hero-wide.png' if (repo/'assets/brand/efi-hero-wide.png').exists() else '/assets/brand/efi-sigil.png')
        copy_local('assets/brand/efi-hero-wide.png') if (repo/'assets/brand/efi-hero-wide.png').exists() else None
        page=template
        vals={'TITLE':html.escape(r['title']),'DESCRIPTION':html.escape(desc,quote=True),'CANONICAL_URL':html.escape(canonical,quote=True),'OG_IMAGE':html.escape(og,quote=True),'FAVICON':html.escape(favicon,quote=True),'BASE_PATH':html.escape(base_path,quote=True),'ROUTE':html.escape(r['route'],quote=True),'SURFACE':html.escape(r['surface_recipe'],quote=True),'PRIMARY_NAV':primary,'REFERENCE_NAV':reference,'CONTENT':body,'END_MARK':html.escape(endmark,quote=True),'JSON_LD':json.dumps({'@context':'https://schema.org','@type':'TechArticle','headline':r['title'],'url':canonical,'isPartOf':{'@type':'WebSite','name':'EFI','url':base_url or route_url}},separators=(',',':'))}
        for k,v in vals.items(): page=page.replace('{{'+k+'}}',v)
        page=page.replace('<html lang="en">',f'<html lang="en" data-base-path="{html.escape(base_path,quote=True)}">')
        dest=out/'index.html' if r['route']=='/' else out/r['route'].strip('/')/'index.html'; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(page,encoding='utf-8')
        manifest_routes.append({'route':r['route'],'source':r['source'],'source_sha256':sha(src),'output':dest.relative_to(out).as_posix(),'output_sha256':sha(dest)})
        clean=text_only(md); search.append({'title':r['title'],'url':route_url,'text':clean[:12000],'excerpt':clean[:190]})
    (out/'search-index.json').write_text(json.dumps(search,separators=(',',':')),encoding='utf-8')
    (out/'site.webmanifest').write_text(json.dumps({'name':'EFI','short_name':'EFI','start_url':join_url(base_path,'/'),'display':'standalone','background_color':'#050505','theme_color':'#050505','icons':[]},separators=(',',':')),encoding='utf-8')
    sitemap=''.join(f'<url><loc>{html.escape((base_url+r["route"]) if base_url else join_url(base_path,r["route"]))}</loc></url>' for r in routes)
    (out/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+sitemap+'</urlset>',encoding='utf-8')
    (out/'robots.txt').write_text('User-agent: *\nAllow: /\n'+(('Sitemap: '+base_url+'/sitemap.xml\n') if base_url else ''),encoding='utf-8')
    notfound=template
    vals={'TITLE':'Not Found','DESCRIPTION':'EFI route not found.','CANONICAL_URL':html.escape(base_url+'/404.html' if base_url else ((base_path or '')+'/404.html'),quote=True),'OG_IMAGE':html.escape(og,quote=True),'FAVICON':html.escape(favicon,quote=True),'BASE_PATH':html.escape(base_path,quote=True),'ROUTE':'/404.html','SURFACE':'404','PRIMARY_NAV':primary,'REFERENCE_NAV':reference,'CONTENT':'<h1>404</h1><p>That route fell out of the field. <a href="'+join_url(base_path,'/')+'">Return to EFI.</a></p>','END_MARK':html.escape(endmark,quote=True),'JSON_LD':'{}'}
    for k,v in vals.items(): notfound=notfound.replace('{{'+k+'}}',v)
    notfound=notfound.replace('<html lang="en">',f'<html lang="en" data-base-path="{html.escape(base_path,quote=True)}">'); (out/'404.html').write_text(notfound,encoding='utf-8')
    outputs={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file() and p.name!='build-manifest.json'}
    manifest={'schema':'efi.pages-build-manifest.v1','base_path':base_path,'base_url':base_url,'routes':manifest_routes,'outputs':outputs}
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'schema':'efi.pages-build.v1','routes':len(routes),'files':len(outputs)+1,'base_path':base_path,'out':str(out)},indent=2))
if __name__=='__main__': main()
