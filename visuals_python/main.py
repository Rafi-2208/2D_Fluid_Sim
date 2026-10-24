import random
from fileinput import filename

import pygame
from utility_functions import *
from modifiable_variables import *
import os
import platform
import time
import tkinter as tk
from tkinter import messagebox
from gui import Gui
import json

from app_logging import APP_LOGGER, configure_logging
from c_types import get_engine_mode, get_engine_name


def load_config(config_filename):
    try:
        with open(config_filename, "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        APP_LOGGER.info("Config file %s not found; using defaults", config_filename)
        return DEFAULT_VARIABLES.copy()
    except json.JSONDecodeError:
        APP_LOGGER.warning("Config file %s contains invalid JSON; using defaults", config_filename,
                           exc_info=True)
        return DEFAULT_VARIABLES.copy()
    except OSError:
        APP_LOGGER.exception("Could not read config file %s; using defaults", config_filename)
        return DEFAULT_VARIABLES.copy()
    if not isinstance(data, dict) or set(data.keys()) != set(DEFAULT_VARIABLES.keys()):
        APP_LOGGER.warning("Config file %s has an unexpected structure; using defaults", config_filename)
        return DEFAULT_VARIABLES.copy()
    APP_LOGGER.info("Loaded config from %s", config_filename)
    return data


def save_config(config_filename):
    config_data = VARIABLES.copy()
    for key, value in config_data.items():
        if hasattr(value, "x") and hasattr(value, "y"):
            config_data[key] = (value.x, value.y)

    with open(config_filename, "w") as file:
        json.dump(config_data, file)
    APP_LOGGER.info("Saved config to %s", config_filename)


def apply_config(config_filename):
    loaded_variables = load_config(config_filename)
    for key, value in loaded_variables.items():
        current_value = VARIABLES.get(key)
        if hasattr(current_value, "x") and hasattr(current_value, "y"):
            current_value.x = value[0]
            current_value.y = value[1]
        else:
            VARIABLES[key] = value
    VARIABLES["RESTART_CLICKED"] = True
    APP_LOGGER.info("Applied config from %s; simulation restart requested", config_filename)


def initialize_vectors():
    VARIABLES["MAP_SIZE"] = Vector2D(VARIABLES["MAP_SIZE"][0], VARIABLES["MAP_SIZE"][1])
    VARIABLES["NEW_MAP_SIZE"] = Vector2D(VARIABLES["NEW_MAP_SIZE"][0], VARIABLES["NEW_MAP_SIZE"][1])
    VARIABLES["GRAVITY"] = Vector2D(VARIABLES["GRAVITY"][0], VARIABLES["GRAVITY"][1])
    VARIABLES["STARTING_POSITION_X"] = Vector2D(VARIABLES["STARTING_POSITION_X"][0],
                                                VARIABLES["STARTING_POSITION_X"][1])
    VARIABLES["STARTING_POSITION_Y"] = Vector2D(VARIABLES["STARTING_POSITION_Y"][0],
                                                VARIABLES["STARTING_POSITION_Y"][1])
    VARIABLES["STARTING_SPEED_X"] = Vector2D(VARIABLES["STARTING_SPEED_X"][0], VARIABLES["STARTING_SPEED_X"][1])
    VARIABLES["STARTING_SPEED_Y"] = Vector2D(VARIABLES["STARTING_SPEED_Y"][0], VARIABLES["STARTING_SPEED_Y"][1])
    VARIABLES["WALL_POINT_1"] = Vector2D(VARIABLES["WALL_POINT_1"][0], VARIABLES["WALL_POINT_1"][1])
    VARIABLES["WALL_POINT_2"] = Vector2D(VARIABLES["WALL_POINT_2"][0], VARIABLES["WALL_POINT_2"][1])


def reset_vectors():
    VARIABLES["MAP_SIZE"] = (VARIABLES["MAP_SIZE"].x, VARIABLES["MAP_SIZE"].y)
    VARIABLES["NEW_MAP_SIZE"] = (VARIABLES["NEW_MAP_SIZE"].x, VARIABLES["NEW_MAP_SIZE"].y)
    VARIABLES["GRAVITY"] = (VARIABLES["GRAVITY"].x, VARIABLES["GRAVITY"].y)
    VARIABLES["STARTING_POSITION_X"] = (VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y)
    VARIABLES["STARTING_POSITION_Y"] = (VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y)
    VARIABLES["STARTING_SPEED_X"] = (VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y)
    VARIABLES["STARTING_SPEED_Y"] = (VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y)
    VARIABLES["WALL_POINT_1"] = (0, 0)
    VARIABLES["WALL_POINT_2"] = (0, 0)


def initialize_walls(saved_user_walls=None):
    if saved_user_walls is None:
        saved_user_walls = []

    walls_array = Wall * VARIABLES["MAX_WALLS"]
    walls_array = walls_array()

    walls_array[0].point1 = Vector2D(0.0, 0.0)
    walls_array[0].point2 = Vector2D(VARIABLES["MAP_SIZE"].x, 0.0)
    walls_array[1].point1 = Vector2D(VARIABLES["MAP_SIZE"].x, 0.0)
    walls_array[1].point2 = Vector2D(VARIABLES["MAP_SIZE"].x, VARIABLES["MAP_SIZE"].y)
    walls_array[2].point1 = Vector2D(VARIABLES["MAP_SIZE"].x, VARIABLES["MAP_SIZE"].y)
    walls_array[2].point2 = Vector2D(0.0, VARIABLES["MAP_SIZE"].y)
    walls_array[3].point1 = Vector2D(0.0, VARIABLES["MAP_SIZE"].y)
    walls_array[3].point2 = Vector2D(0.0, 0.0)

    for i in range(4, 4 + VARIABLES["RANDOM_WALL_COUNT"]):
        walls_array[i].point1 = Vector2D(random.randint(0, int(VARIABLES["MAP_SIZE"].x)),
                                         random.randint(0, int(VARIABLES["MAP_SIZE"].y)))
        walls_array[i].point2 = Vector2D(walls_array[i].point1.x + random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"],
                                                                                  VARIABLES["RANDOM_WALL_MAX_LEN"]),
                                         walls_array[i].point1.y + random.randint(-VARIABLES["RANDOM_WALL_MAX_LEN"],
                                                                                  VARIABLES["RANDOM_WALL_MAX_LEN"]))

    user_start_index = 4 + VARIABLES["RANDOM_WALL_COUNT"]
    for i, (p1, p2) in enumerate(saved_user_walls):
        walls_array[user_start_index + i].point1 = p1
        walls_array[user_start_index + i].point2 = p2

    total_walls = 4 + VARIABLES["RANDOM_WALL_COUNT"] + len(saved_user_walls)

    for i in range(total_walls):
        walls_array[i].normal = calculate_normal(walls_array[i])

    obstacles = Obstacles()
    obstacles.count = total_walls
    obstacles.walls = ctypes.cast(walls_array, ctypes.POINTER(Wall))

    return walls_array, obstacles


