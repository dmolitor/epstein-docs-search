from search import clean_content, get_items_text, item_titles, search_index
from shiny import App, render, ui, reactive
from pathlib import Path
import pocketsearch
import math
import gzip
import shutil

base_dir = Path(__file__).parent
data_dir = base_dir / "data"

db_path = data_dir / "index.db"
gz_path = data_dir / "index.db.gz"

# --- Decompress if needed (minimal change) ---
if (not db_path.exists()) and gz_path.exists():
    with gzip.open(gz_path, "rb") as f_in, open(db_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

# Create a reader for the database (unchanged)
Reader = pocketsearch.PocketReader(
    db_name=str(db_path),
    schema=pocketsearch.FileSystemReader.FSSchema
)

RESULTS_PER_PAGE = 10

app_ui = ui.page_fluid(
    ui.panel_title("", "Epstein document search"),
    # Container that takes up 3/4 of the page width and centers everything
    ui.row(
        ui.column(1),
        ui.column(10,
            ui.div(
                # Page title
                ui.h1("Search the Epstein emails", style="text-align: center; font-weight: bold; margin-bottom: 30px;"),
                ui.br(),
                ui.markdown(
                    "This is an easily searchable repository of the 20,000 documents from the Epstein estate released by the US House Oversight Committee on November 12, 2025."
                    + " [Others](https://couriernewsroom.com/news/we-created-a-searchable-database-with-all-20000-files-from-epsteins-estate/)"
                    + " have put together [similar resources](https://splendorous-chaja-f79791.netlify.app/)!"
                    + " <br><br>Feel free to shoot me an email at *dmolitor [at] infosci.cornell.edu*."
                ),
                ui.br(),
                # Search form container
                ui.div(
                    # Full width search input
                    ui.input_text("user_input", "", placeholder="Search documents...", width="100%"),
                    
                    # Centered search button
                    ui.div(
                        ui.input_action_button(
                            "search_btn", 
                            "Search", 
                            class_="btn-success",
                            style="color: white;"
                        ),
                        style="text-align: center; margin-top: 15px;"
                    ),
                    style="margin-bottom: 30px;"
                ),
                
                # Results count display
                ui.output_ui("results_count"),
                
                # Search results
                ui.output_ui("search_results"),
                
                # Pagination controls
                ui.output_ui("pagination"),
                
                style="margin: 0 auto; padding: 20px;"
            )
        ),
        ui.column(1,
            ui.div(
                ui.a(
                    ui.HTML('<svg width="40" height="40" viewBox="0 0 40 40" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>'),
                    href="https://github.com/dmolitor/epstein-docs-search/",
                    target="_blank",
                    style="text-decoration: none; color: #333; opacity: 0.7; hover:opacity: 1; transition: opacity 0.2s;",
                    title="View on GitHub"
                ),
                style="text-align: center; padding-top: 20px;"
            )
        )
    )
)

def server(input, output, session):
    # Store search results, expanded state, and current page
    search_data = reactive.value({"results": [], "titles": [], "expanded": set(), "total_results": 0})
    current_page = reactive.value(1)
    
    # Track last known button values to detect clicks
    last_button_values = reactive.value({})
    has_searched = reactive.value(False)  # Track if we've performed a search

    def get_smart_pagination_pages(current, total_pages):
        """Generate a smart set of page numbers with logarithmic jumps, limited to max 8 buttons"""
        N = 7
        if total_pages <= N:
            # If N or fewer total pages, show them all
            return list(range(1, total_pages + 1))
        
        pages = set()
        
        # Always include first and last
        pages.add(1)
        pages.add(total_pages)
        
        # Include current page and immediate neighbors
        for i in range(max(1, current - 1), min(total_pages + 1, current + 2)):
            pages.add(i)
        
        # Add strategic jump pages to fill remaining slots (target max N total)
        remaining_slots = N - len(pages)
        
        if remaining_slots > 0:
            # Add logarithmic jumps from current position
            distances = [3, 5, 10, 20, 50, 100]
            
            for distance in distances:
                if remaining_slots <= 0:
                    break
                    
                # Add pages at these distances before current
                if current - distance >= 1 and current - distance not in pages:
                    pages.add(current - distance)
                    remaining_slots -= 1
                    
                if remaining_slots <= 0:
                    break
                    
                # Add pages at these distances after current  
                if current + distance <= total_pages and current + distance not in pages:
                    pages.add(current + distance)
                    remaining_slots -= 1
        
        # Convert to sorted list and limit to N pages max
        sorted_pages = sorted(list(pages))
        return sorted_pages[:N]

    # Handle search button click
    @reactive.effect
    @reactive.event(input.search_btn)
    def _():
        query = input.user_input()
        if query:
            has_searched.set(True)  # Mark that we've performed a search
            results = search_index(reader=Reader, text=query)
            if results["n_hits"] >= 1:             
                titles = item_titles(results)
                results_text = get_items_text(results)
                
                search_data.set({
                    "results": results_text, 
                    "titles": titles, 
                    "expanded": set(),
                    "total_results": len(results_text)
                })
            else:
                # No results found - clear previous results and show 0 count
                search_data.set({
                    "results": [], 
                    "titles": [], 
                    "expanded": set(),
                    "total_results": 0
                })
            
            current_page.set(1)  # Reset to first page
            last_button_values.set({})  # Reset button tracking

    # Handle page button clicks
    @reactive.effect
    def _():
        data = search_data.get()
        if not data["results"]:
            return
            
        total_pages = math.ceil(data["total_results"] / RESULTS_PER_PAGE)
        last_values = last_button_values.get()
        current = current_page.get()
        
        # Get all possible page numbers that could have buttons
        possible_pages = get_smart_pagination_pages(current, total_pages)
        
        for page_num in possible_pages:
            button_id = f"page_{page_num}"
            try:
                current_value = getattr(input, button_id, lambda: 0)()
                last_value = last_values.get(button_id, 0)
                
                if current_value > last_value:
                    current_page.set(page_num)
                
                last_values[button_id] = current_value
            except:
                pass
        
        last_button_values.set(last_values)

    # Dynamic button click handler for expand/collapse
    @reactive.effect
    def _():
        data = search_data.get()
        results = data["results"]
        
        if not results:
            return
        
        # Get current page results
        page = current_page.get()
        start_idx = (page - 1) * RESULTS_PER_PAGE
        end_idx = start_idx + RESULTS_PER_PAGE
        page_results = results[start_idx:end_idx]
            
        # Check each possible toggle button for clicks
        expanded = data["expanded"].copy()
        last_values = last_button_values.get()
        updated = False
        
        for i in range(len(page_results)):
            # Use global index for card IDs
            global_idx = start_idx + i
            button_ids = [f"toggle_card_{global_idx+1}", f"toggle_card_{global_idx+1}_header"]
            for button_id in button_ids:
                try:
                    current_value = getattr(input, button_id, lambda: 0)()
                    last_value = last_values.get(button_id, 0)
                    
                    # If button value increased, it was clicked
                    if current_value > last_value:
                        card_id = f"card_{global_idx+1}"
                        if card_id in expanded:
                            expanded.discard(card_id)
                        else:
                            expanded.add(card_id)
                        updated = True
                    
                    last_values[button_id] = current_value
                    
                except:
                    pass  # Button doesn't exist yet
        
        if updated:
            search_data.set({
                "results": results, 
                "titles": data["titles"], 
                "expanded": expanded,
                "total_results": data["total_results"]
            })
        
        last_button_values.set(last_values)

    @render.ui
    def results_count():
        # Only show results count if we've actually performed a search
        if not has_searched.get():
            return ui.div()
        
        data = search_data.get()
        total = data["total_results"]
        return ui.div(
            ui.h4(f"Returned {total} results", style="text-align: center; color: #666; margin-bottom: 20px;"),
        )

    @render.ui
    def search_results():
        data = search_data.get()
        results = data["results"]
        titles = data["titles"]
        expanded = data["expanded"]
        
        if not results:
            return ui.div()
        
        # Get current page results
        page = current_page.get()
        start_idx = (page - 1) * RESULTS_PER_PAGE
        end_idx = start_idx + RESULTS_PER_PAGE
        page_results = results[start_idx:end_idx]
        page_titles = titles[start_idx:end_idx]
            
        # Create a card for each result on current page
        cards = []
        for i, result_obj in enumerate(zip(page_results, page_titles)):
            result_text, title_text = result_obj
            # Use global index for consistent card IDs
            global_idx = start_idx + i
            card_id = f"card_{global_idx+1}"
            is_expanded = card_id in expanded
            
            # Show truncated or full text based on expansion state
            if is_expanded or len(result_text) <= 100:
                display_text = result_text
                button_text = "Show less" if is_expanded else None
            else:
                display_text = result_text[:100] + "..."
                button_text = "Show more"
            
            # Create card header with optional "Show less" button in top right
            if is_expanded:
                header_content = ui.div(
                    ui.div(
                        title_text,
                        style="flex-grow: 1; font-size: 1.35rem; font-weight: bold; color: #0d6efd;"
                    ),
                    ui.div(
                        ui.input_action_button(
                            f"toggle_{card_id}_header",
                            "Show less",
                            class_="btn-outline-secondary btn-sm",
                            style="width: auto; font-size: 0.8rem;"
                        ),
                        style="margin-left: auto;"
                    ),
                    style="display: flex; align-items: center; background-color: #f8f9fa;"
                )
            else:
                header_content = ui.div(
                    title_text,
                    style="font-size: 1.35rem; font-weight: bold; color: #0d6efd; background-color: #f8f9fa;"
                )

            # Create card content
            card_content = [ui.markdown(clean_content(display_text))]

            # Add bottom button if needed - left-aligned with much smaller width
            if button_text:
                card_content.extend([
                    ui.br(),
                    ui.div(
                        ui.input_action_button(
                            f"toggle_{card_id}",
                            button_text,
                            class_="btn-outline-secondary btn-sm",
                            style="width: auto; display: inline-block;"
                        ),
                        style="text-align: left;"
                    )
                ])

            cards.append(
                ui.card(
                    ui.card_header(
                        header_content
                    ),
                    *card_content,
                    # 2px border (1px smaller) with matching button outline color
                    style="border: 2px solid #0d6efd; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"
                )
            )
        
        return ui.div(*cards)

    @render.ui
    def pagination():
        data = search_data.get()
        if not data["results"] or data["total_results"] <= RESULTS_PER_PAGE:
            return ui.div()
        
        total_pages = math.ceil(data["total_results"] / RESULTS_PER_PAGE)
        current = current_page.get()
        
        # Get smart pagination pages
        page_numbers = get_smart_pagination_pages(current, total_pages)
        
        # Create pagination buttons with gaps
        page_elements = []
        last_page = 0
        
        for page_num in page_numbers:
            # Add "..." if there's a gap
            if page_num > last_page + 1:
                page_elements.append(
                    ui.span("...", style="margin: 0 5px; color: #666; font-size: 0.9rem;")
                )
            
            # Highlight current page
            if page_num == current:
                btn_class = "btn-primary"
            else:
                btn_class = "btn-outline-primary"
            
            page_elements.append(
                ui.input_action_button(
                    f"page_{page_num}",
                    str(page_num),
                    class_=f"{btn_class} btn-sm",
                    style="margin: 2px;"
                )
            )
            
            last_page = page_num
        
        return ui.div(
            ui.div(
                *page_elements,
                style="text-align: center; margin-top: 30px;"
            )
        )

app = App(app_ui, server, static_assets=base_dir / "data")