# Examples

Scripts that turn the release files in this repository into the charts of an article on [captaindrawdown.com](https://captaindrawdown.com/). Each one reads `v1/<release>/` straight from the clone and needs nothing beyond Python 3.9+ and matplotlib.

| Script | What it draws | Reads | Article |
|---|---|---|---|
| `eu27_company_maps.py` | EU27 carbon removal companies, one map per pathway, and all 27 member states as stacked bars (plus the table as CSV) | `companies.csv`, `researchers_by_country.csv`, `examples/world-110m.json` | [Sixteen of 27 EU member states have a carbon removal company, and biochar is why](https://captaindrawdown.com/posts/eu27-carbon-removal-companies-one-map-per-pathway/) |

```
git clone https://github.com/dirkpaessler/cdr-databases.git
cd cdr-databases
pip install matplotlib
python3 examples/eu27_company_maps.py --out charts/                    # release 2026-11.4, as in the article
python3 examples/eu27_company_maps.py --release latest --out charts/   # the newest release
```

The published charts are set in Inter and carry the Carbon Drawdown Initiative logo; the scripts fall back to a system font and draw no logo, the numbers are the same.

`world-110m.json` holds the country outlines: Natural Earth 1:110m (public domain) as TopoJSON from the [world-atlas](https://github.com/topojson/world-atlas) project (ISC licence).

The data keeps its licences (table in the main README): a chart built from `companies.csv` is CC BY-NC-SA 4.0, one built from the census files CC BY 4.0. Cite the release you used.
