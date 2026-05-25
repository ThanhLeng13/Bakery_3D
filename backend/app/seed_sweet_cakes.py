import os
import sys
import io
import mimetypes
import traceback

# Set standard output encoding to utf-8 for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError
from storage3.utils import StorageException

# Load environment variables
load_dotenv()
url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not service_key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in environment variables.")
    sys.exit(1)

supabase = create_client(url, service_key)

# Local directories
cake_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "image", "Image_cake"))

# 18 Sweet Cakes mapping
sweet_cakes = [
    {
        "name": "Cheesecake Red Velvet",
        "price": 35000,
        "description": "Lớp bánh red velvet mềm mịn xen kẽ kem phô mai béo ngậy trong hũ tiện lợi.",
        "sizes": [{"name": "Hộp", "price": 35000}],
        "flavors": ["Red Velvet", "Phô mai"],
        "main_image": "47edd1ea-117a-4af9-a121-853fce784ad9.jpg",
        "alts": []
    },
    {
        "name": "Bánh tiramisu truyền thống",
        "price": 60000,
        "description": "Tiramisu Ý truyền thống thơm hương cà phê espresso và lớp kem mascarpone béo ngậy, phủ cacao và bột trà xanh.",
        "sizes": [{"name": "Hộp", "price": 60000}],
        "flavors": ["Cà phê", "Trà xanh"],
        "main_image": "ea8ece0e-c88f-49d8-a259-419cabfbab7c.jpg",
        "alts": []
    },
    {
        "name": "Bánh tiramisu gấu",
        "price": 55000,
        "description": "Tiramisu thơm ngon tạo hình chú gấu dễ thương, phủ bột cacao mịn màng.",
        "sizes": [{"name": "Hộp", "price": 55000}],
        "flavors": ["Cà phê", "Socola"],
        "main_image": "c229ed4a-8ed1-476b-b078-2434aeca9a4d.jpg",
        "alts": []
    },
    {
        "name": "Bánh cheese tươi",
        "price": 60000,
        "description": "Bánh kem sữa phô mai tươi mềm mịn, ngọt thanh mát lạnh đựng trong hũ square tiện dụng.",
        "sizes": [{"name": "Hộp", "price": 60000}],
        "flavors": ["Phô mai"],
        "main_image": "ee06dc81-7975-4a1b-ad48-a310e3dcf7ee.jpg",
        "alts": ["6e175830-fae4-47a5-ad68-61e96caeaf8d.jpg"]
    },
    {
        "name": "Bánh phomai sợi dẻo",
        "price": 55000,
        "description": "Bánh phô mai nướng với những sợi phô mai dai dẻo thơm ngậy trên mặt.",
        "sizes": [{"name": "Hộp", "price": 55000}],
        "flavors": ["Phô mai"],
        "main_image": "b23732eb-ec6c-4628-91e3-31f9b294b99c.jpg",
        "alts": []
    },
    {
        "name": "Bánh tart trứng",
        "price": 40000,
        "description": "Bánh tart trứng thơm lừng với vỏ ngàn lớp giòn tan và nhân kem trứng nướng mềm mịn (Hộp 3 cái).",
        "sizes": [{"name": "Hộp 3 cái", "price": 40000}],
        "flavors": ["Kem trứng"],
        "main_image": "e580c258-f2f4-409e-b006-4bb7b4664f58.jpg",
        "alts": []
    },
    {
        "name": "Bánh kem cốm dẻo",
        "price": 60000,
        "description": "Hương vị cốm dẻo thơm mát truyền thống kết hợp kem whipped cream béo ngọt nhẹ nhàng.",
        "sizes": [{"name": "Hộp", "price": 60000}],
        "flavors": ["Cốm dẻo"],
        "main_image": "b86b21db-c1f1-407a-8766-c86d93b4d554.jpg",
        "alts": []
    },
    {
        "name": "Bánh khoai lang phô mai",
        "price": 60000,
        "description": "Bánh khoai lang nướng bùi dẻo nhân phô mai kéo sợi thơm ngậy tuyệt hảo (Hộp 2 cái).",
        "sizes": [{"name": "Hộp 2 cái", "price": 60000}],
        "flavors": ["Khoai lang", "Phô mai"],
        "main_image": "24595024-e80a-4e97-87a0-2dfe8bce9d25.jpg",
        "alts": []
    },
    {
        "name": "Bánh mousse chanh dây",
        "price": 50000,
        "description": "Mousse chanh dây chua ngọt tươi mát, lớp thạch vàng óng mượt mà cùng cốt bánh mềm ẩm.",
        "sizes": [{"name": "Hộp", "price": 50000}],
        "flavors": ["Chanh dây"],
        "main_image": "444faa8c-56cc-4749-825e-8e16060f2d30.jpg",
        "alts": []
    },
    {
        "name": "Bánh Dark Oreo",
        "price": 60000,
        "description": "Bánh kem oreo cookies & cream giòn bùi thơm lừng vụn bánh oreo đậm đà.",
        "sizes": [{"name": "Hộp", "price": 60000}],
        "flavors": ["Oreo", "Cream"],
        "main_image": "a5485712-d9b8-4122-9547-50774f1a1c7b.jpg",
        "alts": ["b12428f4-1870-49cd-a567-7bc98b3f2d4c.jpg"]
    },
    {
        "name": "Bánh phô mai cháy",
        "price": 35000,
        "description": "Basque Burnt Cheesecake nướng cháy xém bề mặt thơm bùi, nhân phô mai tan chảy béo ngậy tuyệt hảo.",
        "sizes": [{"name": "Cái", "price": 35000}],
        "flavors": ["Phô mai"],
        "main_image": "1cfa1071-ffde-46f0-abfe-e94ed6b70f2f.jpg",
        "alts": []
    },
    {
        "name": "Bánh su kem",
        "price": 50000,
        "description": "Bánh su kem choux pastry mini nhân kem custard sữa ngọt mát mịn màng (Hộp 9 cái).",
        "sizes": [{"name": "Hộp 9 cái", "price": 50000}],
        "flavors": ["Vanilla custard"],
        "main_image": "ba4c9a91-9227-49b8-b14f-6ab4d6766087.jpg",
        "alts": []
    },
    {
        "name": "Bánh chuối nướng nước dừa",
        "price": 45000,
        "description": "Bánh chuối nướng dẻo ngọt, thơm đậm đà kết hợp nước cốt dừa béo ngậy.",
        "sizes": [{"name": "Hộp", "price": 45000}],
        "flavors": ["Chuối nướng", "Cốt dừa"],
        "main_image": "aec76ef0-ab38-4c4e-b34e-9e3aeebec9d0.jpg",
        "alts": []
    },
    {
        "name": "Bánh Brownie",
        "price": 45000,
        "description": "Brownie chocolate fudge đậm vị đắng ngọt, rắc hạnh nhân lát giòn bùi thơm nhẹ.",
        "sizes": [{"name": "Hộp", "price": 45000}],
        "flavors": ["Chocolate", "Hạnh nhân"],
        "main_image": "2d06e863-6a7d-456d-8a85-80f9a551e594.jpg",
        "alts": []
    },
    {
        "name": "Bánh kem trứng dừa nướng",
        "price": 50000,
        "description": "Bánh bông lan kem trứng nướng cháy bề mặt ngọt béo thơm lừng, rắc vụn dừa sấy khô giòn bùi.",
        "sizes": [{"name": "Hộp", "price": 50000}],
        "flavors": ["Kem trứng", "Dừa sấy"],
        "main_image": "9d3b66c9-c657-4dee-8428-556dfeeaad6f.jpg",
        "alts": []
    },
    {
        "name": "Bánh crepe sầu riêng",
        "price": 65000,
        "description": "Bánh crepe sầu riêng tươi thơm lừng, béo ngậy bọc trong lớp kem whipping mượt mà vỏ dai mịn (Hộp 4 cái).",
        "sizes": [{"name": "Hộp 4 cái", "price": 65000}],
        "flavors": ["Sầu riêng"],
        "main_image": "b52fe046-35bf-46e3-809b-9d707745182f.jpg",
        "alts": []
    },
    {
        "name": "Rau câu flan cheese",
        "price": 55000,
        "description": "Lớp rau câu cà phê giòn ngọt mát lạnh ôm trọn nhân bánh flan phô mai béo ngậy đặc trưng.",
        "sizes": [{"name": "Cái", "price": 55000}],
        "flavors": ["Cà phê flan"],
        "main_image": "772af16b-ec74-4474-bdbe-88244e8c4ee5.jpg",
        "alts": []
    },
    {
        "name": "Bánh gato flan",
        "price": 40000,
        "description": "Sự kết hợp hoàn hảo giữa lớp flan caramel ngọt ngào, béo ngậy và cốt bánh bông lan ẩm mịn.",
        "sizes": [{"name": "Cái", "price": 40000}],
        "flavors": ["Caramel flan"],
        "main_image": "33cce67e-2f11-456f-872d-a1fb3e1e7780.jpg",
        "alts": []
    }
]

