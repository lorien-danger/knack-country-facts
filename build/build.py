"""
Make the dataset (../columns.json and ../rows.jsonl) from the copies in sources/ (made by fetch.py) and the choices
written down in this folder, and write checks.txt: every place where the sources disagree, and what was used.

  python3 build.py

Nothing is typed in by hand except what is in the *.tsv files here, each line with its reason.
"""
import csv, json, re, collections, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / 'sources'
TOP = HERE.parent

countries = json.load(open(SRC / 'countries.json'))
names = {c['id']: c['name'] for c in countries}
wd = json.load(open(SRC / 'wikidata.json'))
ml = {c['cca2'].lower(): c for c in json.load(open(SRC / 'mledoze.json'))}
cca3 = {c['cca3']: k for k, c in ml.items()}
boxes = json.load(open(SRC / 'infobox.json'))
wb = json.load(open(SRC / 'worldbank.json'))
gov_page = json.load(open(SRC / 'government.json'))
inv = {q: c for c, q in wd['qid'].items()}
checks = collections.defaultdict(list)

def tsv(name):
    return {r['id']: r for r in csv.DictReader((l for l in open(HERE / name) if not l.startswith('#')), delimiter='\t')}

def current(p):
    """each country's current values of a Wikidata property: statements without an end time and not deprecated,
    the preferred ones if any are preferred; each a dict with the value (v), its label and what was fetched with it"""
    by = collections.defaultdict(list)
    for s in wd['statements'][p]:
        if s.get('end') or s['rank'].endswith('DeprecatedRank'): continue
        by[inv[s['c']]].append(s)
    out = {}
    for c, ss in by.items():
        pref = [s for s in ss if s['rank'].endswith('PreferredRank')]
        seen, keep = set(), []
        for s in pref or ss:
            if s['v'] not in seen: seen.add(s['v']); keep.append(s)
        out[c] = keep
    return out

def label(s):
    return s.get('vLabel', s['v'])

# --- the infobox, for checking ---------------------------------------------------------------------------------
def field(c, name):
    m = re.search(r'\|\s*' + name + r'\s*=(.*?)(?=\n\s*\|\s*[a-z_0-9]+\s*=|\n\}\}\s*$)', boxes[c]['infobox'], re.S)
    return m.group(1).strip() if m else ''

def strip_notes(v):
    v = re.sub(r'<ref[^>/]*/>', '', v)
    v = re.sub(r'<ref.*?</ref>', '', v, flags=re.S)
    v = re.sub(r'<!--.*?-->', '', v, flags=re.S)
    out, i = '', 0
    while i < len(v):
        m = re.match(r'\{\{\s*(efn|notetag|sfn|refn|r|nbsp|citation needed|cn)\b', v[i:], re.I)
        if m:
            depth = 0
            while i < len(v):
                if v.startswith('{{', i): depth += 1; i += 2; continue
                if v.startswith('}}', i):
                    depth -= 1; i += 2
                    if depth == 0: break
                    continue
                i += 1
            continue
        out += v[i]; i += 1
    return out

def plain_text(v):
    v = strip_notes(v)
    v = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', v)
    v = re.sub(r'<[^>]+>', ' ', v)
    return re.sub(r'\s+', ' ', v).strip()

# --- name -------------------------------------------------------------------------------------------------------
rows = {c['id']: {'id': c['id'], 'name': c['name']} for c in countries}

# --- capital ----------------------------------------------------------------------------------------------------
CAPITAL_NAME = {'Q36262': "St. John's",   # no English label on Wikidata; the article is "St. John's, Antigua and Barbuda"
                'Yaren District': 'Yaren'}
