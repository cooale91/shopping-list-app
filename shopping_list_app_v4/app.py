import json
from pathlib import Path
from collections import defaultdict
import urllib.parse
import streamlit as st

DATA_FILE = Path("recipes.json")
PLANS_FILE = Path("saved_plans.json")
PREFS_FILE = Path("product_preferences.json")

st.set_page_config(
    page_title="Recipe Shopping List",
    page_icon="🛒",
    layout="wide",
)

TABLET_CSS = """
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1250px;
    }
    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1rem;
        border-radius: 0.8rem;
    }
    div[data-testid="stNumberInput"] input {
        font-size: 1rem;
    }
    .recipe-card {
        padding: 1rem;
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 1rem;
        margin-bottom: 0.8rem;
        background: rgba(250,250,250,0.02);
    }
    .small-muted {
        color: #777;
        font-size: 0.92rem;
    }
</style>
"""
st.markdown(TABLET_CSS, unsafe_allow_html=True)

SUPERMARKETS = {
    "Sainsbury's": {
        "search": "https://www.sainsburys.co.uk/gol-ui/SearchResults/",
        "bulk_hint": "Paste the list into Sainsbury's 'Search your Shopping List' page."
    },
    "Tesco": {
        "search": "https://www.tesco.com/groceries/en-GB/search?query=",
        "bulk_hint": "Use the exported text as a shopping reference or paste queries one by one."
    },
    "Asda": {
        "search": "https://groceries.asda.com/search/",
        "bulk_hint": "Use the exported text as a shopping reference or paste queries one by one."
    },
}

DEFAULT_PREFERENCES = {
    "Milk": "semi skimmed milk 2L",
    "Rice": "basmati rice 1kg",
    "Chopped tomatoes": "chopped tomatoes 400g",
    "Onion": "brown onions",
    "Garlic cloves": "garlic bulb",
    "Chicken breast": "chicken breast fillets",
    "Beef mince": "lean beef mince 500g",
    "Coconut milk": "coconut milk 400ml",
    "Spaghetti": "spaghetti 500g",
    "Sour cream": "sour cream 300ml"
}

def load_json_file(path, default_value):
    if not path.exists():
        return default_value
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_recipes():
    return load_json_file(DATA_FILE, [])

def load_plans():
    return load_json_file(PLANS_FILE, {})

def load_preferences():
    prefs = load_json_file(PREFS_FILE, DEFAULT_PREFERENCES.copy())
    if not isinstance(prefs, dict):
        return DEFAULT_PREFERENCES.copy()
    return prefs

def ingredient_key(item):
    return (item["name"].strip().lower(), item.get("unit", "").strip().lower())

def build_shopping_list(selected_recipes, pantry_items):
    combined = defaultdict(lambda: {"quantity": 0, "unit": "", "category": "Other", "name": ""})

    for recipe in selected_recipes:
        scale = recipe["selected_servings"] / recipe["default_servings"]
        for ing in recipe["ingredients"]:
            key = ingredient_key(ing)
            combined[key]["quantity"] += ing["quantity"] * scale
            combined[key]["unit"] = ing.get("unit", "")
            combined[key]["category"] = ing.get("category", "Other")
            combined[key]["name"] = ing["name"]

    pantry_set = {p.strip().lower() for p in pantry_items if p.strip()}
    filtered = []
    for item in combined.values():
        if item["name"].strip().lower() not in pantry_set:
            filtered.append(item)

    filtered.sort(key=lambda x: (x["category"], x["name"].lower()))
    return filtered

def group_by_category(items):
    groups = defaultdict(list)
    for item in items:
        groups[item["category"]].append(item)
    return dict(groups)

def shopping_list_text(items):
    grouped = group_by_category(items)
    lines = []
    for category, entries in grouped.items():
        lines.append(f"{category}")
        lines.append("-" * len(category))
        for item in entries:
            qty = f"{item['quantity']:.2f}".rstrip("0").rstrip(".")
            unit = f" {item['unit']}" if item["unit"] else ""
            lines.append(f"- {item['name']}: {qty}{unit}")
        lines.append("")
    return "\n".join(lines).strip()

