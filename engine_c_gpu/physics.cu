#include "definitions.h"
#include <cuda_runtime.h>
particle_t *d_particles = nullptr;
wall_t *d_walls = nullptr;
gpu_area_t *d_areas = nullptr;
uint32_t *d_frame_buffer = nullptr;
int current_frame_buffer_size = 0;


void __global__ kernel_change_positions(particle_t *particles, const int count, const float delta_time,
                                        const wall_t *walls, const int wall_count,
                                        const float collision_dampening, const int collision_limit,
                                        const float influence_radius,
                                        const vector2D_t map_size) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles + i, walls, wall_count, time_left,
                                                              collision_dampening, influence_radius, map_size);
            if (counter >= collision_limit) {
                break;
            }
        }
    }
}

//A + t(B - A) = C + u(D - C)
//returns remaining time in a frameA
float __device__ calculate_movement_and_wall_collision(particle_t *particle, const wall_t *walls,
                                                       const int wall_count, const float delta_time,
                                                       const float collision_dampening,
                                                       const float influence_radius,
                                                       const vector2D_t map_size) {
    const vector2D_t position_before = particle->position;
    vector2D_t position_after = particle->position;
    position_after.x = position_before.x + particle->velocity.x * delta_time;
    position_after.y = position_before.y + particle->velocity.y * delta_time;
    float result = 2;
    int hit_wall_index = -1;
    for (int i = 0; i < wall_count; i++) {
        const wall_t current_wall = *(walls + i);
        const float dX1 = position_after.x - position_before.x;
        const float dY1 = position_after.y - position_before.y;
        const float dX2 = current_wall.point1.x - current_wall.point2.x;
        const float dY2 = current_wall.point1.y - current_wall.point2.y;
        const float dX3 = current_wall.point1.x - position_before.x;
        const float dY3 = current_wall.point1.y - position_before.y;
        const float W = dX1 * dY2 - dY1 * dX2;
        const float Wt = dX3 * dY2 - dY3 * dX2;
        const float Wu = dX1 * dY3 - dY1 * dX3;
        if (W != 0) {
            const float t = Wt / W;
            const float u = Wu / W;
            if (u >= -0.01f && u <= 1.01f && t > 0 && t <= 1) {
                if (result > t) {
                    result = t;
                    hit_wall_index = i;
                }
            }
        }
    }
    if (result != 2) {
        calculate_bounce(particle, *(walls + hit_wall_index), result * delta_time, collision_dampening);
        return delta_time * (1 - result);
    }
    particle->position = position_after;
    particle->area = get_area_code(particle->position, influence_radius, map_size);
    return 0;
}


void __device__ calculate_bounce(particle_t *particle, const wall_t wall, const float delta_time,
                                 const float collision_dampening) {
    particle->position.x = particle->position.x + particle->velocity.x * delta_time;
    particle->position.y = particle->position.y + particle->velocity.y * delta_time;
    vector2D_t normal = {-(wall.point2.y - wall.point1.y), wall.point2.x - wall.point1.x};
    const float normal_length = sqrtf(normal.x * normal.x + normal.y * normal.y);
    if (normal_length > 0) {
        normal.x = normal.x / normal_length;
        normal.y = normal.y / normal_length;
        float dot_product_wall_velocity = particle->velocity.x * normal.x + particle->velocity.y * normal.y;
        if (dot_product_wall_velocity > 0) {
            normal.x = -normal.x;
            normal.y = -normal.y;
            dot_product_wall_velocity = -dot_product_wall_velocity;
        }
        particle->velocity.x = particle->velocity.x - (1.0f + collision_dampening) * dot_product_wall_velocity * normal.
                               x;
        particle->velocity.y = particle->velocity.y - (1.0f + collision_dampening) * dot_product_wall_velocity * normal.
                               y;
        particle->position.x = particle->position.x + normal.x * 0.05f;
        particle->position.y = particle->position.y + normal.y * 0.05f;
    }
}


float __device__ calculate_distance_squared(const particle_t *particle_a, const particle_t *particle_b) {
    const float distance_x = particle_a->position.x - particle_b->position.x;
    const float distance_y = particle_a->position.y - particle_b->position.y;
    return distance_x * distance_x + distance_y * distance_y;
}

float __device__ calculate_influence(const particle_t *particle_a, const particle_t *particle_b,
                                     const float max_influence_radius,
                                     const float max_influence_radius_squared) {
    const float distance_squared = calculate_distance_squared(particle_a, particle_b);
    if (distance_squared < max_influence_radius_squared) {
        const float distance = sqrtf(distance_squared);
        return (max_influence_radius - distance) * (max_influence_radius - distance) * (
                   max_influence_radius - distance);
    }
    return 0;
}


