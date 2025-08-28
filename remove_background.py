from rembg import remove
from PIL import Image

input_path = 'test_camera\crocodile\img_cat_20250821_114739.jpg'
output_path = 'animal_cutout.jpg'

input_img = Image.open(input_path)
output_img = remove(input_img)
image_rgb = output_img.convert("RGB")
image_rgb.save("output.jpg")