capital_over = tsv('capitals.tsv')
caps = current('P36')
coords = {}
for c in names:
    ss = caps.get(c, [])
    got = [CAPITAL_NAME.get(s['v'], CAPITAL_NAME.get(label(s), label(s))) for s in ss]
    for s in ss:
        if s.get('coord'):
            lon, lat = map(float, re.match(r'Point\(([-\d.eE]+) ([-\d.eE]+)\)', s['coord']).groups())
            coords.setdefault(CAPITAL_NAME.get(s['v'], CAPITAL_NAME.get(label(s), label(s))), [round(lat, 2), round(lon, 2)])
    if c in capital_over:
        o = capital_over[c]
        got = [x for x in o['capital'].split(';') if x]
        checks['capital'].append(f"{names[c]}: {o['capital'] or '(none)'} — {o['why']}")
    m = ml[c]['capital']
    if sorted(got) != sorted(m) and c not in capital_over:
        checks['capital'].append(f"{names[c]}: Wikidata {got}, mledoze {m}; Wikidata used")
    if got:
        rows[c]['capital'] = got
        seat = capital_over[c]['seat'] if c in capital_over and capital_over[c].get('seat') else got[0]
        if seat in coords: rows[c]['capital place'] = coords[seat]
        else: checks['capital place'].append(f"{names[c]}: no coordinates for {seat}")
        if len(got) > 1: checks['capital place'].append(f"{names[c]}: the point is {seat}'s, of {got}")

# --- official languages -----------------------------------------------------------------------------------------
LANG_NAME = {'Bangla': 'Bengali', 'Putonghua': 'Chinese', 'Standard Chinese': 'Chinese', 'Modern Greek': 'Greek',
             'Guarani': 'Guaraní', 'Sesotho': 'Sotho', 'Southern Sotho': 'Sotho', 'Persian (Farsi)': 'Persian',
             'Kurdish language': 'Kurdish', 'Nauru': 'Nauruan', 'Norwegian Bokmål': 'Norwegian',
             'Norwegian Nynorsk': 'Norwegian', 'Bokmål': 'Norwegian', 'Nynorsk': 'Norwegian', 'Sami': 'Sámi',
             'Moldavian': 'Romanian', 'Swiss German': 'German', 'Austro-Bavarian German': 'German'}
lang_over = tsv('languages.tsv')
langs = current('P37')
for c in names:
    a = sorted({LANG_NAME.get(label(s), label(s)) for s in langs.get(c, []) if 'Sign Language' not in label(s)})
    b = sorted({LANG_NAME.get(x, x) for x in ml[c]['languages'].values() if 'Sign Language' not in x})
    if c in lang_over:
        got = [x for x in lang_over[c]['languages'].split(';') if x]
        checks['languages'].append(f"{names[c]}: Wikidata {a}, mledoze {b}: {got or '(none)'} — {lang_over[c]['why']}")
    elif a == b: got = a
    else:
        sys.exit(f'languages disagree for {names[c]}: Wikidata {a}, mledoze {b}; say which in languages.tsv')
    if got: rows[c]['languages'] = got

# --- currency ---------------------------------------------------------------------------------------------------
cur_over = tsv('currencies.tsv')
curs = current('P38')
GENERIC = {'dollar', 'pound', 'peso', 'franc', 'rupee', 'dinar', 'shilling', 'rand', 'mark', 'som', 'won', 'yuan'}
CURRENCY_NAME = {'Euro': 'euro', 'lari': 'Georgian lari', 'denar': 'Macedonian denar'}
for c in names:
    m = [v['name'] for v in ml[c].get('currencies', {}).values()]
    w = [label(s) for s in curs.get(c, [])]
    if c in cur_over:
        got = [x for x in cur_over[c]['currency'].split(';') if x]
        checks['currency'].append(f"{names[c]}: Wikidata {w}, mledoze {m}: {got or '(none)'} — {cur_over[c]['why']}")
    else:
        # mledoze's, but where it gives several, only those Wikidata or the Wikipedia infobox also gives
        text = plain_text(field(c, 'currency')).lower()
        def said(x):   # the whole name, or its last word where that is not shared by many (riel, but not dollar)
            last = x.lower().split()[-1]
            return x.lower() in text or x.lower() in [y.lower() for y in w] or (
                last not in GENERIC and (last in text or any(last in y.lower() for y in w)))
        got = [x for x in m if len(m) == 1 or said(x)]
        got = [CURRENCY_NAME.get(x, x) for x in got]
        if sorted(x.lower() for x in w) != sorted(x.lower() for x in got):
            checks['currency'].append(f"{names[c]}: Wikidata {w}, mledoze {m}; {got} used")
    if got: rows[c]['currency'] = got

