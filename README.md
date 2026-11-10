# Captain Drawdown's CDR Databases

Open datasets on carbon dioxide removal (CDR), maintained daily by CaptainDrawdown, an AI run by the [Carbon Drawdown Initiative](https://www.carbon-drawdown.de/), and published monthly. Documentation, method and changelog: [captaindrawdown.com/data](https://captaindrawdown.com/data/).

**Newest release 2026-11.4** (data as of 2026-11-05): 913 published carbon removal companies, 55,865 researchers with a CDR paper since 2021, 14 shops.

## Layout

One folder per release under `v1/`, the newest also under `v1/latest/`; `manifest.json` lists every file with row counts and SHA-256 checksums. Every release is also a tag (`release-<version>`) with a GitHub release that carries the folder as a zip and the main files.

| Dataset | Files | Licence | DOI |
|---|---|---|---|
| CDR Company Directory | `companies.csv`, `companies.json` | CC BY-NC-SA 4.0 | [10.5281/zenodo.23957359](https://doi.org/10.5281/zenodo.23957359) |
| CDR Researcher Census | `researchers_*.csv`, `top100_*.csv`, `top50_europe_*.csv`, `top100_cited_*.csv`, `*_papers.csv` | CC BY 4.0 | [10.5281/zenodo.23957367](https://doi.org/10.5281/zenodo.23957367) |
| CDR Shops | `shops.csv`, `shops.json` | CC BY 4.0 | [10.5281/zenodo.23957405](https://doi.org/10.5281/zenodo.23957405) |

## Cite as

- Captain Drawdown and Dirk Paessler (2026). CDR Company Directory, version 2026-11.4. Carbon Drawdown Initiative. https://captaindrawdown.com/data/companies/ (CC licence, see page). https://doi.org/10.5281/zenodo.23957359
- Captain Drawdown and Dirk Paessler (2026). CDR Researcher Census, version 2026-11.4. Carbon Drawdown Initiative. https://captaindrawdown.com/data/researchers/ (CC licence, see page). https://doi.org/10.5281/zenodo.23957367
- Captain Drawdown and Dirk Paessler (2026). CDR Shops, version 2026-11.4. Carbon Drawdown Initiative. https://captaindrawdown.com/data/shops/ (CC licence, see page). https://doi.org/10.5281/zenodo.23957405

## Get the data

Use the data where it lives, not a copy: `v1/latest/`, the JSON API and the MCP server always serve the newest release; pin `v1/<version>/` only for a result that must not change.

- Hand your assistant the map: `v1/latest/manifest.json` (also at https://captaindrawdown.com/data/v1/latest/manifest.json) lists every file with description, row count, size, licence and SHA-256. Paste that address into Claude, ChatGPT or Gemini, ask your question, and the assistant picks the file and quotes the version.
- Browse a release folder (`v1/<version>/`) and open any CSV or JSON here on GitHub; `v1/latest/` is always the newest release.
- One zip per release on the [Releases](https://github.com/dirkpaessler/cdr-databases/releases) page.
- Straight into pandas: `pd.read_csv("https://raw.githubusercontent.com/dirkpaessler/cdr-databases/main/v1/latest/companies.csv")`
- Everything with history: `git clone https://github.com/dirkpaessler/cdr-databases.git`
- JSON API without a key: https://captaindrawdown.com/api/ · MCP server for Claude, ChatGPT and Cursor: `pip install captain-drawdown-mcp` · Hugging Face: https://huggingface.co/carbondrawdowninitiative · Zenodo: archived copies with DOIs (table above).

## Examples

`examples/` holds the scripts behind the charts of the articles on captaindrawdown.com, each one reading `v1/<release>/` from a clone of this repository with nothing but Python and matplotlib: `eu27_company_maps.py`. See [examples/README.md](examples/README.md).

## Corrections

The data is AI-maintained and may contain errors. Open an issue here or write to info@carbon-drawdown.de. Person-level data exists only for the researchers in the public top lists; everyone else appears in aggregates (see https://captaindrawdown.com/privacy/).

Releases in this repository: 2026-11.4.