def qty_string(item):
    qty = f"{item['quantity']:.2f}".rstrip("0").rstrip(".")
    unit = f" {item['unit']}" if item["unit"] else ""
    return f"{qty}{unit}"

def preferred_search_term(item_name, preferences):
    mapped = preferences.get(item_name, "").strip()
    return mapped if mapped else item_name

def shop_search_url(store_name, query_text):
    base = SUPERMARKETS[store_name]["search"]
    query = urllib.parse.quote(query_text)
    return f"{base}{query}"

def build_shop_all_links(items, store_name, preferences):
    lines = [f"Open these in {store_name}:"]
    for item in items:
        query = preferred_search_term(item["name"], preferences)
        url = shop_search_url(store_name, query)
        lines.append(f"- {item['name']} ({qty_string(item)}) => {query}: {url}")
    return "\n".join(lines)

def build_bulk_shopping_text(items, preferences, include_quantities=False):
    lines = []
    for item in items:
        query = preferred_search_term(item["name"], preferences)
        if include_quantities:
            lines.append(f"{query} - {qty_string(item)}")
        else:
            lines.append(query)
    return "\n".join(lines)

recipes = load_recipes()
saved_plans = load_plans()
preferences = load_preferences()

if "selected_recipe_names" not in st.session_state:
    st.session_state.selected_recipe_names = []
if "servings" not in st.session_state:
    st.session_state.servings = {}
if "pantry_text" not in st.session_state:
    st.session_state.pantry_text = ""
if "plan_name" not in st.session_state:
    st.session_state.plan_name = ""
if "store_name" not in st.session_state:
    st.session_state.store_name = "Sainsbury's"
if "top_link_count" not in st.session_state:
    st.session_state.top_link_count = 8

st.title("Recipe Shopping List")
st.caption("Choose recipes, exclude pantry items, save weekly plans, and streamline online shopping.")

tab1, tab2, tab3, tab4 = st.tabs(["Choose recipes", "Shopping list", "Saved plans", "Product preferences"])