void __global__ kernel_calculate_densities(particle_t *particles, const int count, const float max_influence_radius,
                                           const gpu_area_t *areas, const vector2D_t map_size) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    const int x_limit = (int) (map_size.x / max_influence_radius);
    const int y_limit = (int) (map_size.y / max_influence_radius);
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        particles[i].density = 0;
        const int cell_x = (int) (particles[i].position.x / max_influence_radius);
        const int cell_y = (int) (particles[i].position.y / max_influence_radius);
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                const int neighbor_x = cell_x + dx;
                const int neighbor_y = cell_y + dy;
                if (neighbor_x >= 0 && neighbor_x < x_limit &&
                    neighbor_y >= 0 && neighbor_y < y_limit) {
                    const int cell_index = neighbor_y * x_limit + neighbor_x;
                    int limit = areas[cell_index].count;
                    if (limit > MAX_PARTICLES_PER_AREA) {
                        limit = MAX_PARTICLES_PER_AREA;
                    }
                    for (int j = 0; j < limit; j++) {
                        int neighbor_idx = areas[cell_index].particle_indexes[j];
                        particles[i].density += calculate_influence(&particles[i], &particles[neighbor_idx],
                                                                    max_influence_radius, max_influence_radius_squared);
                    }
                }
            }
        }
    }
}


void __global__ kernel_calculate_forces(particle_t *particles, const int count, const float target_density,
                                        const float pressure_multiplier, const float max_influence_radius,
                                        const float delta_time, const gpu_area_t *areas, const vector2D_t map_size,
                                        const float viscosity, wall_t *walls, int wall_count,
                                        float wall_default_push, vector2D_t gravity_force, float friction_multiplier) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    const int x_limit = (int) (map_size.x / max_influence_radius);
    const int y_limit = (int) (map_size.y / max_influence_radius);
    float gravity_per_time_x = gravity_force.x * delta_time;
    float gravity_per_time_y = gravity_force.y * delta_time;
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        const float pressure = (particles[i].density - target_density) * pressure_multiplier;
        const int cell_x = (int) (particles[i].position.x / max_influence_radius);
        const int cell_y = (int) (particles[i].position.y / max_influence_radius);
        float velocity_change_x = gravity_per_time_x;
        float velocity_change_y = gravity_per_time_y;
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                const int neighbor_x = cell_x + dx;
                const int neighbor_y = cell_y + dy;
                if (neighbor_x >= 0 && neighbor_x < x_limit &&
                    neighbor_y >= 0 && neighbor_y < y_limit) {
                    const int cell_index = neighbor_y * x_limit + neighbor_x;
                    int limit = areas[cell_index].count;
                    if (limit > MAX_PARTICLES_PER_AREA) limit = MAX_PARTICLES_PER_AREA;
                    for (int j = 0; j < limit; j++) {
                        int neighbor_id = areas[cell_index].particle_indexes[j];
                        if (i != neighbor_id) {
                            const float distance_squared = calculate_distance_squared(
                                particles + i, &particles[neighbor_id]);
                            if (distance_squared < max_influence_radius_squared) {
                                const float distance = sqrtf(distance_squared);
                                if (0.001f < distance_squared) {
                                    const float pressure2 =
                                            (particles[neighbor_id].density - target_density) * pressure_multiplier;
                                    const float average_pressure = (pressure + pressure2) / 2;
                                    if (average_pressure > 0) {
                                        const float pressure_gradient =
                                                (max_influence_radius - distance) * (max_influence_radius - distance);
                                        const vector2D_t pressure_force_vector = {
                                            (particles[i].position.x - particles[neighbor_id].position.x) / distance *
                                            pressure_gradient * average_pressure,
                                            (particles[i].position.y - particles[neighbor_id].position.y) / distance *
                                            pressure_gradient * average_pressure,
                                        };
                                        velocity_change_x += +pressure_force_vector.x * delta_time;
                                        velocity_change_y += +pressure_force_vector.y * delta_time;
                                    }
                                }
                                const float viscosity_relative =
                                        (1 - distance / max_influence_radius) * viscosity * delta_time;
                                velocity_change_x += (particles[neighbor_id].velocity.x - particles[i].velocity.x) *
                                        viscosity_relative;
                                velocity_change_y += (particles[neighbor_id].velocity.y - particles[i].velocity.y) *
                                        viscosity_relative;
                            }
                        }
                    }
                }
            }
        }
        vector2D_t wall_push = calculate_wall_force(particles + i, walls, wall_count, velocity_change_x,
                                                    velocity_change_y, max_influence_radius, wall_default_push);
        particles[i].velocity.x += velocity_change_x + wall_push.x;
        particles[i].velocity.y += velocity_change_y + wall_push.y;
        particles[i].velocity.x = particles[i].velocity.x * friction_multiplier;
        particles[i].velocity.y = particles[i].velocity.y * friction_multiplier;
    }
}

