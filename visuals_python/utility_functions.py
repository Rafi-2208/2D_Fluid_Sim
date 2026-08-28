
import math
def draw_text(surface, text, font, x, y, color=(255, 255, 255)):
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))

def rotate_vector(x, y, angle_degrees):
    rad = math.radians(angle_degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    new_x = x * cos_a - y * sin_a
    new_y = x * sin_a + y * cos_a
    return new_x, new_y