with tab1:
    st.subheader("Pick your meals")
    st.markdown('<div class="small-muted">Tablet-friendly selector with larger controls.</div>', unsafe_allow_html=True)

    search = st.text_input("Search recipes", placeholder="Try: pasta, curry, soup")
    filtered_recipes = [
        r for r in recipes
        if search.lower() in r["name"].lower()
    ] if search else recipes

    cols_top = st.columns([1, 1, 2])
    with cols_top[0]:
        if st.button("Select all shown"):
            st.session_state.selected_recipe_names = [r["name"] for r in filtered_recipes]
    with cols_top[1]:
        if st.button("Clear selection"):
            st.session_state.selected_recipe_names = []
    with cols_top[2]:
        st.write(f"Recipes available: **{len(filtered_recipes)}**")

    for recipe in filtered_recipes:
        selected = recipe["name"] in st.session_state.selected_recipe_names
        st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
        left, right = st.columns([2.2, 1])
        with left:
            new_selected = st.checkbox(
                recipe["name"],
                value=selected,
                key=f"select_{recipe['name']}"
            )
            st.markdown(
                f'<div class="small-muted">Default servings: {recipe["default_servings"]} · '
                f'{len(recipe["ingredients"])} ingredients</div>',
                unsafe_allow_html=True
            )
        with right:
            servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=20,
                value=st.session_state.servings.get(recipe["name"], recipe["default_servings"]),
                step=1,
                key=f"servings_{recipe['name']}"
            )
            st.session_state.servings[recipe["name"]] = servings

        if new_selected and recipe["name"] not in st.session_state.selected_recipe_names:
            st.session_state.selected_recipe_names.append(recipe["name"])
        elif not new_selected and recipe["name"] in st.session_state.selected_recipe_names:
            st.session_state.selected_recipe_names.remove(recipe["name"])

        with st.expander(f"View ingredients for {recipe['name']}"):
            for ing in recipe["ingredients"]:
                unit = f" {ing['unit']}" if ing.get("unit") else ""
                st.write(f"- {ing['name']}: {ing['quantity']}{unit} ({ing.get('category', 'Other')})")
        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.subheader("Your combined shopping list")

    top_controls = st.columns([1.1, 1.1, 1.8])
    with top_controls[0]:
        st.session_state.store_name = st.selectbox(
            "Supermarket",
            options=list(SUPERMARKETS.keys()),
            index=list(SUPERMARKETS.keys()).index(st.session_state.store_name)
        )
    with top_controls[1]:
        st.session_state.top_link_count = st.number_input(
            "Top quick links",
            min_value=1,
            max_value=30,
            value=st.session_state.top_link_count,
            step=1
        )
    with top_controls[2]:
        st.caption(SUPERMARKETS[st.session_state.store_name]["bulk_hint"])

    st.text_area(
        "Pantry items to exclude (one per line)",
        key="pantry_text",
        height=120,
        placeholder="Example:\nolive oil\nsalt\nblack pepper"
    )
    pantry_items = st.session_state.pantry_text.splitlines()

    selected_recipes = []
    for recipe in recipes:
        if recipe["name"] in st.session_state.selected_recipe_names:
            recipe_copy = dict(recipe)
            recipe_copy["selected_servings"] = st.session_state.servings.get(
                recipe["name"], recipe["default_servings"]
            )
            selected_recipes.append(recipe_copy)

    if not selected_recipes:
        st.info("Select at least one recipe in the first tab.")
    else:
        items = build_shopping_list(selected_recipes, pantry_items)
        grouped = group_by_category(items)

        summary_cols = st.columns(4)
        summary_cols[0].metric("Recipes selected", len(selected_recipes))
        summary_cols[1].metric("Items to buy", len(items))
        summary_cols[2].metric("Categories", len(grouped))
        summary_cols[3].metric("Preferred mappings", sum(1 for k, v in preferences.items() if v.strip()))

        st.markdown("### Bulk shopping text")
        st.write("Use this to paste into a supermarket shopping-list search or keep as a clean buying list.")
        bulk_plain = build_bulk_shopping_text(items, preferences, include_quantities=False)
        bulk_with_qty = build_bulk_shopping_text(items, preferences, include_quantities=True)

        bulk_cols = st.columns(2)
        with bulk_cols[0]:
            st.text_area("Bulk list (preferred search terms)", value=bulk_plain, height=220)
            st.download_button(
                "Download bulk list (.txt)",
                data=bulk_plain,
                file_name="bulk_shopping_list.txt",
                mime="text/plain"
            )
        with bulk_cols[1]:
            st.text_area("Bulk list with quantities", value=bulk_with_qty, height=220)
            st.download_button(
                "Download bulk list with quantities (.txt)",
                data=bulk_with_qty,
                file_name="bulk_shopping_list_with_quantities.txt",
                mime="text/plain"
            )

        st.markdown("### Open top search links")
        st.write("Use these for the first items you want to buy fastest.")
        quick_items = items[:st.session_state.top_link_count]
        quick_cols = st.columns(2)
        for idx, item in enumerate(quick_items):
            with quick_cols[idx % 2]:
                query = preferred_search_term(item["name"], preferences)
                link = shop_search_url(st.session_state.store_name, query)
                st.link_button(
                    f"{item['name']} → {query}",
                    link,
                    use_container_width=True
                )

        st.markdown("### All shopping links")
        all_links_text = build_shop_all_links(items, st.session_state.store_name, preferences)
        safe_store_name = st.session_state.store_name.lower().replace("'", "").replace(" ", "_")
        st.download_button(
            f"Download all {st.session_state.store_name} links (.txt)",
            data=all_links_text,
            file_name=f"{safe_store_name}_shopping_links.txt",
            mime="text/plain"
        )

        with st.expander("Show all search links"):
            for item in items:
                query = preferred_search_term(item["name"], preferences)
                link = shop_search_url(st.session_state.store_name, query)
                st.markdown(f"- [{item['name']} — {qty_string(item)} → {query}]({link})")

        st.markdown("### Item-by-item list")
        for category, entries in grouped.items():
            st.markdown(f"#### {category}")
            for item in entries:
                query = preferred_search_term(item["name"], preferences)
                link = shop_search_url(st.session_state.store_name, query)

                box_cols = st.columns([2.2, 1.5, 1.2])
                with box_cols[0]:
                    st.checkbox(
                        f"{item['name']} — {qty_string(item)}",
                        key=f"buy_{category}_{item['name']}_{item['unit']}",
                        value=False
                    )
                with box_cols[1]:
                    st.caption(f"Search term: {query}")
                with box_cols[2]:
                    st.link_button("Shop", link, use_container_width=True)

        txt = shopping_list_text(items)
        st.download_button(
            "Download shopping list (.txt)",
            data=txt,
            file_name="shopping_list.txt",
            mime="text/plain"
        )

