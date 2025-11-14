# epstein-docs-search
This app provides an [easily searchable repository of the documents](https://www.dmolitor.com/epstein-docs-search/)
from the Epstein estate released by the US House Oversight Committee.

> [!NOTE]  
> This app runs entirely _in your browser_! As a result, the first time you visit may take 15-20 seconds to load
> so be patient :)

## Building locally

To build the app locally, do the following. First, ensure
[uv](https://docs.astral.sh/uv/getting-started/installation/) is installed and
prep your environment with
```
uv sync
```

Next, download the documents and build the search index with
```
uv run build_index.py
```

Finally, build the static webpage and corresponding assets with
```
uvx shinylive export ./app ./docs  
```

and serve the app locally on port 8000 with
```
uvx python -m http.server --directory docs --bind localhost 8000
```