# --- land borders -----------------------------------------------------------------------------------------------
for c in names:
    nb = []
    for x in ml[c]['borders']:
        k = cca3.get(x)
        if k in names: nb.append(names[k])
        else: checks['neighbours'].append(f"{names[c]}: border with {x} left out (not one of the 198)")
    if nb: rows[c]['neighbours'] = sorted(nb)
# Wikidata's "shares border with" (P47) mixes land and sea borders, so it is only used to check: a land border
# mledoze gives that Wikidata does not have is listed
p47 = collections.defaultdict(set)
for s in wd['statements']['P47']:
    if s['rank'].endswith('DeprecatedRank') or s.get('end'): continue
    if s['v'] in inv: p47[inv[s['c']]].add(names[inv[s['v']]])
for c in names:
    miss = [n for n in rows[c].get('neighbours', []) if n not in p47[c]]
    if miss: checks['neighbours'].append(f"{names[c]}: land border with {miss} not in Wikidata P47")

for c in names:
    rows[c]['landlocked'] = 'landlocked' if ml[c]['landlocked'] else 'has a coast'

# --- driving side -----------------------------------------------------------------------------------------------
drive = current('P1622')
for c in names:
    v = sorted({label(s) for s in drive.get(c, [])})
    if len(v) != 1: checks['drives on'].append(f"{names[c]}: Wikidata {v}"); continue
    rows[c]['drives on'] = v[0]
    ib = plain_text(field(c, 'drives_on')).lower()
    if ib and v[0] not in ib: checks['drives on'].append(f"{names[c]}: Wikidata {v[0]}, Wikipedia infobox '{ib}'")

# --- calling code -----------------------------------------------------------------------------------------------
code_over = tsv('calling.tsv')
codes = current('P474')
def nanp(code):
    return code.startswith('+1') and len(code) > 2
for c in names:
    w = sorted({re.sub(r'[\s-]', '', label(s)) for s in codes.get(c, [])})
    idd = ml[c]['idd']
    m = sorted({idd['root'] + x for x in idd['suffixes']}) if len(idd.get('suffixes', [])) <= 3 else [idd['root']]
    if c in code_over:
        code = code_over[c]['code']
        checks['calling code'].append(f"{names[c]}: Wikidata {w}, mledoze {m}: {code} — {code_over[c]['why']}")
    elif len(w) == 1:
        code = w[0]
        if code not in m: checks['calling code'].append(f"{names[c]}: Wikidata {w}, mledoze {m}; Wikidata used")
    else:
        sys.exit(f'calling code for {names[c]}: Wikidata {w}, mledoze {m}; say which in calling.tsv')
    ib = re.sub(r'[\s-]', '', plain_text(field(c, 'calling_code')))
    if code.replace(' ', '') not in ib: checks['calling code'].append(f"{names[c]}: {code}; Wikipedia infobox '{ib}'")
    # a tree: the world zone (the first digit), then the code; in zone 1 (the North American Numbering Plan) the
    # code is +1 and an area code
    if code.startswith('+1'):
        rows[c]['calling code'] = ['+1'] + ([f'+1 {code[2:]}'] if len(code) > 2 else [])
    elif code == '+7':
        rows[c]['calling code'] = ['+7']
    else:
        rows[c]['calling code'] = [f'+{code[1]}…', code]

# --- internet domain --------------------------------------------------------------------------------------------
tlds = current('P78')
for c in names:
    w = [label(s) for s in tlds.get(c, []) if re.fullmatch(r'\.[a-z]{2}', label(s))]
    m = [t for t in ml[c]['tld'] if re.fullmatch(r'\.[a-z]{2}', t)]
    got = m[0] if m else None
    if not w or w[0] != got: checks['internet domain'].append(f"{names[c]}: Wikidata {w}, mledoze {ml[c]['tld']}; mledoze used")
    if got: rows[c]['internet domain'] = got

# --- highest point ----------------------------------------------------------------------------------------------
top_over = tsv('highest.tsv')
tops = current('P610')
elev = collections.defaultdict(list)
for e in wd['elevation']:
    if e['unit'] != 'Q11573' or e['rank'].endswith('DeprecatedRank'): continue   # metres only
    elev[e['v']].append((e['rank'].endswith('PreferredRank'), float(e['elev'])))