vector2D_t __device__ calculate_wall_force(particle_t *particle, wall_t *walls, int wall_count, float velocity_change_x,
                                           float velocity_change_y, float max_influence_radius,
                                           float wall_default_push) {
    vector2D_t wall_force = {0, 0};
    for (int i = 0; i < wall_count; i++) {
        float directional_distance = (particle->position.x - walls[i].point1.x) * walls[i].normal.x +
                                     (particle->position.y - walls[i].point1.y) * walls[i].normal.y;
        float distance = directional_distance;
        float sign = 1;
        if (distance < 0) {
            distance = -distance;
            sign = -1;
        }
        if (distance < max_influence_radius) {
            float vel_along_normal = walls[i].normal.x * velocity_change_x +
                                     walls[i].normal.y * velocity_change_y;

            if (directional_distance * vel_along_normal < 0) {
                float distance_factor = (1.0f - distance / max_influence_radius);
                float distance_factor_squared = distance_factor * distance_factor;
                float force_magnitude = -vel_along_normal * distance_factor_squared;
                wall_force.x += force_magnitude * walls[i].normal.x + walls[i].normal.x * wall_default_push * sign;
                wall_force.y += force_magnitude * walls[i].normal.y + walls[i].normal.y * wall_default_push * sign;;
            }
        }
    }
    return wall_force;
}

int __device__ get_area_code(const vector2D_t point, const float influence_radius, const vector2D_t size) {
    int x = (int) (point.x / influence_radius);
    int y = (int) (point.y / influence_radius);

    const int x_limit = (int) (size.x / influence_radius);
    const int y_limit = (int) (size.y / influence_radius);
    if (x < 0) {
        x = 0;
    }
    if (x >= x_limit) {
        x = x_limit - 1;
    }
    if (y < 0) {
        y = 0;
    }
    if (y >= y_limit) {
        y = y_limit - 1;
    }
    return y * x_limit + x;
}

__global__ void kernel_clear_grid(gpu_area_t *areas, int total_areas) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < total_areas) {
        areas[i].count = 0;
    }
}

__global__ void kernel_area_segregation(particle_t *particles, const int count, gpu_area_t *areas,
                                        const float max_influence_radius, const vector2D_t size, const int area_count) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        int area_code = get_area_code((particles + i)->position, max_influence_radius, size);
        if (area_code >= 0 && area_code < area_count) {
            int insert_id = atomicAdd(&areas[area_code].count, 1);
            if (insert_id < MAX_PARTICLES_PER_AREA) {
                areas[area_code].particle_indexes[insert_id] = i;
            }
        }
    }
}

EXPORT void update(particle_t *particles, const int count, float delta_time, const vector2D_t gravity_force,
                   const obstacles_t walls, const int collision_limit, const float max_influence_radius,
                   const float target_density, const float pressure_multiplier, const float collision_dampening,
                   const float viscosity, const vector2D_t map_size, area_t *areas, const float friction_multiplier,
                   float wall_default_push , int substeps) {

    
    const int x_limit = (int) (map_size.x / max_influence_radius);
    const int y_limit = (int) (map_size.y / max_influence_radius);
    int total_areas = x_limit * y_limit;
    if (d_particles == nullptr) {
        cudaMalloc((void **) &d_particles, count * sizeof(particle_t));
        cudaMalloc((void **) &d_walls, walls.count * sizeof(wall_t));
        cudaMalloc((void **) &d_areas, total_areas * sizeof(gpu_area_t));
    }
    cudaMemcpy(d_particles, particles, count * sizeof(particle_t), cudaMemcpyHostToDevice);
    cudaMemcpy(d_walls, walls.walls, walls.count * sizeof(wall_t), cudaMemcpyHostToDevice);
    int threads = 256;
    int blocks = (count + threads - 1) / threads;
    int area_blocks = (total_areas + threads - 1) / threads;
    delta_time = delta_time / (float)substeps;
    for (int i = 0; i < substeps; i++) {
        kernel_clear_grid<<<area_blocks , threads>>>(d_areas, total_areas);
        kernel_area_segregation<<<blocks , threads>>>(d_particles, count, d_areas, max_influence_radius, map_size,
                                                      total_areas);
        kernel_calculate_densities<<<blocks , threads>>>(d_particles, count, max_influence_radius, d_areas, map_size);
        kernel_calculate_forces<<<blocks , threads>>>(d_particles, count, target_density, pressure_multiplier,
                                                      max_influence_radius,
                                                      delta_time,
                                                      d_areas, map_size, viscosity, d_walls, walls.count, wall_default_push,
                                                      gravity_force, friction_multiplier);
        kernel_change_positions<<<blocks , threads>>>(d_particles, count, delta_time, d_walls, walls.count,
                                                      collision_dampening,
                                                      collision_limit, max_influence_radius,
                                                      map_size);
    }
    cudaDeviceSynchronize();
    cudaMemcpy(particles, d_particles, count * sizeof(particle_t), cudaMemcpyDeviceToHost);
}