with tab3:
    st.subheader("Weekly meal plans")

    st.session_state.plan_name = st.text_input(
        "Plan name",
        value=st.session_state.plan_name,
        placeholder="Example: Week 1 / Family meals / Batch cook week"
    )

    save_cols = st.columns([1, 1.3])
    with save_cols[0]:
        if st.button("Save current plan"):
            if not st.session_state.plan_name.strip():
                st.warning("Enter a plan name first.")
            else:
                saved_plans[st.session_state.plan_name.strip()] = {
                    "selected_recipe_names": st.session_state.selected_recipe_names,
                    "servings": st.session_state.servings,
                    "pantry_text": st.session_state.pantry_text,
                    "store_name": st.session_state.store_name,
                }
                save_json_file(PLANS_FILE, saved_plans)
                st.success(f"Saved plan: {st.session_state.plan_name.strip()}")

    if saved_plans:
        plan_to_load = st.selectbox("Saved plans", options=list(saved_plans.keys()))
        action_cols = st.columns([1, 1])
        with action_cols[0]:
            if st.button("Load selected plan"):
                data = saved_plans[plan_to_load]
                st.session_state.selected_recipe_names = data.get("selected_recipe_names", [])
                st.session_state.servings = data.get("servings", {})
                st.session_state.pantry_text = data.get("pantry_text", "")
                st.session_state.store_name = data.get("store_name", "Sainsbury's")
                st.success(f"Loaded plan: {plan_to_load}")
        with action_cols[1]:
            if st.button("Delete selected plan"):
                saved_plans.pop(plan_to_load, None)
                save_json_file(PLANS_FILE, saved_plans)
                st.success(f"Deleted plan: {plan_to_load}")
                st.rerun()

with tab4:
    st.subheader("Preferred product mapping")
    st.write("Make your ingredient searches more specific so shopping takes fewer taps.")

    all_ingredient_names = sorted({
        ing["name"]
        for recipe in recipes
        for ing in recipe["ingredients"]
    })

    for ingredient_name in all_ingredient_names:
        preferences[ingredient_name] = st.text_input(
            ingredient_name,
            value=preferences.get(ingredient_name, ""),
            key=f"pref_{ingredient_name}"
        )

    pref_cols = st.columns([1, 1, 2])
    with pref_cols[0]:
        if st.button("Save preferences"):
            save_json_file(PREFS_FILE, preferences)
            st.success("Saved preferred product mappings.")
    with pref_cols[1]:
        if st.button("Reset defaults"):
            preferences = DEFAULT_PREFERENCES.copy()
            save_json_file(PREFS_FILE, preferences)
            st.success("Reset to default mappings.")
            st.rerun()
    with pref_cols[2]:
        st.caption("Example: set Milk to 'semi skimmed milk 2L' instead of a generic milk search.")