for c in names:
    ss = tops.get(c, [])
    if c in top_over:
        o = top_over[c]
        if o['point']: rows[c]['highest point'] = o['point']; rows[c]['highest point (m)'] = int(o['metres'])
        checks['highest point'].append(f"{names[c]}: Wikidata {[label(s) for s in ss]}: {o['point'] or '(none)'} {o['metres']} — {o['why']}")
        continue
    if len(ss) != 1:
        checks['highest point'].append(f"{names[c]}: Wikidata {[label(s) for s in ss]}; left out"); continue
    s = ss[0]
    es = elev.get(s['v'], [])
    pref = [x for p, x in es if p] or [x for p, x in es]
    if not pref: checks['highest point'].append(f"{names[c]}: no elevation in metres for {label(s)}"); continue
    if len({round(x) for x in pref}) > 1:
        checks['highest point'].append(f"{names[c]}: {label(s)} has elevations {sorted(pref)}; the highest used")
    rows[c]['highest point'] = label(s)
    rows[c]['highest point (m)'] = round(max(pref))

# Wikipedia's list of elevation extremes, to check: where its point or height differs (by more than 1%), say so
ext = {}
for rec in json.load(open(SRC / 'elevation.json'))['wikitext'].split('\n|-'):
    m = re.search(r'^\s*[^\n]*\n\|\{\{([A-Z]{3})\}\}\s*\n\|(.*?)\{\{epi/moft\|(-?[\d.]+)', rec, re.S)
    if m and m.group(1) in cca3: ext[cca3[m.group(1)]] = (plain_text(m.group(2)), float(m.group(3)))
for c in names:
    r = rows[c]
    if 'highest point' not in r or c in top_over: continue
    if c not in ext: checks['highest point'].append(f"{names[c]}: not in Wikipedia's list"); continue
    n, h = ext[c]
    if abs(h - r['highest point (m)']) > max(5, 0.01 * h) or n.split()[0].lower()[:4] not in r['highest point'].lower():
        checks['highest point'].append(f"{names[c]}: {r['highest point']} {r['highest point (m)']} m; Wikipedia's list: {n} {h:g} m")

# --- form of government -----------------------------------------------------------------------------------------
GOV_ALIAS = {'Czech Republic': 'Czechia', 'Georgia (country)': 'Georgia', 'Cape Verde': 'Cabo Verde',
             'Timor-Leste': 'East Timor', 'Federated States of Micronesia': 'Micronesia', 'Vatican City': 'Vatican',
             'Kingdom of Denmark': 'Denmark', 'Kingdom of the Netherlands': 'Netherlands'}
GOV_PATH = [  # the article's sections, most particular first, and the path in this dataset's tree
    ('Military juntas', ['provisional government', 'military junta']),
    ('Provisional governments', ['provisional government']),
    ('One-party states', ['one-party state']),
    ('Islamic theocracy', ['theocracy']),
    ('Theocratic presidential republic', ['theocracy']),
    ('Absolute monarchies', ['monarchy', 'absolute']),
    ('Semi-constitutional monarchies', ['monarchy', 'semi-constitutional']),
    ('Parliamentary constitutional monarchies', ['monarchy', 'constitutional']),
    ('Parliamentary republics with an executive presidency', ['republic', 'parliamentary', 'executive president']),
    ('Parliamentary republics', ['republic', 'parliamentary', 'ceremonial president']),
    ('Presidential republics without a prime minister', ['republic', 'presidential', 'no prime minister']),
    ('Presidential republics with a prime minister', ['republic', 'presidential', 'with a prime minister']),
    ('Semi-presidential republics', ['republic', 'semi-presidential']),
    ('Assembly-independent republic', ['republic', 'assembly-independent']),
]
gov_found = collections.defaultdict(list)
sec = []
for line in gov_page['wikitext'].split('\n'):
    m = re.match(r'^(=+)\s*(.*?)\s*=+\s*$', line)
    if m: sec = sec[:len(m.group(1)) - 2] + [m.group(2)]; continue
    if 'Systems of internal structure' in sec or 'European Union' in sec: continue
    m = re.match(r"^\s*['*]*\s*\{\{[Ff]lag(?:country|icon|u)?\|([^}|]+)", line)
    if m:
        n = GOV_ALIAS.get(m.group(1).strip(), m.group(1).strip())
        gov_found[n].append(sec)
