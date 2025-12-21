import os
import django
import sys
from decimal import Decimal

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clothing.settings")
django.setup()

from app.models import Product, ProductVariant, Category
from chatbot.services import ProductSearchHandler

def verify():
    print("--- Setting up data ---")
    # Clean up
    Product.objects.filter(slug__in=['blue-shirt-verify', 'red-shirt-verify']).delete()
    Category.objects.filter(slug='shirts-verify').delete()

    category = Category.objects.create(name="Shirts Verify", slug="shirts-verify")
    prod1 = Product.objects.create(name="Blue Shirt Verify", slug="blue-shirt-verify", category=category, description="Cotton blue shirt")
    var1 = ProductVariant.objects.create(product=prod1, sku="BS-S-V", size="S", color="Blue", price=Decimal("500.00"), mrp=Decimal("600.00"))
    
    print(f"Created Product: {prod1} (Active: {prod1.is_active})")
    print(f"Created Variant: {var1} (Size: {var1.size}, Color: {var1.color})")

    handler = ProductSearchHandler()

    print("\n--- Test 1: Search by Keyword ---")
    msg = "looking for blue"
    resp = handler.handle(msg, {})
    print(f"Message: {msg}")
    print(f"Reply: {resp.get('reply')}")
    if 'products' in resp:
        print(f"Found: {[p['name'] for p in resp['products']]}")
    else:
        print("No products found")

    print("\n--- Test 2: Filter by Size ---")
    msg = "have size S"
    filters = {'size': 'S'}
    resp = handler.handle(msg, {}, filters)
    print(f"Message: {msg}")
    print(f"Filter: {filters}")
    print(f"Reply: {resp.get('reply')}")
    if 'products' in resp:
        print(f"Found: {[p['name'] for p in resp['products']]}")
    else:
        print("No products found")

    # Clean up
    prod1.delete()
    category.delete()

if __name__ == "__main__":
    verify()