__global__ void drawing_particles(particle_t *particles, const int count, const int radius,
                                  const vector2D_t screen_size,
                                  uint32_t *frame_buffer, const int colour_type, const int pitch,
                                  const float visual_pressure_multiplier) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        int x = (int) particles[i].position.x;
        int y = (int) particles[i].position.y;
        float density = particles[i].density;
        float colour_calculation_helper = density / visual_pressure_multiplier;
        if (colour_calculation_helper > 1) {
            colour_calculation_helper = 1;
        }
        int r = 0, g = 0, b = 0;
        if (colour_type == 0) {
            r = (int) (colour_calculation_helper * 255);
            g = 50;
            b = (int) ((1 - colour_calculation_helper) * 255);
        } else if (colour_type == 1) {
            float lightness = 1 - colour_calculation_helper;
            r = (int) (150 * lightness);
            g = (int) (50 + 150 * lightness);
            b = (int) (150 + 105 * lightness);
        }
        uint32_t colour = (255 << 24) | (r << 16) | (g << 8) | b;
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dy = -radius; dy <= radius; dy++) {
                if (dx * dx + dy * dy < radius * radius) {
                    if (x + dx >= 0 && y + dy >= 0 && x + dx < (int) screen_size.x && y + dy < (int) screen_size.y) {
                        int index = ((y + dy) * (pitch / 4)) + x + dx;
                        frame_buffer[index] = colour;
                    }
                }
            }
        }
    }
}

__device__ void drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer,
                              int pitch) {
    for (int i = 0; i < wall_count; i++) {
        int start_x = (int) walls[i].point1.x;
        int start_y = (int) walls[i].point1.y;
        int end_x = (int) walls[i].point2.x;
        int end_y = (int) walls[i].point2.y;
        uint32_t colour = (255 << 24) | (255 << 16) | (255 << 8) | 255;
        int dx = start_x - end_x;
        int dy = start_y - end_y;
        if (dx < 0) {
            dx = -dx;
        }
        if (dy > 0) {
            dy = -dy;
        }
        int step_x = 1;
        int step_y = 1;
        if (end_x < start_x) {
            step_x = -1;
        }
        if (end_y < start_y) {
            step_y = -1;
        }
        int error = dx + dy;
        while (1) {
            if (start_x >= 0 && start_x < (int) screen_size.x && start_y >= 0 && start_y < (int) screen_size.y) {
                int index = (start_y * (pitch / 4)) + start_x;
                frame_buffer[index] = colour;
            }
            if (start_x == end_x && start_y == end_y) {
                break;
            }
            int error2 = error * 2;
            if (error2 >= dy) {
                error += dy;
                start_x += step_x;
            }
            if (error2 <= dx) {
                error += dx;
                start_y += step_y;
            }
        }
    }
}


__global__ void kernel_drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer,
                                     int pitch) {
    if (threadIdx.x == 0 && blockIdx.x == 0) {
        drawing_walls(walls, wall_count, screen_size, frame_buffer, pitch);
    }
}

EXPORT void drawing(particle_t *particles, const int count, obstacles_t *walls, const int radius,
                    const vector2D_t screen_size, uint32_t *frame_buffer, const int colour_type, const int pitch,
                    const float visual_pressure_multiplier) {
    int required_buffer_size = (pitch / 4) * (int) screen_size.y * sizeof(uint32_t);
    if (current_frame_buffer_size < required_buffer_size) {
        if (d_frame_buffer != nullptr) cudaFree(d_frame_buffer);
        cudaMalloc((void **) &d_frame_buffer, required_buffer_size);
        current_frame_buffer_size = required_buffer_size;
    }
    cudaMemset(d_frame_buffer, 0, required_buffer_size);

    int threads = 256;
    int blocks = (count + threads - 1) / threads;
    drawing_particles<<<blocks, threads>>>(d_particles, count, radius, screen_size,
                                           d_frame_buffer, colour_type, pitch,
                                           visual_pressure_multiplier);

    kernel_drawing_walls<<<1, 1>>>(d_walls, walls->count, screen_size, d_frame_buffer, pitch);
    cudaDeviceSynchronize();
    cudaMemcpy(frame_buffer, d_frame_buffer, required_buffer_size, cudaMemcpyDeviceToHost);
}
