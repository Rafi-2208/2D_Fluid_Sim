//
// Created by rafal on 26.08.2026.
//
#ifndef ENGINE_C_DEFINITIONS_H
#define ENGINE_C_DEFINITIONS_H

#ifdef __cplusplus
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT __declspec(dllexport)
#endif

#define MAX_PARTICLES_PER_AREA 500

typedef struct {
    int count;
    int particle_indexes[MAX_PARTICLES_PER_AREA];
} gpu_area_t;

typedef struct {
    float x, y;
} vector2D_t;

typedef struct {
    vector2D_t position;
    vector2D_t velocity;
    float density;
    int area;
} particle_t;

typedef struct {
    vector2D_t point1;
    vector2D_t point2;
    vector2D_t normal;
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


EXPORT void update(particle_t *particles, int count, float delta_time, vector2D_t gravity_force,
                   obstacles_t walls, int collision_limit, float max_influence_radius, float target_density,
                   float pressure_multiplier, float collision_dampening, float viscosity, vector2D_t map_size,
                   area_t *areas , float friction_multiplier ,float wall_default_push , int substeps);

void __global__ kernel_change_positions(particle_t *particles, int count, float delta_time, const wall_t * walls, int wall_count, float collision_dampening,
                      int collision_limit, float influence_radius, vector2D_t map_size);

float __device__ calculate_movement_and_wall_collision(particle_t *particle, const wall_t * walls, int wall_count, float delta_time, float collision_dampening, float influence_radius, vector2D_t map_size);

void __device__ calculate_bounce(particle_t *particle, wall_t wall, float delta_time, float collision_dampening);

float __device__ calculate_distance_squared(const particle_t * particle_a, const particle_t * particle_b);

float __device__ calculate_influence(const particle_t * particle_a, const particle_t * particle_b, float max_influence_radius, float max_influence_radius_squared);

void __global__ kernel_calculate_densities(particle_t *particles, int count, float max_influence_radius,
                         const gpu_area_t *areas, vector2D_t map_size);

void __global__ kernel_calculate_forces(particle_t *particles, int count, float target_density,
                               float pressure_multiplier, float max_influence_radius,
                               float delta_time, const gpu_area_t *areas, vector2D_t map_size, float viscosity ,wall_t * walls , int wall_count,
                      float wall_default_push, vector2D_t gravity_force, float friction_multiplier);

vector2D_t __device__ calculate_wall_force(particle_t *particle, wall_t * walls, int wall_count, float velocity_change_x , float velocity_change_y , float max_influence_radius , float wall_default_push);

int __device__ get_area_code(vector2D_t point, float influence_radius, vector2D_t size);

void __global__ kernel_clear_grid(gpu_area_t *areas, int total_areas);

void __global__ kernel_area_segregation(particle_t *particles, int count, gpu_area_t *areas, float max_influence_radius, vector2D_t size, int area_count);

__global__ void drawing_particles(particle_t *particles, const int count, const int radius, const vector2D_t screen_size,
                       uint32_t *frame_buffer, const int colour_type, const int pitch,
                       const float visual_pressure_multiplier);

__device__ void drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer, int pitch);

__global__ void kernel_drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer, int pitch);

EXPORT void drawing(particle_t *particles, const int count, obstacles_t *walls, const int radius,
                    const vector2D_t screen_size, uint32_t *frame_buffer, const int colour_type, const int pitch,
                    const float visual_pressure_multiplier);

#endif //ENGINE_C_DEFINITIONS_H
