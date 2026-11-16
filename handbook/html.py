#!/usr/bin/env python3
# handbook.md -> one html page per chapter and a contents page, in the site's style
# python3 html.py OUTDIR [handbook.md]
import html, os, re, sys, time

out = sys.argv[1]
src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'handbook.md')
slugs = ['about', 'preparing', 'installing', 'mag', 'rifle', 'base', 'kernel', 'iso', 'maintaining', 'files']

NAV = ('<a href="./">Home</a> |\n<a href="download.html">Install</a> |\n<b>Handbook</b> |\n'
       '<a href="packages.html">Packages</a> |\n<a href="new.html">News</a> |\n<a href="board.html">Board</a> |\n'
       '<a href="chat.html">Chat</a> |\n<a href="source.html">Source</a> |\n'
       '<a href="https://x22.chamesle.org/">X22</a> |\n<a href="about.html">About</a>')

def page(title, desc, url, body):
    t = html.escape(title)
    d = html.escape(desc)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t} - Chamesle</title>
<meta name="description" content="{d}">
<link rel="canonical" href="https://chamesle.org/{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Chamesle">
<meta property="og:title" content="{t} - Chamesle">
<meta property="og:description" content="{d}">
<meta property="og:url" content="https://chamesle.org/{url}">
<link rel="stylesheet" href="style.css?13">
</head>
<body>

<div id="page">

<div id="top">
<h1><a href="./">Chamesle</a></h1>
</div>

<div id="nav">
{NAV}
</div>

<main>
{body}
</main>

<hr>
<div id="foot">
Something wrong on this page? Tell us on the <a href="board.html">board</a>.<br>
Chamesle is installed by hand, from the <a href="docs.html">handbook</a>.<br>
<a href="https://ko-fi.com/L6N725GI1V">Ko-fi</a><br>
<a href="#" id="edit-link">Edit text</a><br>
$Date: {time.strftime('%Y-%m-%d')} $
</div>

</div>

<script src="edit.js"></script>
</body>
</html>
'''

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])', r'<i>\1</i>', s)
    return s

def ident(h):
    m = re.match(r'(\d+(?:\.\d+)*)\.? ', h)
    return 's' + m.group(1).replace('.', '-') if m else re.sub(r'\W+', '-', h.lower()).strip('-')

def render(lines):
    o = []
    i = 0
    n = len(lines)
    while i < n:
        l = lines[i]
        if not l.strip():
            i += 1
        elif l.startswith('### ') or l.startswith('#### '):
            h = l.lstrip('#').strip()
            lvl = 2 if l.startswith('### ') else 3
            o.append(f'<h{lvl} id="{ident(h)}">{inline(h)}</h{lvl}>')
            i += 1
        elif l.startswith('    '):
            c = []
            while i < n and (lines[i].startswith('    ') or (not lines[i].strip() and i + 1 < n and lines[i + 1].startswith('    '))):
                c.append(lines[i][4:])
                i += 1
            o.append('<pre>' + html.escape('\n'.join(c)) + '</pre>')
        elif l.startswith('|'):
            rows = []
            while i < n and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not re.fullmatch(r'[-: ]+', ''.join(r))]
            t = '<table>\n<tr>' + ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr>\n'
            for r in body:
                t += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>\n'
            o.append(t + '</table>')
        elif re.match(r'(\* |\d+\. )', l):
            tag = 'ul' if l.startswith('* ') else 'ol'
            items = []
            while i < n and re.match(r'(\* |\d+\. )', lines[i]):
                it = [re.sub(r'^(\* |\d+\. )', '', lines[i])]
                i += 1
                while i < n and lines[i].strip() and lines[i].startswith('  ') and not re.match(r'\s*(\* |\d+\. )', lines[i]):
                    it.append(lines[i].strip())
                    i += 1
                items.append(' '.join(it))
            o.append(f'<{tag}>\n' + '\n'.join(f'<li>{inline(x)}</li>' for x in items) + f'\n</{tag}>')
        else:
            p = []
            while i < n and lines[i].strip() and not re.match(r'(\* |\d+\. |#|\||    )', lines[i]):
                p.append(lines[i].strip())
                i += 1
            if not p:
                p = [l.strip()]
                i += 1
            o.append('<p>' + inline(' '.join(p)) + '</p>')
    return '\n'.join(o)

text = open(src).read().split('\n')
chapters = []
for l in text:
    if l.startswith('## '):
        chapters.append((l[3:].strip(), []))
    elif chapters:
        chapters[-1][1].append(l)

assert len(chapters) == len(slugs), 'chapters and slugs do not match'
os.makedirs(out, exist_ok=True)

def fname(k):
    return f'handbook-{slugs[k]}.html'

toc = ['<h2>The handbook</h2>', '<p><i>How to build, install and run Chamesle.</i></p>', '<ol>']
for k, (title, body) in enumerate(chapters):
    name = re.sub(r'^\d+\. ', '', title)
    subs = [l[4:].strip() for l in body if l.startswith('### ')]
    toc.append(f'<li><a href="{fname(k)}">{html.escape(name)}</a>')
    if subs:
        toc.append('<ul>' + ''.join(f'<li><a href="{fname(k)}#{ident(s)}">{html.escape(s)}</a></li>' for s in subs) + '</ul>')
    toc.append('</li>')
toc.append('</ol>')
open(os.path.join(out, 'docs.html'), 'w').write(page('Handbook', 'The Chamesle handbook, chapter by chapter: preparing, installing by hand, mag, rifle, the base system, the kernel, the live ISO and the files of the system.', 'docs.html', '\n'.join(toc)))

for k, (title, body) in enumerate(chapters):
    name = re.sub(r'^\d+\. ', '', title)
    bar = []
    if k: bar.append(f'<a href="{fname(k - 1)}">&larr; {html.escape(re.sub(r"^\d+\. ", "", chapters[k - 1][0]))}</a>')
    bar.append('<a href="docs.html">Contents</a>')
    if k < len(chapters) - 1: bar.append(f'<a href="{fname(k + 1)}">{html.escape(re.sub(r"^\d+\. ", "", chapters[k + 1][0]))} &rarr;</a>')
    nav = '<p>' + ' | '.join(bar) + '</p>'
    first = next((l for l in body if l.strip() and not l.startswith(('#', ' ', '|', '*'))), name)
    desc = re.sub(r'[`*]', '', first)[:200]
    b = f'{nav}\n<h2>{html.escape(title)}</h2>\n' + render(body) + f'\n<hr>\n{nav}'
    open(os.path.join(out, fname(k)), 'w').write(page(name, desc, fname(k), b))
print(len(chapters) + 1, 'pages in', out)