gov_over = tsv('government.tsv')
by_name = {v: k for k, v in names.items()}
for n, secs in gov_found.items():
    if n not in by_name: checks['government'].append(f"{n} in the article is not one of the 198"); continue
for c, n in names.items():
    if c in gov_over:
        o = gov_over[c]
        if o['path']: rows[c]['government'] = o['path'].split(';')
        checks['government'].append(f"{n}: {o['path'] or '(none)'} — {o['why']}"); continue
    paths = []
    for s in gov_found.get(n, []):
        for title, path in GOV_PATH:
            if title in s: paths.append(path); break
    if not paths: checks['government'].append(f"{n}: not in the article"); continue
    best = min(paths, key=lambda p: [x[1] for x in GOV_PATH].index(p))
    if len({tuple(p) for p in paths}) > 1: checks['government'].append(f"{n}: in {paths}; {best} used")
    rows[c]['government'] = best

# --- demonym ----------------------------------------------------------------------------------------------------
dem = collections.defaultdict(set)
for s in wd['statements']['P1549']: dem[inv[s['c']]].add(s['v'])
for c in names:
    m = ml[c].get('demonyms', {}).get('eng', {}).get('m')
    if not m: continue
    d = m
    if not all(x in dem[c] for x in re.split(r', | or ', m)):
        # mledoze's unless Wikidata has others and the Wikipedia infobox says one of those (the first it says)
        text = plain_text(field(c, 'demonym'))
        found = [(text.find(x), x) for x in sorted(dem[c]) if re.search(r'\b' + re.escape(x) + r'\b', text)]
        d = min(found)[1] if found and not re.search(r'\b' + re.escape(m) + r'\b', text) else m
        checks['demonym'].append(f"{names[c]}: mledoze {m}, Wikidata {sorted(dem[c])}, Wikipedia '{text[:60]}'; {d} used")
    rows[c]['demonym'] = d

# --- World Bank -------------------------------------------------------------------------------------------------
WB = {'NY.GDP.PCAP.CD': ('GDP per person', lambda x: round(x)), 'SP.DYN.LE00.IN': ('life expectancy', lambda x: round(x, 1))}
years = collections.defaultdict(collections.Counter)
for ind, (col, rnd) in WB.items():
    got = {r['iso3']: r for r in wb[ind]}
    for c in names:
        r = got.get(ml[c]['cca3'])
        if not r: checks[col].append(f"{names[c]}: none"); continue
        if r['year'] < '2022': checks[col].append(f"{names[c]}: the latest is from {r['year']}; left out"); continue
        rows[c][col] = rnd(r['value'])
        years[col][r['year']] += 1

# --- write ------------------------------------------------------------------------------------------------------
ORDER = ['name', 'capital', 'capital place', 'languages', 'currency', 'neighbours', 'landlocked', 'drives on',
         'calling code', 'internet domain', 'highest point', 'highest point (m)', 'government', 'demonym',
         'GDP per person', 'life expectancy']
meta = json.load(open(HERE / 'columns.json'))
assert [c['name'] for c in meta['columns']] == ORDER, [c['name'] for c in meta['columns']]
json.dump(meta, open(TOP / 'columns.json', 'w'), ensure_ascii=False, indent=1)
with open(TOP / 'rows.jsonl', 'w') as f:
    for c in names:
        r = rows[c]
        f.write(json.dumps({'id': c, **{k: r[k] for k in ORDER if k in r}}, ensure_ascii=False) + '\n')

with open(HERE / 'checks.txt', 'w') as f:
    f.write('Where the sources disagree, and what was used (written by build.py)\n')
    for col in ORDER:
        n = sum(1 for r in rows.values() if col in r)
        f.write(f'\n## {col}: {n} of {len(rows)} countries have it\n')
        if col in years: f.write(f'years of the figures: {dict(sorted(years[col].items()))}\n')
        for line in checks.get(col, []): f.write(line + '\n')
for col in ORDER: print(f'{col:20} {sum(1 for r in rows.values() if col in r)}')
