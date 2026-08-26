import os
from PIL import Image, ImageDraw, ImageFont

def generate_icon(size, filename):
    # Create an image with an ultra-premium dark slate background
    img = Image.new("RGBA", (size, size), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw an outer radial-style gradient glowing ring
    center = size // 2
    ring_radius = int(size * 0.42)
    
    # Simple multi-layered circles to create a beautiful neon glow effect
    for i in range(25):
        alpha = int(8 - i * 0.3)
        if alpha < 1: alpha = 1
        r = ring_radius + i
        draw.ellipse([center - r, center - r, center + r, center + r], outline=(99, 102, 241, alpha), width=2)
        
    for i in range(15):
        alpha = int(12 - i * 0.7)
        if alpha < 1: alpha = 1
        r = ring_radius - i
        draw.ellipse([center - r, center - r, center + r, center + r], outline=(147, 51, 234, alpha), width=2)

    # Core circle (dark glass container)
    core_r = int(size * 0.36)
    draw.ellipse([center - core_r, center - core_r, center + core_r, center + core_r], fill=(30, 41, 59, 255), outline=(99, 102, 241, 100), width=4)
    
    # Draw geometric tech lines (archivist archive theme)
    # Line 1 (box arch top)
    box_w = int(size * 0.15)
    box_h = int(size * 0.12)
    draw.rectangle([center - box_w, center - box_h - int(size*0.05), center + box_w, center - int(size*0.05)], outline=(129, 140, 248, 180), width=3)
    
    # Draw a bold glowing letter "A" in the center using lines since fonts can fail to load
    # "A" points
    pt1 = (center, center - int(size * 0.12))
    pt2 = (center - int(size * 0.10), center + int(size * 0.12))
    pt3 = (center + int(size * 0.10), center + int(size * 0.12))
    
    # Draw lines with thickness
    draw.line([pt1, pt2], fill=(255, 255, 255, 255), width=int(size * 0.035))
    draw.line([pt1, pt3], fill=(255, 255, 255, 255), width=int(size * 0.035))
    # crossbar
    cb_y = center + int(size * 0.04)
    draw.line([(center - int(size * 0.06), cb_y), (center + int(size * 0.06), cb_y)], fill=(99, 102, 241, 255), width=int(size * 0.025))

    # Save
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename, "PNG")
    print(f"Generated {filename} ({size}x{size})")

if __name__ == "__main__":
    generate_icon(192, "templates/icons/icon-192.png")
    generate_icon(512, "templates/icons/icon-512.png")
