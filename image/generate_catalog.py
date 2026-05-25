import os
import html
from urllib.parse import quote

def generate_catalog():
    # Base paths
    image_dir = os.path.dirname(os.path.abspath(__file__))
    menu_dir = os.path.join(image_dir, "menu")
    cake_dir = os.path.join(image_dir, "Image_cake")
    
    # Validate directories exist before listing
    if not os.path.isdir(menu_dir):
        raise FileNotFoundError(f"Menu image directory not found: {menu_dir}")
    if not os.path.isdir(cake_dir):
        raise FileNotFoundError(f"Cake image directory not found: {cake_dir}")
    
    # Read files
    menu_files = sorted([f for f in os.listdir(menu_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    cake_files = sorted([f for f in os.listdir(cake_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
    
    # Generate Menu cards HTML
    menu_cards_html = ""
    for f in menu_files:
        safe_src = "menu/" + quote(f, safe="")
        safe_alt = html.escape(f, quote=True)
        safe_text = html.escape(f)
        menu_cards_html += f"""
        <div class="card menu-card">
            <img src="{safe_src}" alt="Menu — {safe_alt}">
            <p>Menu: {safe_text}</p>
        </div>"""
        
    # Generate Cake cards HTML
    cake_cards_html = ""
    for f in cake_files:
        safe_src = "Image_cake/" + quote(f, safe="")
        safe_alt = html.escape(f, quote=True)
        safe_text = html.escape(f)
        cake_cards_html += f"""
        <div class="card">
            <img src="{safe_src}" alt="Cake — {safe_alt}">
            <p>{safe_text}</p>
        </div>"""
        
    # Full HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Cake Catalog Viewer</title>
    <style>
        body {{ font-family: sans-serif; background-color: #fcf8f2; color: #5c3d2e; margin: 20px; }}
        h1, h2 {{ border-bottom: 2px solid #e8837a; padding-bottom: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
        .card {{ background: white; border: 1px solid #e8837a; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; }}
        .card img {{ width: 100%; height: 200px; object-fit: cover; }}
        .card p {{ margin: 10px; font-weight: bold; font-size: 14px; overflow-wrap: break-word; word-break: normal; hyphens: auto; }}
        .menu-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .menu-card img {{ width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>Menu Flyers</h1>
    <div class="menu-grid">{menu_cards_html}
    </div>
    
    <h2>Cake Images in Image_cake</h2>
    <div class="grid">{cake_cards_html}
    </div>
</body>
</html>
"""
    
    # Write to catalog.html
    catalog_path = os.path.join(image_dir, "catalog.html")
    with open(catalog_path, "w", encoding="utf-8") as f_out:
        f_out.write(html_content)
        
    print(f"Successfully generated catalog.html at {catalog_path} with {len(menu_files)} menu flyers and {len(cake_files)} cake images.")

if __name__ == "__main__":
    generate_catalog()