def initialize_areas():
    x_limit = int(VARIABLES["MAP_SIZE"].x / VARIABLES["MAX_INFLUENCE_DISTANCE"])
    y_limit = int(VARIABLES["MAP_SIZE"].y / VARIABLES["MAX_INFLUENCE_DISTANCE"])
    total_areas = x_limit * y_limit
    areas_array = (Area * total_areas)()

    for i in range(total_areas):
        areas_array[i].area = i
        areas_array[i].count = 0
        PointerArrayType = ctypes.POINTER(Particle) * VARIABLES["MAX_PARTICLES_PER_AREA"]
        particle_pointers_buffer = PointerArrayType()
        areas_array[i].particles = ctypes.cast(particle_pointers_buffer, ctypes.POINTER(ctypes.POINTER(Particle)))

    return areas_array


def initialize_particles(particle_count):
    particles_array = Particle * VARIABLES["MAX_PARTICLES"]
    particles_array = particles_array()

    pos_x_min = int(min(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
    pos_x_max = int(max(VARIABLES["STARTING_POSITION_X"].x, VARIABLES["STARTING_POSITION_X"].y))
    pos_y_min = int(min(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
    pos_y_max = int(max(VARIABLES["STARTING_POSITION_Y"].x, VARIABLES["STARTING_POSITION_Y"].y))
    spd_x_min = int(min(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
    spd_x_max = int(max(VARIABLES["STARTING_SPEED_X"].x, VARIABLES["STARTING_SPEED_X"].y))
    spd_y_min = int(min(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))
    spd_y_max = int(max(VARIABLES["STARTING_SPEED_Y"].x, VARIABLES["STARTING_SPEED_Y"].y))

    for i in range(particle_count):
        start_x = random.randint(pos_x_min, pos_x_max)
        start_y = random.randint(pos_y_min, pos_y_max)
        particles_array[i].position = Vector2D(start_x, start_y)

        vel_x = random.randint(spd_x_min, spd_x_max)
        vel_y = random.randint(spd_y_min, spd_y_max)
        particles_array[i].velocity = Vector2D(vel_x, vel_y)

    return particles_array


def add_user_wall(walls_array, obstacles):
    if VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"] < VARIABLES["MAX_WALLS"]:
        new_wall_index = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]
        walls_array[new_wall_index].point1 = Vector2D(VARIABLES["WALL_POINT_1"].x, VARIABLES["WALL_POINT_1"].y)
        walls_array[new_wall_index].point2 = Vector2D(VARIABLES["WALL_POINT_2"].x, VARIABLES["WALL_POINT_2"].y)
        walls_array[new_wall_index].normal = calculate_normal(walls_array[new_wall_index])
        VARIABLES["WALL_COUNT"] += 1
        obstacles.count = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]


def remove_user_wall(obstacles):
    if VARIABLES["WALL_COUNT"] > 4:
        VARIABLES["WALL_COUNT"] -= 1
        obstacles.count = VARIABLES["WALL_COUNT"] + VARIABLES["RANDOM_WALL_COUNT"]


def extract_saved_walls(walls_array, obstacles):
    user_wall_count = VARIABLES["WALL_COUNT"] - 4
    saved_user_walls = []

    for i in range(obstacles.count - user_wall_count, obstacles.count):
        p1 = Vector2D(walls_array[i].point1.x, walls_array[i].point1.y)
        p2 = Vector2D(walls_array[i].point2.x, walls_array[i].point2.y)
        saved_user_walls.append((p1, p2))

    return saved_user_walls


def handle_restart(walls_array, obstacles, gui):
    new_w, new_h = int(VARIABLES["NEW_MAP_SIZE"].x), int(VARIABLES["NEW_MAP_SIZE"].y)
    VARIABLES["MAP_SIZE"].x = new_w
    VARIABLES["MAP_SIZE"].y = new_h

    gui.pygame_frame.config(width=new_w, height=new_h)

    areas_array = initialize_areas()
    screen = pygame.display.set_mode((new_w, new_h))

    VARIABLES["PARTICLE_COUNT"] = int(VARIABLES["STARTING_PARTICLE_COUNT"])
    particles_array = initialize_particles(VARIABLES["PARTICLE_COUNT"])

    saved_user_walls = extract_saved_walls(walls_array, obstacles)
    walls_array, obstacles = initialize_walls(saved_user_walls)

    VARIABLES["RESTART_CLICKED"] = False

    return screen, areas_array, particles_array, walls_array, obstacles


def update_physics(particles_array, obstacles, areas_array, dt):
    if dt > 0.016:
        dt = 0.016

    friction_split_timing = VARIABLES["FRICTION_MULTIPLIER"] ** (1.0 / VARIABLES["SUB_STEPS"])
    wall_push_split_timing = VARIABLES["WALL_DEFAULT_PUSH"] / VARIABLES["SUB_STEPS"]

    get_engine().update(
        ctypes.cast(particles_array, ctypes.POINTER(Particle)),
        VARIABLES["PARTICLE_COUNT"],
        dt,
        VARIABLES["GRAVITY"],
        obstacles,
        VARIABLES["COLLISION_LIMIT"],
        VARIABLES["MAX_INFLUENCE_DISTANCE"],
        VARIABLES["TARGET_DENSITY"],
        VARIABLES["PRESSURE_MULTIPLIER"],
        VARIABLES["COLLISION_DAMPENING"],
        VARIABLES["VISCOSITY"],
        VARIABLES["MAP_SIZE"],
        areas_array,
        friction_split_timing,
        wall_push_split_timing,
        VARIABLES["SUB_STEPS"],
    )


def log_simulation_settings(obstacles):
    APP_LOGGER.info(
        "Simulation settings: engine=%s map=%sx%s particles=%d max_particles=%d walls=%d "
        "substeps=%d influence_radius=%s target_density=%s pressure_multiplier=%s gravity=(%s,%s)",
        get_engine_name(),
        VARIABLES["MAP_SIZE"].x,
        VARIABLES["MAP_SIZE"].y,
        VARIABLES["PARTICLE_COUNT"],
        VARIABLES["MAX_PARTICLES"],
        obstacles.count,
        VARIABLES["SUB_STEPS"],
        VARIABLES["MAX_INFLUENCE_DISTANCE"],
        VARIABLES["TARGET_DENSITY"],
        VARIABLES["PRESSURE_MULTIPLIER"],
        VARIABLES["GRAVITY"].x,
        VARIABLES["GRAVITY"].y,
    )


def draw_screen(screen, particles_array, obstacles, fps_value, main_font):
    screen.fill((0, 0, 0))
    screen.lock()

    pitch = screen.get_pitch()
    view = memoryview(screen.get_view('1'))
    buffer_array = (ctypes.c_uint32 * (len(view) // 4)).from_buffer(view)

    get_engine().drawing(
        ctypes.cast(particles_array, ctypes.POINTER(Particle)),
        VARIABLES["PARTICLE_COUNT"],
        ctypes.byref(obstacles),
        VARIABLES["VISUAL_RADIUS"],
        VARIABLES["MAP_SIZE"],
        buffer_array,
        VARIABLES["VISUAL_COLOUR"],
        pitch,
        VARIABLES["VISUAL_COLOUR_PRESSURE_MULTIPLIER"]
    )

    view.release()
    del buffer_array
    del view

    screen.unlock()

    if VARIABLES["FPS_COUNTER"]:
        draw_text(screen, "FPS: " + str(round(fps_value, 2)), main_font, 20, 20, (0, 255, 0))

    pygame.display.flip()


def main():
    configure_logging()
    APP_LOGGER.info("Application starting")
    VARIABLES.update(load_config("config.json"))
    initialize_engine()
    initialize_vectors()
    walls_array, obstacles = initialize_walls()
    areas_array = initialize_areas()
    particles_array = initialize_particles(VARIABLES["MAX_PARTICLES"])
    log_simulation_settings(obstacles)

    root = tk.Tk()
    gui = Gui(
        VARIABLES,
        root,
        apply_config,
        save_config
    )
    root.update()

    os.environ['SDL_WINDOWID'] = str(gui.pygame_frame.winfo_id())
    if platform.system() == "Windows":
        os.environ['SDL_VIDEODRIVER'] = 'windows'

    pygame.init()
    pygame.font.init()

    main_font = pygame.font.SysFont(None, 30)
    clock = pygame.time.Clock()
    screen = pygame.display.set_mode((int(VARIABLES["MAP_SIZE"].x), int(VARIABLES["MAP_SIZE"].y)))

    running = True
    summary_started = time.monotonic()
    summary_frame_count = 0
    summary_frame_time = 0.0
    summary_max_frame_time = 0.0

    def on_closing():
        nonlocal running
        APP_LOGGER.info("Window close requested")
        running = False

    root.protocol("WM_DELETE_WINDOW", on_closing)

    while running:
        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            APP_LOGGER.info("GUI window closed")
            running = False
            break
        if VARIABLES["RESTART_CLICKED"]:
            APP_LOGGER.info("Simulation restart requested")
            try:
                initialize_engine()
            except (OSError, ValueError) as error:
                APP_LOGGER.exception("Could not switch to the requested simulation engine")
                messagebox.showerror("Engine selection failed", str(error), parent=root)
                active_engine_mode = get_engine_mode()
                VARIABLES["RENDERING"] = active_engine_mode if active_engine_mode is not None else "auto"
            screen, areas_array, particles_array, walls_array, obstacles = handle_restart(walls_array, obstacles, gui)
            log_simulation_settings(obstacles)

        if VARIABLES["ADD_WALL_CLICKED"]:
            previous_wall_count = obstacles.count
            add_user_wall(walls_array, obstacles)
            if obstacles.count > previous_wall_count:
                APP_LOGGER.info("User added a wall; wall_count=%d", obstacles.count)
            else:
                APP_LOGGER.warning("User wall could not be added; maximum wall count reached")
            VARIABLES["ADD_WALL_CLICKED"] = False

        if VARIABLES["REMOVE_WALL_CLICKED"]:
            previous_wall_count = obstacles.count
            remove_user_wall(obstacles)
            if obstacles.count < previous_wall_count:
                APP_LOGGER.info("User removed a wall; wall_count=%d", obstacles.count)
            else:
                APP_LOGGER.warning("User wall could not be removed; no user-created walls remain")
            VARIABLES["REMOVE_WALL_CLICKED"] = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        dt = clock.tick_busy_loop(60) / 1000.0
        fps_value = clock.get_fps()
        frame_started = time.perf_counter()
        update_physics(particles_array, obstacles, areas_array, dt)
        draw_screen(screen, particles_array, obstacles, fps_value, main_font)
        frame_time = time.perf_counter() - frame_started
        summary_frame_count += 1
        summary_frame_time += frame_time
        summary_max_frame_time = max(summary_max_frame_time, frame_time)
        summary_elapsed = time.monotonic() - summary_started
        if summary_elapsed >= 60.0:
            average_fps = summary_frame_count / summary_elapsed
            average_frame_ms = summary_frame_time / summary_frame_count * 1000.0
            APP_LOGGER.info(
                "Simulation summary: avg_fps=%.2f avg_frame_ms=%.2f max_frame_ms=%.2f "
                "engine=%s particles=%d walls=%d substeps=%d",
                average_fps,
                average_frame_ms,
                summary_max_frame_time * 1000.0,
                get_engine_name(),
                VARIABLES["PARTICLE_COUNT"],
                obstacles.count,
                VARIABLES["SUB_STEPS"],
            )
            summary_started = time.monotonic()
            summary_frame_count = 0
            summary_frame_time = 0.0
            summary_max_frame_time = 0.0
    APP_LOGGER.info("Application shutting down")
    reset_vectors()
    save_config("config.json")
    pygame.quit()
    try:
        root.destroy()
    except tk.TclError:
        APP_LOGGER.debug("GUI window was already destroyed")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        configure_logging()
        APP_LOGGER.exception("Unhandled application error")
        raise