def validate_all_images_exist():
    print("Validating that all local images referenced in sweet_cakes exist...")
    missing_images = []
    for item in sweet_cakes:
        main_path = os.path.join(cake_dir, item["main_image"])
        if not os.path.isfile(main_path):
            missing_images.append(item["main_image"])
        for alt_img in item["alts"]:
            alt_path = os.path.join(cake_dir, alt_img)
            if not os.path.isfile(alt_path):
                missing_images.append(alt_img)
    
    if missing_images:
        print(f"Error: The following {len(missing_images)} image file(s) are missing from '{cake_dir}':")
        for img in missing_images:
            print(f"  - {img}")
        sys.exit(1)
    
    print("All referenced images verified successfully.")

def clean_old_sweet_cakes():
    app_env = os.getenv("APP_ENV")
    if app_env not in ["development", "test"]:
        print(f"Aborting clean_old_sweet_cakes: APP_ENV='{app_env}' is not 'development' or 'test'.")
        return

    print("Checking database for old 'bánh ngọt' category products...")
    
    # 1. Get all active products with category 'bánh ngọt'
    res = supabase.table("products").select("id, name").eq("category", "bánh ngọt").eq("is_active", True).execute()
    old_products = res.data or []
    
    if not old_products:
        print("No active 'bánh ngọt' products found to deactivate.")
        return
        
    old_ids = [p["id"] for p in old_products]
    print(f"Found {len(old_products)} active 'bánh ngọt' products to deactivate: {[p['name'] for p in old_products]}")
    
    # 2. Perform a non-destructive update on products (set is_active=False)
    res_upd = supabase.table("products").update({"is_active": False}).in_("id", old_ids).execute()
    print(f"Deactivated products successfully: {len(res_upd.data or [])}")

