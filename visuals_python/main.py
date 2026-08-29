import time
import pygame
from c_types import *
import random
from utility_functions import *
from modifiable_variables import *
MAP_SIZE = Vector2D(MAP_SIZE[0] , MAP_SIZE[1])
GRAVITY = Vector2D(GRAVITY[0], GRAVITY[1])


WALL_COUNT = WALL_COUNT + RANDOM_WALL_COUNT
walls_array = Wall * WALL_COUNT
walls_array = walls_array()
walls_array[0].point1 = Vector2D(0.0, 0.0)
walls_array[0].point2 = Vector2D(2000.0, 0.0)
walls_array[1].point1 = Vector2D(2000.0, 0.0)
walls_array[1].point2 = Vector2D(2000.0, 1200.0)
walls_array[2].point1 = Vector2D(2000.0, 1200.0)
walls_array[2].point2 = Vector2D(0.0, 1200.0)
walls_array[3].point1 = Vector2D(0.0, 1200.0)
walls_array[3].point2 = Vector2D(0.0, 0.0)
walls_array[4].point1 = Vector2D(700.0, 1200.0)
walls_array[4].point2 = Vector2D(700.0, 0.0)
for i in range(RANDOM_WALL_COUNT):
    walls_array[i + 4].point1 = Vector2D(random.randint(0 , 2000), random.randint(0 , 1200))
    walls_array[i + 4].point2 = Vector2D(random.randint(-RANDOM_WALL_MAX_LEN, RANDOM_WALL_MAX_LEN) + walls_array[i + 4].point1.x, random.randint(-RANDOM_WALL_MAX_LEN, RANDOM_WALL_MAX_LEN) + walls_array[i + 4].point1.y)

obstacles = Obstacles()
obstacles.count = WALL_COUNT
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))




pygame.init()
screen = pygame.display.set_mode((int(MAP_SIZE.x) , int(MAP_SIZE.y)))
clock = pygame.time.Clock()
pygame.font.init()
main_font = pygame.font.SysFont(None, 30)

x_limit = int(MAP_SIZE.x / MAX_INFLUENCE_DISTANCE)
y_limit = int(MAP_SIZE.y / MAX_INFLUENCE_DISTANCE)
total_areas = x_limit * y_limit
areas_array = (Area * total_areas)()
for i in range(total_areas):
    areas_array[i].area = i
    areas_array[i].count = 0
    PointerArrayType = ctypes.POINTER(Particle) * MAX_PARTICLES_PER_AREA
    particle_pointers_buffer = PointerArrayType()
    areas_array[i].particles = ctypes.cast(particle_pointers_buffer, ctypes.POINTER(ctypes.POINTER(Particle)))



particles_array = Particle * PARTICLE_COUNT
particles_array = particles_array()
for i in range(PARTICLE_COUNT):
    start_x = random.randint(100, 800)
    start_y = random.randint(100, 1100)
    particles_array[i].position = Vector2D(start_x, start_y)
    vel_x = random.randint(0, 0)
    vel_y = random.randint(0, 0)
    particles_array[i].velocity = Vector2D(vel_x, vel_y)


t = time.time()
time.sleep(8)
running = True
while running:
    if time.time() - t > 20:
        walls_array[4].point1 = Vector2D(700.0, 1.0)
        walls_array[4].point2 = Vector2D(700.0, 0.0)
        obstacles = Obstacles()
        obstacles.count = WALL_COUNT
        obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))
        FRICTION_MULTIPLIER = .9999

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick_busy_loop(60) / 1000.0
    fps_value = clock.get_fps()

    if dt > 0.016:
        dt = 0.016

    engine.update(
        particles_array,
        PARTICLE_COUNT,
        dt,
        GRAVITY,
        obstacles,
        COLLISION_LIMIT,
        MAX_INFLUENCE_DISTANCE,
        TARGET_DENSITY,
        PRESSURE_MULTIPLIER,
        COLLISION_DAMPENING,
        VISCOSITY,
        MAP_SIZE,
        areas_array,
        FRICTION_MULTIPLIER
    )

    for i in range(PARTICLE_COUNT):
        if VISUAL_COLOUR == 0:
            p = particles_array[i]
            colour_calculation_helper = min(1.0, p.density / VISUAL_COLOUR_PRESSURE_MULTIPLIER)
            r = int(colour_calculation_helper * 255)
            g = 50
            b = int((1.0 - colour_calculation_helper) * 255)
            pos = (int(p.position.x), int(p.position.y))
            pygame.draw.circle(screen, (r, g, b), pos, VISUAL_RADIUS)
        elif VISUAL_COLOUR == 1:
            p = particles_array[i]
            colour_calculation_helper = min(1.0, p.density / VISUAL_COLOUR_PRESSURE_MULTIPLIER)
            lightness = 1.0 - colour_calculation_helper
            r = int(150 * lightness)
            g = int(50 + (150 * lightness))
            b = int(150 + (105 * lightness))
            pos = (int(p.position.x), int(p.position.y))
            pygame.draw.circle(screen, (r, g, b), pos, VISUAL_RADIUS)
    for i in range(obstacles.count):
        wall = obstacles.walls[i]
        start_pos = (wall.point1.x, wall.point1.y)
        end_pos = (wall.point2.x, wall.point2.y)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)

    draw_text(screen, "FPS: " + str(round(fps_value, 2)), main_font, 20, 20, (0, 255, 0))
    pygame.display.flip()

pygame.quit()
