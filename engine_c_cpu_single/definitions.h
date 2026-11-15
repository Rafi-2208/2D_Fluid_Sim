//
// Created by rafal on 26.08.2026.
//
#ifndef ENGINE_C_DEFINITIONS_H
#define ENGINE_C_DEFINITIONS_H

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#include <stdint.h>

#define MAX_PARTICLES_PER_AREA 128

typedef struct {
    float x, y;
} vector2D_t;

typedef struct {
    float x, y, z;
} vector3D_t;

typedef struct {
    vector3D_t position;
    vector3D_t velocity;
    float density;
    int area;
} particle_t;

typedef struct {
    vector3D_t point1;
    vector3D_t point2;
    vector3D_t point3;
    vector3D_t normal;
} wall_t;

typedef struct {
    wall_t *walls;
    int count;
} obstacles_t;

typedef struct {
    int area;
    int count;
    particle_t **particles;
} area_t;

typedef struct {
    vector3D_t position;
    float yaw;
    float pitch;
    float fov;
} camera_t;

EXPORT void update(particle_t *particles, int count, float delta_time, vector3D_t gravity_force,
                   obstacles_t walls, int collision_limit, float max_influence_radius, float target_density,
                   float pressure_multiplier, float collision_dampening, float viscosity, vector3D_t map_size,
                   area_t *areas, float friction_multiplier, float wall_default_push, int substeps);

void change_positions(particle_t *particles, int count, float delta_time, const obstacles_t *walls,
                      float collision_dampening, int collision_limit, float influence_radius, vector3D_t map_size);

float calculate_movement_and_wall_collision(particle_t *particle, const obstacles_t *walls, float delta_time,
                                            float collision_dampening, float influence_radius, vector3D_t map_size);

void calculate_bounce(particle_t *particle, wall_t wall, float delta_time, float collision_dampening);

float calculate_influence(const particle_t *particle_a, const particle_t *particle_b, float max_influence_radius,
                          float max_influence_radius_squared);

void calculate_densities(particle_t *particles, int count, float max_influence_radius,
                         const area_t *areas, vector3D_t map_size);

void calculate_forces(particle_t *particles, int count, float target_density,
                      float pressure_multiplier, float max_influence_radius,
                      float delta_time, const area_t *areas, vector3D_t map_size, float viscosity, obstacles_t walls,
                      float wall_default_push, vector3D_t gravity_force, float friction_multiplier);

vector3D_t calculate_wall_force(particle_t *particle, obstacles_t walls, float velocity_change_x,
                                float velocity_change_y, float velocity_change_z,
                                float max_influence_radius, float wall_default_push);

float calculate_distance_squared(const particle_t *particle_a, const particle_t *particle_b);

int get_area_code(vector3D_t point, float influence_radius, vector3D_t size);

void area_segregation(particle_t *particles, int count, area_t *areas, float max_influence_radius, vector3D_t size);

EXPORT void drawing(particle_t *particles, int count, obstacles_t *walls, int radius, vector2D_t screen_size,
                    uint32_t *frame_buffer, int colour_type, int pitch, float visual_pressure_multiplier,
                    camera_t camera);

typedef void (*engine_log_callback_t)(int level, const char *component, const char *message);
EXPORT void set_log_callback(engine_log_callback_t callback);

void drawing_particles(particle_t *particles, int count, int radius, vector2D_t screen_size, uint32_t *frame_buffer,
                       float *depth_buffer, int colour_type, int pitch, float visual_pressure_multiplier,
                       camera_t camera);

void drawing_walls(obstacles_t *walls, vector2D_t screen_size, uint32_t *frame_buffer, int pitch, camera_t camera);

#endif //ENGINE_C_DEFINITIONS_H
