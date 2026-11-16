"""
Download what this dataset is made from into build/sources/, so build.py works from fixed copies (and anyone can see
exactly what it read). Run it again to take newer versions; the date is written to sources/FETCHED.

  python3 fetch.py

- countries.json: the 198 countries of knack-countries (id = ISO 3166-1 alpha-2, name), copied from its rows.jsonl
  (only id and name) so this dataset's names are exactly that dataset's.
- wikidata.json: from Wikidata (CC0), by SPARQL: each country's item (found by its ISO 3166-1 alpha-2 code, P297),
  and for each property used every statement on it, with its rank, its start and end time, the English label of
  the item it points at, and for capitals and highest points that item's coordinates and elevation.
- mledoze.json: mledoze/countries (ODbL): land borders, demonyms, calling codes, internet domains, capitals,
  currencies and languages.
- infobox.json: the infobox of each country's English Wikipedia article (CC BY-SA 4.0) and its revision id, the
  third source where the others disagree (official languages, capitals) and for checking.
- worldbank.json: the World Bank's World Development Indicators (CC BY 4.0), each country's most recent GDP per
  person and life expectancy, with the year.
- government.json: the English Wikipedia article "List of countries by system of government" (CC BY-SA 4.0), its
  wikitext and revision id, for the form of government.
"""
import json, re, sys, time, datetime, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'sources'
UA = {'User-Agent': 'knack-country-facts-build/1.0 (https://github.com/lorien-danger/knack-country-facts)'}
COUNTRIES = 'https://raw.githubusercontent.com/lorien-danger/knack-countries/main/rows.jsonl'
MLEDOZE = 'https://raw.githubusercontent.com/mledoze/countries/master/countries.json'
# Wikidata items by ISO code where the code's item is not the country itself
ITEM = {'nl': 'Q55',    # NL is on the Kingdom of the Netherlands (Q29999); the country in Europe is Q55
        'cy': 'Q229'}   # CY is also on the island (Q644636)
PROPS = {'P36': 'capital', 'P38': 'currency', 'P37': 'official language', 'P47': 'shares border with',
         'P1622': 'driving side', 'P474': 'country calling code', 'P78': 'top-level Internet domain',
         'P610': 'highest point', 'P571': 'inception', 'P122': 'basic form of government', 'P85': 'anthem',
         'P30': 'continent', 'P1549': 'demonym'}

# World Bank World Development Indicators (CC BY 4.0): each country's most recent value
WORLDBANK = {'NY.GDP.PCAP.CD': 'GDP per person (current US$)', 'SP.DYN.LE00.IN': 'life expectancy at birth (years)'}

def get(url):
    for k in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r: return r.read()
        except Exception as e:
            print('  retry:', e, file=sys.stderr); time.sleep(5 * (k + 1))
    raise RuntimeError(url)

