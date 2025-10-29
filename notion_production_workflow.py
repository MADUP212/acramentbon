import os
import requests

NOTION_TOKEN = os.getenv("NOTION_SECRET_TOKEN")

# IDs des bases (remplace ceux du lien par le vrai ID Notion si besoin)
DATABASE_IDS = {
    "productions": "29af968fdebf8015930ae2cda8467397",  # Productions
    "recipes_ppp": "296f968fdebf80b0b31dd2a287eaf027",   # Recettes_PPP_4500
    "recipes_ccp": "296f968fdebf80a69a5bd2313f528a25",   # Recettes_CCP_4500
    "inventory": "296f968fdebf81b5a870ec66696278ed",     # Inventaire
}

# Nom des propriétés à retrouver dans les bases
FIELDS = {
    "productions": {
        "product": "Produit",
        "quantity": "Quantité désirée",
        "factor": "Facteur",
        "status": "État",
        "recipe_field": "Recette calculée"
    },
    "recipes": {
        "ingredient": "Nom Ingrédient",
        "quantity": "Quantité pour 4500",
        "unit": "Unité"
    },
    "inventory": {
        "ingredient": "Nom Ingrédient",
        "stock": "Stock actuel"
    }
}

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def fetch_new_productions():
    url = f"https://api.notion.com/v1/databases/{DATABASE_IDS['productions']}/query"
    # Filtrer «État» == «Imprimer recette», adaptez si champ status différent
    resp = requests.post(url, json={
        "filter": {
            "property": FIELDS['productions']['status'],
            "select": {
                "equals": "Imprimer recette"
            }
        }
    }, headers=HEADERS)
    data = resp.json()
    return data.get("results", [])

def get_recipe(product):
    db_key = "recipes_ppp" if product == "PPP" else "recipes_ccp"
    url = f"https://api.notion.com/v1/databases/{DATABASE_IDS[db_key]}/query"
    resp = requests.post(url, json={}, headers=HEADERS)
    return resp.json().get("results", [])

def update_inventory(ingredient, quantity_used):
    # Recherche l’item dans inventaire (Nom Ingrédient)
    url = f"https://api.notion.com/v1/databases/{DATABASE_IDS['inventory']}/query"
    resp = requests.post(url, json={
        "filter": {
            "property": FIELDS['inventory']['ingredient'],
            "title": {"equals": ingredient}
        }
    }, headers=HEADERS)
    results = resp.json().get("results", [])
    if not results:
        print(f"{ingredient} non trouvé dans inventaire.")
        return
    # Met à jour le stock
    page_id = results[0]["id"]
    current_stock = results[0]["properties"][FIELDS['inventory']['stock']]['number']
    new_stock = current_stock - quantity_used
    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    requests.patch(update_url, json={
        "properties": {
            FIELDS['inventory']['stock']: {"number": new_stock}
        }
    }, headers=HEADERS)

def print_recipe_to_production(page_id, recipe_text):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    requests.patch(url, json={
        "properties": {
            FIELDS['productions']['recipe_field']: {"rich_text": [{"text": {"content": recipe_text}}]}
        }
    }, headers=HEADERS)

def main():
    productions = fetch_new_productions()
    for prod in productions:
        props = prod['properties']
        product = props[FIELDS['productions']['product']]['select']['name']
        factor = props[FIELDS['productions']['factor']]['number']
        page_id = prod['id']
        recipes = get_recipe(product)
        recipe_lines = []
        for rec in recipes:
            rec_props = rec['properties']
            ingredient = rec_props[FIELDS['recipes']['ingredient']]['title'][0]['text']['content']
            base_qty = rec_props[FIELDS['recipes']['quantity']]['number']
            unit = rec_props[FIELDS['recipes']['unit']]['rich_text'][0]['text']['content']
            qty_used = base_qty * factor
            # Met à jour l’inventaire
            update_inventory(ingredient, qty_used)
            # Ajoute à la recette pour impression
            recipe_lines.append(f"{ingredient}: {qty_used:.2f} {unit}")
        # Crée la recette affichée
        recipe_text = "\n".join(recipe_lines)
        print_recipe_to_production(page_id, recipe_text)
        print(f"Production traitée et recette imprimée pour {product} ({page_id})")

if __name__ == "__main__":
    main()
