import pocketsearch
from typing import Any, Dict, List

def clean_content(text):
    # Remove BOM character if present
    if text.startswith('\ufeff'):
        text = text[1:]
    
    # Convert newlines to HTML line breaks
    # Simple approach: replace all \n with <br>
    text = text.replace('\n', '<br>')
    text = text.replace('*', '@')
    text = text.replace("`", "@")
    
    return text

def last(x):
    if len(x) < 1:
        return(None)
    return x[len(x)-1]

def item_titles(items: Dict) -> List[str]:
    return [last(item.filename.split("/")) for item in items["items"]]

def search_index(reader: pocketsearch.PocketReader, text: str) -> Dict[str, Any]:
    with reader as DBReader:
        hits = DBReader.search(text=text).count()
        items = DBReader.search(text=text)
        # Highlight items for rendering
        items_highlighted = items.highlight(
            "text",
            marker_start='<mark style="background-color: yellow;">',
            marker_end="</mark>"
        )
        # Subset items
        items_highlighted = items_highlighted[0:(hits)]
        out = {
            "n_hits": hits,
            "items": items_highlighted
        }
        return out

def get_items_text(items: Dict) -> List[str]:
    return [x.text for x in items["items"]]
