import pygame
from c_types import *
import random

wall_count = 4
walls_array = Wall * wall_count
walls_array = walls_array()
walls_array[0].point1 = Vector2D(100.0, 100.0)
walls_array[0].point2 = Vector2D(700.0, 100.0)
walls_array[1].point1 = Vector2D(700.0, 100.0)
walls_array[1].point2 = Vector2D(700.0, 500.0)
walls_array[2].point1 = Vector2D(700.0, 500.0)
walls_array[2].point2 = Vector2D(100.0, 500.0)
walls_array[3].point1 = Vector2D(100.0, 500.0)
walls_array[3].point2 = Vector2D(100.0, 100.0)
obstacles = Obstacles()
obstacles.count = wall_count
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

PARTICLE_COUNT = 1000
MAX_INFLUENCE_DISTANCE = 40
GRAVITY = Vector2D(0.0, 981.0)
COLLISION_LIMIT = 10
TARGET_DENSITY = 10000
PRESSURE_MULTIPLIER = 1.0
COLLISION_DAMPENING = 0.9


particles_array = Particle * PARTICLE_COUNT
particles_array = particles_array()
for i in range(PARTICLE_COUNT):
    start_x = random.uniform(150.0, 650.0)
    start_y = random.uniform(150.0, 450.0)
    particles_array[i].position = Vector2D(start_x, start_y)
    vel_x = random.uniform(-200.0, 200.0)
    vel_y = random.uniform(-200.0, 200.0)
    particles_array[i].velocity = Vector2D(vel_x, vel_y)



running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick(120) / 1000.0
    engine.update_positions(
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
    )
    for i in range(PARTICLE_COUNT):
        p = particles_array[i]
        colour_calculation_helper = min(1.0, p.density / 550000.0)
        r = int(colour_calculation_helper * 255)
        g = 50
        b = int((1.0 - colour_calculation_helper) * 255)
        pos = (int(p.position.x), int(p.position.y))
        pygame.draw.circle(screen, (r, g, b), pos, 3)
    for i in range(obstacles.count):
        wall = obstacles.walls[i]
        start_pos = (wall.point1.x, wall.point1.y)
        end_pos = (wall.point2.x, wall.point2.y)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)
    pygame.display.flip()

pygame.quit()