def sparql(q):
    j = json.loads(get('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})))
    return [{k: v['value'].replace('http://www.wikidata.org/entity/', '') for k, v in b.items()} for b in j['results']['bindings']]

def statements(qids, p):
    vals = ' '.join('wd:' + q for q in qids)
    return sparql(f'''
SELECT ?c ?v ?vLabel ?rank ?start ?end ?coord ?elev ?elevUnit ?lang WHERE {{
  VALUES ?c {{ {vals} }}
  ?c p:{p} ?s . ?s ps:{p} ?v ; wikibase:rank ?rank .
  OPTIONAL {{ ?s pq:P580 ?start }} OPTIONAL {{ ?s pq:P582 ?end }}
  OPTIONAL {{ ?v wdt:P625 ?coord }}
  OPTIONAL {{ ?v p:P2044/psv:P2044 [ wikibase:quantityAmount ?elev ; wikibase:quantityUnit ?elevUnit ] }}
  BIND(LANG(?v) AS ?lang)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}''')

def infobox(text):
    """the first {{Infobox ...}} template, by matching braces"""
    m = re.search(r'\{\{\s*Infobox', text, re.I)
    if not m: return ''
    depth, i = 0, m.start()
    while i < len(text):
        if text.startswith('{{', i): depth += 1; i += 2; continue
        if text.startswith('}}', i):
            depth -= 1; i += 2
            if depth == 0: return text[m.start():i]
            continue
        i += 1
    return text[m.start():]

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    countries = [{'id': r['id'], 'name': r['name']} for r in map(json.loads, get(COUNTRIES).decode().splitlines())]
    (OUT / 'countries.json').write_text(json.dumps(countries, ensure_ascii=False, indent=0))
    iso = {}
    for b in sparql('SELECT ?item ?iso WHERE { ?item wdt:P297 ?iso }'):
        iso.setdefault(b['iso'].lower(), []).append(b['item'])
    qid = {}
    for c in countries:
        qs = iso.get(c['id'], [])
        qid[c['id']] = ITEM.get(c['id']) or (qs[0] if len(qs) == 1 else None)
        if not qid[c['id']]: print('NO ITEM', c, qs, file=sys.stderr)
    labels = {b['c']: b['cLabel'] for b in sparql('SELECT ?c ?cLabel WHERE { VALUES ?c { %s } SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }' % ' '.join('wd:' + q for q in qid.values()))}
    props = {}
    for p in PROPS:
        props[p] = [b for b in statements(list(qid.values()), p) if b.get('lang') in (None, '', 'en')]
        print(p, PROPS[p], len(props[p]), file=sys.stderr)
        time.sleep(2)
    # the elevation (P2044) of each highest point, every statement with its rank and unit
    tops = sorted({b['v'] for b in props['P610']})
    elev = sparql('''SELECT ?v ?elev ?unit ?rank WHERE { VALUES ?v { %s } ?v p:P2044 ?s . ?s wikibase:rank ?rank ;
      psv:P2044 [ wikibase:quantityAmount ?elev ; wikibase:quantityUnit ?unit ] }''' % ' '.join('wd:' + q for q in tops))
    json.dump({'qid': qid, 'labels': labels, 'props': PROPS, 'statements': props, 'elevation': elev}, open(OUT / 'wikidata.json', 'w'),
              ensure_ascii=False, indent=0)
    (OUT / 'mledoze.json').write_bytes(get(MLEDOZE))
    wb = {}
    for ind in WORLDBANK:
        j = json.loads(get(f'https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&mrnev=1&per_page=500'))
        wb[ind] = [{'iso3': r['countryiso3code'], 'name': r['country']['value'], 'year': r['date'], 'value': r['value']}
                   for r in j[1] if r['value'] is not None]
    json.dump(wb, open(OUT / 'worldbank.json', 'w'), indent=0)
    for page, file in [('List of countries by system of government', 'government.json')]:
        j = json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'parse', 'page': page, 'prop': 'wikitext|revid', 'format': 'json', 'formatversion': 2})))
        json.dump({'page': page, 'revid': j['parse']['revid'], 'wikitext': j['parse']['wikitext']},
                  open(OUT / file, 'w'), ensure_ascii=False)
    # each country's English Wikipedia infobox (CC BY-SA 4.0): the third source for the facts the other two disagree on
    titles = {b['c']: b['article'] for b in sparql('SELECT ?c ?article WHERE { VALUES ?c { %s } ?article schema:about ?c ; schema:isPartOf <https://en.wikipedia.org/> }' % ' '.join('wd:' + q for q in qid.values()))}
    boxes = {}
    for c, q in qid.items():
        t = urllib.parse.unquote(titles[q].split('/wiki/')[-1]).replace('_', ' ')
        j = json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'titles': t, 'redirects': 1, 'prop': 'revisions', 'rvprop': 'ids|content',
            'rvslots': 'main', 'rvsection': 0, 'format': 'json', 'formatversion': 2})))
        p = j['query']['pages'][0]; rev = p['revisions'][0]
        boxes[c] = {'article': p['title'], 'revid': rev['revid'], 'infobox': infobox(rev['slots']['main']['content'])}
    json.dump(boxes, open(OUT / 'infobox.json', 'w'), ensure_ascii=False, indent=0)
    (OUT / 'FETCHED').write_text(datetime.date.today().isoformat() + '\n')
