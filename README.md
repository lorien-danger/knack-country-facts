# Country facts

Facts about the 198 countries of [knack-countries](https://github.com/lorien-danger/knack-countries): the capital
and where it is, the official languages, the currency, the countries each one borders on land, whether it has a
coast, which side of the road people drive on, its calling code and internet domain, its highest point and how high
that is, its form of government, what its people are called, GDP per person and life expectancy. A dataset for
[Knack](https://github.com/lorien-danger/knack): add it by this repo's link.

It is meant to be used with knack-countries: the `name` column has exactly the names in knack-countries'
`rows.jsonl` (and the same `id`, the ISO 3166-1 alpha-2 code), so a deck can show a flag or a shape from there and ask
a fact from here. It has none of what knack-countries has (flag, shape, region, population, size).

Suggested decks: **Capitals of the countries** (country, capital, where the capital is), **Countries' languages and
money** (country, official languages, currency) and **Countries' calling codes and web domains** (country, calling
code, internet domain).

## Columns

| column | label in the app | type | what it is | from |
| --- | --- | --- | --- | --- |
| name | Country | plain | the country's name, as in knack-countries | knack-countries |
| capital | Capital | parts | the capital; several where a country has several (Bolivia, Eswatini, Palestine, South Africa, Sri Lanka, Yemen), the seat of government first | Wikidata, checked against mledoze/countries |
| capital place | Where the capital is | sphere | where the (first) capital is, latitude and longitude to 2 decimals | Wikidata |
| languages | Official languages | parts | the official languages of the whole country; sign languages left out | Wikidata and mledoze/countries, settled with Wikipedia where they disagree |
| currency | Currency | parts | the currencies in use as legal tender | mledoze/countries, checked against Wikidata and Wikipedia |
| neighbours | Land neighbours | parts | the countries it shares a land border with, by their names here; missing for the 39 that have none | mledoze/countries, checked against Wikidata |
| landlocked | Coast | plain | "has a coast" or "landlocked" | mledoze/countries |
| drives on | Drives on the | plain | left or right | Wikidata, checked against Wikipedia |
| calling code | Calling code | tree | the world zone (the first digit), then the code: +2… › +27; in zone 1 (North America and the Caribbean) +1 and the area code: +1 › +1 876 | Wikidata, checked against mledoze/countries and Wikipedia |
| internet domain | Internet domain | plain | the country-code top-level domain (.uk) | mledoze/countries, checked against Wikidata |
| highest point | Highest point | plain | its highest point's name | Wikidata, checked against Wikipedia's list of elevation extremes |
| highest point (m) | Height of the highest point | number (log) | its height in metres | Wikidata, checked the same way |
| government | Government | tree | the system of government: republic › parliamentary › ceremonial president, monarchy › absolute, one-party state… | Wikipedia, List of countries by system of government |
| demonym | People are called | plain | the word for its people (French, Ivorian) | mledoze/countries, checked against Wikidata and Wikipedia |
| GDP per person | GDP per person | number (log) | gross domestic product per person, current US dollars, rounded to the dollar (shown to 2 digits) | World Bank |
| life expectancy | Life expectancy | number | life expectancy at birth, years, to one decimal (shown to 2 digits) | World Bank |

### The government tree

    republic      parliamentary        ceremonial president (43), executive president (6)
                  presidential         no prime minister (35), with a prime minister (17)
                  semi-presidential (28), assembly-independent (5)
    monarchy      constitutional (28), semi-constitutional (10), absolute (5)
    one-party state (6)
    theocracy (2: Afghanistan, Iran)
    provisional government (6)   military junta (6)

The branches are the sections of the Wikipedia article, as they stand in the revision read (its id is in
`build/sources/government.json`). Where a country is in two sections the more particular is used (a military junta
over the system it replaced).

### What is missing, and why

| column | countries | missing |
| --- | --- | --- |
| capital, capital place | 197 | Western Sahara: disputed; no source gives it a capital |
| languages | 197 | Burkina Faso: its 2024 charter made "all national languages" official without naming them |
| neighbours | 159 | the 39 with no land border |
| highest point, height | 188 | Gambia, Maldives, Western Sahara (no named point); Colombia (two peaks of unknown order); Bangladesh, Ghana, Guinea-Bissau, Kuwait, Micronesia, Senegal (Wikidata and Wikipedia name different points) |
| government | 197 | Western Sahara |
| GDP per person | 189 | Kosovo, North Korea, Taiwan, Vatican, Western Sahara (none); Cuba, Eritrea, South Sudan, Yemen (none since 2021) |
| life expectancy | 194 | Kosovo, Taiwan, Vatican, Western Sahara |

Every other column is there for all 198.

## Sources

- [Wikidata](https://www.wikidata.org/) (CC0): capitals (P36) and their coordinates (P625), official languages
  (P37), currency (P38), shares border with (P47), driving side (P1622), calling code (P474), internet domain (P78),
  highest point (P610) and its elevation (P2044), demonym (P1549). Each country's item is found by its ISO code
  (P297). The current statements are used: none with an end date, the preferred ones where some are preferred.
- [mledoze/countries](https://github.com/mledoze/countries) (ODbL 1.0): land borders, landlocked, currencies,
  languages, capitals, calling codes, internet domains, demonyms.
- English Wikipedia (CC BY-SA 4.0): the article
  [List of countries by system of government](https://en.wikipedia.org/wiki/List_of_countries_by_system_of_government)
  for the government column; [List of elevation extremes by country](https://en.wikipedia.org/wiki/List_of_elevation_extremes_by_country)
  and the infobox of each country's article, to check the other columns and to settle where Wikidata and mledoze
  disagree. The revisions read are in `build/sources/`.
- [World Bank World Development Indicators](https://data.worldbank.org/) (CC BY 4.0): GDP per capita (current US$,
  NY.GDP.PCAP.CD) and life expectancy at birth (SP.DYN.LE00.IN), each country's most recent figure.
- [knack-countries](https://github.com/lorien-danger/knack-countries) (ODbL): the names and ids.

## How it was checked

`build/build.py` compares every column that has two or three sources and writes every disagreement, and what was
done about it, to [`build/checks.txt`](build/checks.txt). Where the sources disagree on something that matters, the
choice is written by hand with its reason in a TSV in `build/` (`capitals.tsv`, `languages.tsv`,
`currencies.tsv`, `calling.tsv`, `highest.tsv`, `government.tsv`): for example, Serbia's highest point is Midžor,
because Wikidata's Velika Rudoka is in Kosovo; Finland's is on Halti's slope at 1324 m, because the summit is in
Norway; the official languages of 65 countries were settled by what two of the three sources give.

What agrees across sources: capitals for all but spelling (Reykjavík, Ulaanbaatar…) and the countries with several;
calling codes and internet domains for all; driving side for every country whose infobox says; land borders all
appear in Wikidata's P47. Of the 174 highest points that are in Wikipedia's list and were not settled by hand, 144
have the same point and height (within 1%); the other 30 are listed in `checks.txt`: most are other names for the
same mountain (Kanchenjunga, Paektu-san), the rest heights that differ by a few metres to 2% between surveys (Mount
Cameroon 4095 or 4040 m, Khüiten Peak 4374 or 4356 m).

Checked by hand, every fact, against the country's Wikipedia article: Ivory Coast, Costa Rica, Madagascar, Sri Lanka,
Bahrain, Benin and Peru (chosen at random), and the United States, France, Australia, China and South Africa.

And in the Knack app, at phone size: every column on the Columns screen, shown and asked, and each suggested deck
practised.

## What goes out of date

As of November 2026 (the sources were read on the date in `build/sources/FETCHED`):

- **Government** changes with coups and new constitutions (Madagascar's junta from October 2025, the six provisional
  governments). **Capitals** move rarely but do (Equatorial Guinea's is Ciudad de la Paz since 2026; Indonesia's
  is still Jakarta here).
- **Official languages** change with new constitutions and charters (Mali 2023, Niger 2025, Burkina Faso 2024, the
  United States 2025).
- **Currencies** change (Zimbabwe Gold since 2024; Sierra Leone and others have redenominated).
- **GDP per person** is for 2025 for 181 countries (2022 to 2024 for the rest) and **life expectancy** for 2024: the
  World Bank revises both and adds a year each summer.
- Highest-point heights are changed by new surveys (Everest 8849 m since 2020).

Borders, driving sides, calling codes, domains and demonyms change very rarely.

## Lining up with the other datasets

- **knack-countries**: all 198 names and ids are the same, by construction (`build/fetch.py` copies them).
- **knack-landmarks**: its `country` column has 79 distinct values; 76 are names here. The ones that differ:
  `Czech Republic` (here `Czechia`, 1 landmark), `Vatican City` (here `Vatican`, 1 landmark), and the 3 landmarks in
  Antarctica with no country.

## Building it

`build/` makes the dataset with Python 3 and nothing else:

    cd build
    python3 fetch.py      # download the sources into build/sources/ (already there: the copies used)
    python3 build.py      # columns.json and rows.jsonl, and checks.txt

`build/columns.json` is the column definitions (labels, units, suggested decks); `build.py` copies it to the top.

## Licence

Because it is made from mledoze/countries (ODbL), this database is made available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/) (`LICENSE`), like knack-countries. It also
draws on Wikidata (CC0), the World Bank (CC BY 4.0: "World Bank, World Development Indicators") and Wikipedia
(CC BY-SA 4.0: Wikipedia contributors, the articles named above). The build scripts may be used freely.