def upload_image_to_storage(product_id, image_filename):
    local_path = os.path.join(cake_dir, image_filename)
    if not os.path.isfile(local_path):
        print(f"  Warning: Local image file {image_filename} not found at {local_path}!")
        return None
        
    storage_path = f"{product_id}/{image_filename}"
    
    try:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
            
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = "image/jpeg"
            
        print(f"  Uploading {image_filename} ({mime_type}) to storage '{storage_path}'...")
        
        # Upload
        supabase.storage.from_("product-images").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type, "cache-control": "3600"}
        )
        
        # Get public url
        public_url = supabase.storage.from_("product-images").get_public_url(storage_path)
        return public_url
    except StorageException as e:
        print(f"  Storage SDK exception uploading {image_filename} to {storage_path}: {e}")
        
        # Verify if it is a duplicate resource error (statusCode 409, Duplicate, or already exists message)
        is_duplicate = False
        err_msg = str(e).lower()
        if "duplicate" in err_msg or "already exists" in err_msg or "409" in err_msg:
            is_duplicate = True
            
        if is_duplicate:
            # If it already exists, let's try to get public URL directly as fallback
            try:
                public_url = supabase.storage.from_("product-images").get_public_url(storage_path)
                print(f"  Fallback: Retrieve public URL: {public_url}")
                return public_url
            except StorageException as fe:
                print(f"  Storage SDK fallback error retrieving public URL for {image_filename} at {storage_path}: {fe}")
                return None
            except Exception as fe:
                print(f"  Unexpected fallback error retrieving public URL for {image_filename} at {storage_path}: {fe}")
                return None
        else:
            # Not a duplicate error - do not fallback, re-raise to fail the script
            raise e
    except Exception as e:
        print(f"  Unexpected error during upload of {image_filename} to {storage_path}: {e}")
        raise e

