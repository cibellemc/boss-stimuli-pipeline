import argparse
from PIL import Image
import os

# Configuration
target_size = (512, 512)
quality = 80

def optimize(target_dir):
    if not os.path.exists(target_dir):
        print(f"Directory {target_dir} does not exist.")
        return

    files = [f for f in os.listdir(target_dir) if f.endswith('.png')]
    print(f"Found {len(files)} PNG files to optimize in '{target_dir}'.")
    
    for filename in files:
        file_path = os.path.join(target_dir, filename)
        try:
            with Image.open(file_path) as img:
                # Resize keeping aspect ratio or force square? 
                # The user said 512x512, I'll resize it to fit within 512x512
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                
                # Create webp name
                base_name = os.path.splitext(filename)[0]
                webp_path = os.path.join(target_dir, f"{base_name}.webp")
                
                # Save as webp
                img.save(webp_path, 'WEBP', quality=quality)
                
            # Delete original png
            os.remove(file_path)
            print(f"Optimized: {filename} -> {base_name}.webp")
            
        except Exception as e:
            print(f"Error optimizing {filename}: {e}")

    print("\nOptimization complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize PNG images to WebP.")
    parser.add_argument("--dir", required=True, help="Directory containing PNG images to optimize")
    args = parser.parse_args()
    
    optimize(args.dir)
