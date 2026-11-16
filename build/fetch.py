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
- government.json: the English Wikipedia article "List of countries by system of government" (CC BY-SA 4.0), its
  wikitext and revision id, for the form of government.
"""
import json, sys, time, datetime, urllib.parse, urllib.request
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
    json.dump({'qid': qid, 'labels': labels, 'props': PROPS, 'statements': props}, open(OUT / 'wikidata.json', 'w'),
              ensure_ascii=False, indent=0)
    (OUT / 'mledoze.json').write_bytes(get(MLEDOZE))
    for page, file in [('List of countries by system of government', 'government.json')]:
        j = json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'parse', 'page': page, 'prop': 'wikitext|revid', 'format': 'json', 'formatversion': 2})))
        json.dump({'page': page, 'revid': j['parse']['revid'], 'wikitext': j['parse']['wikitext']},
                  open(OUT / file, 'w'), ensure_ascii=False)
    (OUT / 'FETCHED').write_text(datetime.date.today().isoformat() + '\n')