def seed_products():
    print("\n--- SEEDING NEW SWEET CAKE PRODUCTS ---")
    for item in sweet_cakes:
        print(f"\nProcessing product: {item['name']}...")
        
        # Insert/update product
        product_data = {
            "name": item["name"],
            "description": item["description"],
            "category": "bánh ngọt",
            "base_price": item["price"],
            "sizes": item["sizes"],
            "flavors": item["flavors"],
            "is_active": True
        }
        
        try:
            # Check for existing product by name + category
            res_exist = supabase.table("products").select("id").eq("name", item["name"]).eq("category", product_data["category"]).execute()
            if res_exist.data:
                product_id = res_exist.data[0]["id"]
                print(f"  Product '{item['name']}' already exists with ID: {product_id}. Updating details and setting active.")
                res_prod = supabase.table("products").update(product_data).eq("id", product_id).execute()
            else:
                print(f"  Inserting new product '{item['name']}'...")
                res_prod = supabase.table("products").insert(product_data).execute()

            if not res_prod.data:
                print(f"  Error: Failed to insert/update product {item['name']}.")
                continue
                
            product = res_prod.data[0]
            product_id = product["id"]
            print(f"  Saved product '{item['name']}' with ID: {product_id}")
            
            # Upload main image
            main_img = item["main_image"]
            public_url = upload_image_to_storage(product_id, main_img)
            
            if public_url:
                # Check if this image URL already exists for the product
                res_img_exist = supabase.table("product_images").select("id").eq("product_id", product_id).eq("url", public_url).execute()
                if not res_img_exist.data:
                    # Insert product image record
                    img_data = {
                        "product_id": product_id,
                        "url": public_url,
                        "sort_order": 0
                    }
                    supabase.table("product_images").insert(img_data).execute()
                    print(f"  Associated main image: {main_img} -> {public_url}")
                else:
                    print(f"  Main image {main_img} already associated.")
                
            # Upload alternate images if any
            for alt_idx, alt_img in enumerate(item["alts"], start=1):
                alt_url = upload_image_to_storage(product_id, alt_img)
                if alt_url:
                    # Check if this alternate image URL already exists for the product
                    res_alt_exist = supabase.table("product_images").select("id").eq("product_id", product_id).eq("url", alt_url).execute()
                    if not res_alt_exist.data:
                        alt_data = {
                            "product_id": product_id,
                            "url": alt_url,
                            "sort_order": alt_idx
                        }
                        supabase.table("product_images").insert(alt_data).execute()
                        print(f"  Associated alt image #{alt_idx}: {alt_img} -> {alt_url}")
                    else:
                        print(f"  Alt image #{alt_idx} {alt_img} already associated.")
                    
        except APIError as e:
            print(f"  Postgrest API Error processing product {item['name']}: {e}")
            print(traceback.format_exc())
        except Exception as e:
            print(f"  Unexpected error processing product {item['name']}: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    validate_all_images_exist()
    clean_old_sweet_cakes()
    seed_products()
    print("\nSeeding finished successfully!")
