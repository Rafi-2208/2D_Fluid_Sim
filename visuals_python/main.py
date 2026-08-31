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
for i in range(RANDOM_WALL_COUNT):
    walls_array[i + 4].point1 = Vector2D(random.randint(0 , 2000), random.randint(0 , 1200))
    walls_array[i + 4].point2 = Vector2D(random.randint(-RANDOM_WALL_MAX_LEN, RANDOM_WALL_MAX_LEN) + walls_array[i + 4].point1.x, random.randint(-RANDOM_WALL_MAX_LEN, RANDOM_WALL_MAX_LEN) + walls_array[i + 4].point1.y)
for i in range(RANDOM_WALL_COUNT + WALL_COUNT):
    walls_array[i].normal = calculate_normal(walls_array[i])


obstacles = Obstacles()
obstacles.count = WALL_COUNT
obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))


FRICTION_MULTIPLIER = FRICTION_MULTIPLIER ** (1.0 / SUB_STEPS)
WALL_DEFAULT_PUSH = WALL_DEFAULT_PUSH / SUB_STEPS
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
    start_x = random.randint(10, 500)
    start_y = random.randint(10, 1190)
    particles_array[i].position = Vector2D(start_x, start_y)
    vel_x = random.randint(0, 0)
    vel_y = random.randint(0, 0)
    particles_array[i].velocity = Vector2D(vel_x, vel_y)

total_time = 0
time_update = 0
iteration = 0
drawing_time = 0
t = time.time()
running = True
while running:
    t = time.time()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    dt = clock.tick_busy_loop(60) / 1000.0
    fps_value = clock.get_fps()

    if dt > 0.016:
        dt = 0.016
    t2 = time.time()
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
        FRICTION_MULTIPLIER,
        WALL_DEFAULT_PUSH,
        SUB_STEPS,
    )
    time_update += time.time() - t2
    t3 = time.time()

    screen.fill((0, 0, 0))
    screen.lock()
    pitch = screen.get_pitch()
    view = memoryview(screen.get_view('1'))
    buffer_array = (ctypes.c_uint32 * (len(view) // 4)).from_buffer(view)
    engine.drawing(
        particles_array,
        PARTICLE_COUNT,
        ctypes.byref(obstacles),
        VISUAL_RADIUS,
        MAP_SIZE,
        buffer_array,
        VISUAL_COLOUR,
        pitch,
        VISUAL_COLOUR_PRESSURE_MULTIPLIER
    )
    drawing_time += time.time() - t3
    view.release()
    del buffer_array
    del view
    screen.unlock()
    if FPS_COUNTER:
        draw_text(screen, "FPS: " + str(round(fps_value, 2)), main_font, 20, 20, (0, 255, 0))
    pygame.display.flip()
    total_time += time.time() - t
    iteration+=1
    print(round((time_update + drawing_time) / (0.016 * iteration) , 4) , round(time_update / iteration * 1000 , 2) , round(total_time / iteration * 1000 , 2) , round(drawing_time / iteration * 1000 , 2))
pygame.quit()