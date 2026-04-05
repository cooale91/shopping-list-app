import json
import re
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import streamlit as st

DATA_FILE = Path("recipes.json")
PREFS_FILE = Path("product_preferences.json")

st.set_page_config(
    page_title="Meal Planner",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

MOBILE_CSS = """
<style>
html, body, [class*="css"]  {
    color: #111111;
}
.block-container {
    max-width: 560px;
    padding-top: 0.7rem;
    padding-bottom: 6.5rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
}
header[data-testid="stHeader"] {
    background: rgba(255,255,255,0.0);
}
section[data-testid="stSidebar"] {
    display: none;
}
.app-shell {
    border: 1px solid rgba(80,80,80,0.20);
    border-radius: 24px;
    padding: 0.9rem;
    background: #ffffff;
    box-shadow: 0 8px 28px rgba(0,0,0,0.06);
}
.hero {
    padding: 1rem;
    border-radius: 20px;
    margin-bottom: 0.9rem;
    background: linear-gradient(135deg, rgba(0,120,255,0.12), rgba(0,180,120,0.08));
    border: 1px solid rgba(0,120,255,0.15);
}
.hero h1 {
    font-size: 1.55rem;
    margin: 0 0 0.2rem 0;
    color: #111111;
}
.hero p {
    margin: 0;
    color: #2c2c2c;
    font-size: 1rem;
    line-height: 1.35;
}
.section-card {
    padding: 0.95rem;
    border-radius: 18px;
    margin-bottom: 0.85rem;
    border: 1px solid rgba(80,80,80,0.18);
    background: #ffffff;
}
.recipe-card {
    padding: 0.95rem;
    border-radius: 16px;
    margin-bottom: 0.8rem;
    border: 1px solid rgba(80,80,80,0.18);
    background: #fcfcfc;
}
.metric-pill {
    padding: 0.6rem 0.85rem;
    border-radius: 999px;
    display: inline-block;
    margin-right: 0.45rem;
    margin-bottom: 0.45rem;
    border: 1px solid rgba(80,80,80,0.18);
    background: #f7f7f7;
    font-size: 0.98rem;
    color: #111111;
}
.item-row {
    padding: 0.85rem 0.1rem;
    border-bottom: 1px solid rgba(120,120,120,0.14);
}
.bottom-hint {
    position: sticky;
    bottom: 0.55rem;
    margin-top: 1rem;
    padding: 0.95rem;
    border-radius: 16px;
    background: #f8f8f8;
    border: 1px solid rgba(80,80,80,0.15);
    color: #111111;
}
.small-muted {
    color: #333333;
    font-size: 0.95rem;
}
.stButton > button,
.stDownloadButton > button,
.stLinkButton > a {
    width: 100%;
    min-height: 3.5rem;
    font-size: 1.05rem;
    font-weight: 600;
    border-radius: 16px;
}
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
textarea,
input {
    font-size: 1.02rem !important;
    color: #111111 !important;
}
label, .stMarkdown, p, li, span, div {
    color: #111111;
}
div[data-testid="stCheckbox"] label p {
    font-size: 1.02rem !important;
    color: #111111 !important;
}
div[data-testid="stTabs"] button {
    font-size: 1rem;
    padding-top: 0.8rem;
    padding-bottom: 0.8rem;
    color: #111111;
}
h1, h2, h3, h4 {
    color: #111111;
}
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

SUPERMARKETS = {
    "Sainsbury's": "https://www.sainsburys.co.uk/gol-ui/SearchResults/",
    "Tesco": "https://www.tesco.com/groceries/en-GB/search?query=",
    "Asda": "https://groceries.asda.com/search/",
}

DEFAULT_PREFERENCES = {
    "Onion": "brown onions",
    "Garlic cloves": "garlic bulb",
    "Chicken breast": "chicken breast fillets",
    "Beef mince": "lean beef mince 500g",
    "Chopped tomatoes": "chopped tomatoes 400g",
    "Spaghetti": "spaghetti 500g",
    "Coconut milk": "coconut milk 400ml",
    "Rice": "basmati rice 1kg",
    "Sour cream": "sour cream 300ml",
}

DEFAULT_CATEGORIES = [
    "Vegetables", "Fruit", "Meat", "Fish", "Dairy", "Bakery",
    "Pasta & Rice", "Cupboard", "Tins & Jars", "Frozen", "Other"
]

def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_recipes():
    return load_json(DATA_FILE, [])

def save_recipes(recipes):
    save_json(DATA_FILE, recipes)

def load_preferences():
    prefs = load_json(PREFS_FILE, DEFAULT_PREFERENCES.copy())
    return prefs if isinstance(prefs, dict) else DEFAULT_PREFERENCES.copy()

def ingredient_key(item):
    return (item["name"].strip().lower(), item.get("unit", "").strip().lower())

def qty_text(qty, unit):
    q = f"{float(qty):.2f}".rstrip("0").rstrip(".")
    return f"{q}{(' ' + unit) if unit else ''}"

def preferred_term(name, preferences):
    return preferences.get(name, "").strip() or name

def shop_url(store, query):
    return SUPERMARKETS[store] + quote(query)

def combine_items(selected_recipes, pantry_items):
    combined = defaultdict(lambda: {"quantity": 0.0, "unit": "", "category": "Other", "name": ""})
    for recipe in selected_recipes:
        scale = recipe["selected_servings"] / recipe["default_servings"]
        for ing in recipe["ingredients"]:
            key = ingredient_key(ing)
            combined[key]["quantity"] += float(ing["quantity"]) * scale
            combined[key]["unit"] = ing.get("unit", "")
            combined[key]["category"] = ing.get("category", "Other")
            combined[key]["name"] = ing["name"]

    pantry_set = {p.strip().lower() for p in pantry_items if p.strip()}
    items = [v for v in combined.values() if v["name"].strip().lower() not in pantry_set]
    items.sort(key=lambda x: (x["category"], x["name"].lower()))
    return items

def group_items(items):
    grouped = defaultdict(list)
    for item in items:
        grouped[item["category"]].append(item)
    return dict(grouped)

def bulk_text(items, prefs, with_qty=False):
    lines = []
    for item in items:
        query = preferred_term(item["name"], prefs)
        lines.append(f"{query} - {qty_text(item['quantity'], item['unit'])}" if with_qty else query)
    return "\n".join(lines)

def recipe_exists(recipes, name):
    target = name.strip().lower()
    return any(r["name"].strip().lower() == target for r in recipes)

def infer_category(name: str) -> str:
    text = name.lower()
    vegetable_terms = ["onion", "garlic", "carrot", "pepper", "potato", "broccoli", "celery", "tomato", "spinach", "lettuce", "courgette", "zucchini", "mushroom"]
    meat_terms = ["chicken", "beef", "mince", "pork", "sausage", "bacon", "turkey", "lamb"]
    dairy_terms = ["milk", "cheese", "cream", "butter", "yoghurt", "yogurt", "sour cream", "mozzarella"]
    bakery_terms = ["bread", "wrap", "bun", "roll", "tortilla", "naan", "pitta", "pita"]
    pasta_terms = ["rice", "pasta", "spaghetti", "noodle", "couscous"]
    tins_terms = ["coconut milk", "beans", "tomatoes", "tinned", "tin", "chickpeas"]
    if any(t in text for t in vegetable_terms):
        return "Vegetables"
    if any(t in text for t in meat_terms):
        return "Meat"
    if any(t in text for t in dairy_terms):
        return "Dairy"
    if any(t in text for t in bakery_terms):
        return "Bakery"
    if any(t in text for t in pasta_terms):
        return "Pasta & Rice"
    if any(t in text for t in tins_terms):
        return "Tins & Jars"
    return "Other"

def fetch_hellofresh_recipe(url: str) -> dict:
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-GB,en;q=0.9"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = None
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(" ", strip=True)

    ingredients = []
    servings = 2
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "Recipe":
                if not title:
                    title = item.get("name")
                y = item.get("recipeYield")
                if isinstance(y, str):
                    m = re.search(r"(\d+)", y)
                    if m:
                        servings = int(m.group(1))
                elif isinstance(y, (int, float)):
                    servings = int(y)
                for ing in item.get("recipeIngredient", []) or []:
                    ingredients.append(parse_ingredient_line(ing))

    if not ingredients:
        text_lines = []
        for li in soup.find_all(["li", "span", "p", "div"]):
            txt = li.get_text(" ", strip=True)
            if txt:
                text_lines.append(txt)
        seen = set()
        for line in text_lines:
            if looks_like_ingredient(line):
                parsed = parse_ingredient_line(line)
                key = (parsed["name"].lower(), parsed["unit"])
                if key not in seen:
                    seen.add(key)
                    ingredients.append(parsed)

    if not title:
        raise ValueError("Could not find recipe title on that page.")
    if not ingredients:
        raise ValueError("Could not extract ingredients from that HelloFresh page.")

    cleaned = []
    seen_names = set()
    for ing in ingredients:
        name = ing["name"].strip()
        if not name:
            continue
        key = (name.lower(), ing.get("unit", ""))
        if key in seen_names:
            continue
        seen_names.add(key)
        cleaned.append({
            "name": name,
            "quantity": ing.get("quantity", 1.0) or 1.0,
            "unit": ing.get("unit", ""),
            "category": infer_category(name),
        })

    return {"name": title.strip(), "default_servings": int(servings) if servings else 2, "ingredients": cleaned}

def looks_like_ingredient(line: str) -> bool:
    lower = line.lower()
    skip_terms = ["method", "instructions", "nutrition", "calories", "allergens", "difficulty", "prep time", "cook time", "recipe", "share", "save"]
    if any(term in lower for term in skip_terms):
        return False
    return bool(re.search(r"\b(g|kg|ml|l|tbsp|tsp|clove|cloves|pack|packs|pot|pots|tin|tins)\b", lower) or re.match(r"^\d", line))

def parse_ingredient_line(line: str) -> dict:
    text = " ".join(str(line).replace("\xa0", " ").split()).strip("•- ")
    text = re.sub(r"\([^)]*\)", "", text).strip()
    quantity = 1.0
    unit = ""
    name = text

    m = re.match(r"^(\d+(?:\.\d+)?(?:/\d+)?)\s*([A-Za-z]+)?\s+(.*)$", text)
    if m:
        raw_qty, raw_unit, raw_name = m.groups()
        try:
            if "/" in raw_qty and raw_qty.count("/") == 1:
                a, b = raw_qty.split("/")
                quantity = float(a) / float(b)
            else:
                quantity = float(raw_qty)
        except Exception:
            quantity = 1.0
        unit = normalize_unit(raw_unit or "")
        name = raw_name.strip()
    else:
        for u in ["g", "kg", "ml", "l", "tbsp", "tsp", "clove", "cloves", "pack", "packs", "pot", "pots", "tin", "tins"]:
            if re.search(rf"\b{u}\b", text.lower()):
                unit = normalize_unit(u)
                name = re.sub(rf"^\s*\d+(?:\.\d+)?\s*{u}\s+", "", text, flags=re.I).strip() or text
                break

    return {"name": name.title() if name.islower() else name, "quantity": quantity, "unit": unit}

def normalize_unit(unit: str) -> str:
    unit = unit.lower()
    mapping = {"cloves": "cloves", "clove": "clove", "packs": "pack", "pots": "pot", "tins": "tin"}
    return mapping.get(unit, unit)

recipes = load_recipes()
preferences = load_preferences()

if "selected_recipe_names" not in st.session_state:
    st.session_state.selected_recipe_names = []
if "servings" not in st.session_state:
    st.session_state.servings = {}
if "pantry_text" not in st.session_state:
    st.session_state.pantry_text = ""
if "store_name" not in st.session_state:
    st.session_state.store_name = "Sainsbury's"
if "import_preview" not in st.session_state:
    st.session_state.import_preview = None
if "hf_url" not in st.session_state:
    st.session_state.hf_url = ""

st.markdown('<div class="app-shell">', unsafe_allow_html=True)
st.markdown("""
<div class="hero">
  <h1>Meal Planner</h1>
  <p>Choose recipes, add your own, import a HelloFresh recipe link, and turn everything into a shopping list.</p>
</div>
""", unsafe_allow_html=True)

tab_plan, tab_shop, tab_add, tab_import = st.tabs(["Plan", "Shop", "Add recipe", "Import URL"])

with tab_plan:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    search = st.text_input("Search recipes", placeholder="Pasta, curry, soup...")
    filtered = [r for r in recipes if search.lower() in r["name"].lower()] if search else recipes

    top = st.columns([1, 1])
    with top[0]:
        if st.button("Select all shown"):
            st.session_state.selected_recipe_names = [r["name"] for r in filtered]
    with top[1]:
        if st.button("Clear all"):
            st.session_state.selected_recipe_names = []

    st.markdown(
        f'<span class="metric-pill">{len(filtered)} recipes shown</span>'
        f'<span class="metric-pill">{len(st.session_state.selected_recipe_names)} selected</span>',
        unsafe_allow_html=True,
    )

    for recipe in filtered:
        selected = recipe["name"] in st.session_state.selected_recipe_names
        st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([2.2, 1])
        with c1:
            new_selected = st.checkbox(recipe["name"], value=selected, key=f"sel_{recipe['name']}")
            st.markdown(
                f'<div class="small-muted">{recipe["default_servings"]} servings · {len(recipe["ingredients"])} ingredients</div>',
                unsafe_allow_html=True
            )
        with c2:
            servings = st.number_input(
                "Servings",
                min_value=1,
                max_value=20,
                value=int(st.session_state.servings.get(recipe["name"], recipe["default_servings"])),
                step=1,
                key=f"serv_{recipe['name']}"
            )
            st.session_state.servings[recipe["name"]] = int(servings)

        if new_selected and recipe["name"] not in st.session_state.selected_recipe_names:
            st.session_state.selected_recipe_names.append(recipe["name"])
        elif not new_selected and recipe["name"] in st.session_state.selected_recipe_names:
            st.session_state.selected_recipe_names.remove(recipe["name"])

        with st.expander("View ingredients"):
            for ing in recipe["ingredients"]:
                st.write(f"- {ing['name']}: {qty_text(ing['quantity'], ing.get('unit', ''))} ({ing.get('category', 'Other')})")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_shop:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.session_state.store_name = st.selectbox("Supermarket", list(SUPERMARKETS.keys()))
    with c2:
        st.caption("Buttons sized for a small tablet screen")

    st.session_state.pantry_text = st.text_area(
        "Pantry items to exclude",
        value=st.session_state.pantry_text,
        height=100,
        placeholder="salt\nolive oil\nblack pepper"
    )
    pantry_items = st.session_state.pantry_text.splitlines()

    selected = []
    for recipe in recipes:
        if recipe["name"] in st.session_state.selected_recipe_names:
            r = dict(recipe)
            r["selected_servings"] = st.session_state.servings.get(recipe["name"], recipe["default_servings"])
            selected.append(r)

    if not selected:
        st.info("Choose at least one recipe in Plan.")
    else:
        items = combine_items(selected, pantry_items)
        grouped = group_items(items)

        st.markdown(
            f'<span class="metric-pill">{len(selected)} recipes</span>'
            f'<span class="metric-pill">{len(items)} items</span>'
            f'<span class="metric-pill">{len(grouped)} categories</span>',
            unsafe_allow_html=True,
        )

        plain_bulk = bulk_text(items, preferences, with_qty=False)
        qty_bulk = bulk_text(items, preferences, with_qty=True)

        st.text_area("Bulk list to copy", value=plain_bulk, height=150, key="plain_bulk")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("Download list", plain_bulk, "bulk_shopping_list.txt", mime="text/plain")
        with d2:
            st.download_button("Download with qty", qty_bulk, "bulk_shopping_list_with_qty.txt", mime="text/plain")

        st.markdown("### Quick shop")
        for category, entries in grouped.items():
            st.markdown(f"**{category}**")
            for item in entries:
                query = preferred_term(item["name"], preferences)
                link = shop_url(st.session_state.store_name, query)
                a, b = st.columns([2.05, 1])
                with a:
                    st.markdown(
                        f'<div class="item-row"><strong>{item["name"]}</strong><br><span class="small-muted">{qty_text(item["quantity"], item["unit"])} · search: {query}</span></div>',
                        unsafe_allow_html=True,
                    )
                with b:
                    st.link_button("Shop", link, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab_add:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Build a recipe")
    st.caption("Add up to 8 ingredients in one go.")

    with st.form("add_recipe_form", clear_on_submit=False):
        recipe_name = st.text_input("Recipe name", placeholder="Chicken pasta bake")
        default_servings = st.number_input("Default servings", min_value=1, max_value=20, value=4, step=1)

        st.markdown("#### Ingredients")
        rows = []
        for i in range(1, 9):
            c1, c2, c3, c4 = st.columns([2.1, 1, 1, 1.15])
            with c1:
                ing_name = st.text_input(f"Ingredient {i}", key=f"ing_name_{i}", placeholder="Chicken breast")
            with c2:
                ing_qty = st.number_input(f"Qty {i}", min_value=0.0, value=0.0, step=0.5, key=f"ing_qty_{i}")
            with c3:
                ing_unit = st.text_input(f"Unit {i}", key=f"ing_unit_{i}", placeholder="g / ml / tin")
            with c4:
                ing_cat = st.selectbox(f"Category {i}", options=DEFAULT_CATEGORIES, key=f"ing_cat_{i}")
            rows.append((ing_name, ing_qty, ing_unit, ing_cat))

        submitted = st.form_submit_button("Save recipe")

    if submitted:
        clean_name = recipe_name.strip()
        if not clean_name:
            st.error("Recipe name is required.")
        elif recipe_exists(recipes, clean_name):
            st.error("That recipe already exists.")
        else:
            ingredients = []
            for ing_name, ing_qty, ing_unit, ing_cat in rows:
                if ing_name.strip():
                    if float(ing_qty) <= 0:
                        st.error(f"{ing_name} needs a quantity greater than 0.")
                        st.stop()
                    ingredients.append({
                        "name": ing_name.strip(),
                        "quantity": float(ing_qty),
                        "unit": ing_unit.strip(),
                        "category": ing_cat,
                    })
            if not ingredients:
                st.error("Add at least one ingredient.")
            else:
                new_recipe = {"name": clean_name, "default_servings": int(default_servings), "ingredients": ingredients}
                recipes.append(new_recipe)
                recipes.sort(key=lambda r: r["name"].lower())
                save_recipes(recipes)
                for ing in ingredients:
                    preferences.setdefault(ing["name"], ing["name"])
                save_json(PREFS_FILE, preferences)
                st.success(f"Saved recipe: {clean_name}")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with tab_import:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Import HelloFresh recipe URL")
    st.caption("Paste a public HelloFresh recipe page and preview it before saving.")

    st.session_state.hf_url = st.text_input(
        "HelloFresh recipe URL",
        value=st.session_state.hf_url,
        placeholder="https://www.hellofresh.co.uk/recipes/..."
    )

    if st.button("Fetch recipe from URL"):
        if not st.session_state.hf_url.strip():
            st.error("Paste a HelloFresh recipe URL first.")
        else:
            try:
                st.session_state.import_preview = fetch_hellofresh_recipe(st.session_state.hf_url.strip())
                st.success("Recipe fetched. Check the preview below.")
            except Exception as e:
                st.session_state.import_preview = None
                st.error(f"Could not import that URL: {e}")

    preview = st.session_state.import_preview
    if preview:
        st.markdown("### Preview")
        st.markdown(f"**{preview['name']}**")
        st.write(f"Servings: {preview['default_servings']}")
        for ing in preview["ingredients"]:
            st.write(f"- {ing['name']}: {qty_text(ing['quantity'], ing.get('unit', ''))} ({ing.get('category', 'Other')})")

        save_cols = st.columns(2)
        with save_cols[0]:
            if st.button("Save imported recipe"):
                if recipe_exists(recipes, preview["name"]):
                    st.error("That recipe already exists in your list.")
                else:
                    recipes.append(preview)
                    recipes.sort(key=lambda r: r["name"].lower())
                    save_recipes(recipes)
                    for ing in preview["ingredients"]:
                        preferences.setdefault(ing["name"], ing["name"])
                    save_json(PREFS_FILE, preferences)
                    st.success(f"Saved recipe: {preview['name']}")
                    st.session_state.import_preview = None
                    st.session_state.hf_url = ""
                    st.rerun()
        with save_cols[1]:
            if st.button("Discard preview"):
                st.session_state.import_preview = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="bottom-hint">
  <strong>Fire 7 layout:</strong> buttons are larger, text is darker, and the page is centered to keep taps easier on a small screen.
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
