from PIL import Image

def resize_image(image, max_width, max_height):
    # Obtenir les dimensions de l'image
    width, height = image.size

    # Calculer les facteurs de mise à l'échelle pour la largeur et la hauteur
    ratio_width = max_width / width
    ratio_height = max_height / height

    # Choisir le ratio le plus petit pour conserver les proportions
    ratio = min(ratio_width, ratio_height)

    # Calculer les nouvelles dimensions de l'image
    new_width = int(width * ratio)
    new_height = int(height * ratio)

    # Redimensionner l'image
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)