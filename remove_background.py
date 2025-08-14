from rembg import remove
from PIL import Image

input_path = 'image.jpg'
output_path = 'animal_cutout.jpg'

input_img = Image.open(input_path)
output_img = remove(input_img)
output_img.save(output_path)