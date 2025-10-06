import random
from database import SessionLocal, Product
import time

# Random data pools
PRODUCT_NAMES = [
    "Laptop", "Mouse", "Keyboard", "Monitor", "Headphones",
    "Webcam", "Microphone", "Tablet", "Smartphone", "Charger",
    "USB Cable", "HDMI Cable", "Router", "Printer", "Scanner",
    "External SSD", "RAM Module", "Graphics Card", "Motherboard", "CPU",
    "Power Supply", "Case", "Cooling Fan", "Thermal Paste", "Screwdriver Set"
]

ADJECTIVES = [
    "Pro", "Ultra", "Premium", "Essential", "Basic",
    "Advanced", "Elite", "Standard", "Deluxe", "Compact",
    "Wireless", "Portable", "Gaming", "Professional", "Budget"
]

CATEGORIES = [
    "Electronics", "Accessories", "Components", "Peripherals",
    "Networking", "Storage", "Audio", "Video", "Tools"
]

DESCRIPTIONS = [
    "High-performance device with advanced features",
    "Reliable and durable for everyday use",
    "Premium quality with extended warranty",
    "Compact design perfect for portability",
    "Professional-grade equipment for serious users",
    "Budget-friendly option without compromising quality",
    "Latest technology with cutting-edge specs",
    "Ergonomic design for maximum comfort",
    "Energy-efficient and environmentally friendly",
    "Compatible with all major platforms"
]

def generate_random_product():
    """Generate a single random product."""
    name = f"{random.choice(ADJECTIVES)} {random.choice(PRODUCT_NAMES)}"
    
    # Add model number sometimes
    if random.random() > 0.5:
        name += f" {random.choice(['X', 'Pro', 'Plus', 'Max'])}{random.randint(1, 9)}"
    
    category = random.choice(CATEGORIES)
    price = round(random.uniform(9.99, 1999.99), 2)
    description = random.choice(DESCRIPTIONS)
    stock = random.randint(0, 500)
    
    return Product(
        name=name,
        category=category,
        price=price,
        description=description,
        stock=stock
    )

def seed_database_in_batches(total_products=50, batch_size=5):
    """
    Seed database with random products in batches.
    
    Args:
        total_products: Total number of products to generate
        batch_size: Number of products to insert per batch
    """
    db = SessionLocal()
    
    # Clear existing data
    print("Clearing existing products...")
    db.query(Product).delete()
    db.commit()
    
    print(f"\nGenerating {total_products} products in batches of {batch_size}...")
    print("-" * 60)
    
    total_batches = (total_products + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        # Calculate how many products in this batch
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_products)
        current_batch_size = end_idx - start_idx
        
        # Generate batch
        batch = [generate_random_product() for _ in range(current_batch_size)]
        
        # Insert batch
        db.add_all(batch)
        db.commit()
        
        # Display batch info
        print(f"\n✓ Batch {batch_num + 1}/{total_batches} inserted ({current_batch_size} products):")
        for i, product in enumerate(batch, 1):
            print(f"  {start_idx + i}. {product.name} - ${product.price} ({product.category})")
        
        # Small delay between batches (optional, for visualization)
        if batch_num < total_batches - 1:
            time.sleep(0.5)
    
    db.close()
    
    print("\n" + "=" * 60)
    print(f"✓ Successfully seeded {total_products} products in {total_batches} batches!")
    print("=" * 60)

def display_database_stats():
    """Display statistics about the seeded database."""
    db = SessionLocal()
    
    total = db.query(Product).count()
    categories = db.query(Product.category).distinct().all()
    avg_price = db.query(Product).with_entities(Product.price).all()
    avg_price = sum(p[0] for p in avg_price) / len(avg_price) if avg_price else 0
    
    print("\n📊 Database Statistics:")
    print(f"   Total Products: {total}")
    print(f"   Categories: {len(categories)}")
    print(f"   Average Price: ${avg_price:.2f}")
    
    # Category breakdown
    print("\n   Products per Category:")
    for cat in categories:
        count = db.query(Product).filter(Product.category == cat[0]).count()
        print(f"     - {cat[0]}: {count}")
    
    db.close()

if __name__ == "__main__":
    # Customize these values
    TOTAL_PRODUCTS = 50
    BATCH_SIZE = 5
    
    seed_database_in_batches(
        total_products=TOTAL_PRODUCTS,
        batch_size=BATCH_SIZE
    )
    
    display_database_stats()