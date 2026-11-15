#include "definitions.h"
#include <stdarg.h>
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <math.h>
#include <cuda_runtime.h>

static engine_log_callback_t log_callback = nullptr;

EXPORT void set_log_callback(engine_log_callback_t callback) {
    log_callback = callback;
}

static void native_log(int level, const char *component, const char *format, ...) {
    if (log_callback == nullptr) {
        return;
    }
    char message[512];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    log_callback(level, component, message);
}

static bool check_cuda(cudaError_t status, const char *operation) {
    if (status == cudaSuccess) {
        return true;
    }
    native_log(3, "CUDA", "%s failed: %s", operation, cudaGetErrorString(status));
    return false;
}

static bool check_kernel_launch(const char *operation) {
    return check_cuda(cudaGetLastError(), operation);
}

particle_t *d_particles = nullptr;
wall_t *d_walls = nullptr;
gpu_area_t *d_areas = nullptr;
uint32_t *d_frame_buffer = nullptr;
unsigned long long *d_zbuffer = nullptr;
size_t current_frame_buffer_pixels = 0;
int old_count = 0;
int old_wall_count = 0;
int old_total_areas = 0;

void __global__ kernel_change_positions(particle_t *particles, const int count, const float delta_time,
                                        const wall_t *walls, const int wall_count,
                                        const float collision_dampening, const int collision_limit,
                                        const float influence_radius, const vector3D_t map_size) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0.0f) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles + i, walls, wall_count, time_left,
                                                              collision_dampening, influence_radius, map_size);
            if (counter >= collision_limit) {
                break;
            }
        }
        if (particles[i].position.x < 0.1f) {
            particles[i].position.x = 0.1f;
            if (particles[i].velocity.x < 0.0f) particles[i].velocity.x = -particles[i].velocity.x * collision_dampening;
        } else if (particles[i].position.x > map_size.x - 0.1f) {
            particles[i].position.x = map_size.x - 0.1f;
            if (particles[i].velocity.x > 0.0f) particles[i].velocity.x = -particles[i].velocity.x * collision_dampening;
        }
        if (particles[i].position.y < 0.1f) {
            particles[i].position.y = 0.1f;
            if (particles[i].velocity.y < 0.0f) particles[i].velocity.y = -particles[i].velocity.y * collision_dampening;
        } else if (particles[i].position.y > map_size.y - 0.1f) {
            particles[i].position.y = map_size.y - 0.1f;
            if (particles[i].velocity.y > 0.0f) particles[i].velocity.y = -particles[i].velocity.y * collision_dampening;
        }
        if (particles[i].position.z < 0.1f) {
            particles[i].position.z = 0.1f;
            if (particles[i].velocity.z < 0.0f) particles[i].velocity.z = -particles[i].velocity.z * collision_dampening;
        } else if (particles[i].position.z > map_size.z - 0.1f) {
            particles[i].position.z = map_size.z - 0.1f;
            if (particles[i].velocity.z > 0.0f) particles[i].velocity.z = -particles[i].velocity.z * collision_dampening;
        }
        particles[i].area = get_area_code(particles[i].position, influence_radius, map_size);
    }
}

float __device__ calculate_movement_and_wall_collision(particle_t *particle, const wall_t *walls,
                                                       const int wall_count, const float delta_time,
                                                       const float collision_dampening,
                                                       const float influence_radius,
                                                       const vector3D_t map_size) {
    const vector3D_t position_before = particle->position;
    const vector3D_t d = {
        particle->velocity.x * delta_time,
        particle->velocity.y * delta_time,
        particle->velocity.z * delta_time
    };
    const vector3D_t position_after = {
        position_before.x + d.x,
        position_before.y + d.y,
        position_before.z + d.z
    };

    float result = 2.0f;
    int hit_wall_index = -1;

    for (int i = 0; i < wall_count; i++) {
        const wall_t w = walls[i];
        const float denom = d.x * w.normal.x + d.y * w.normal.y + d.z * w.normal.z;
        if (fabsf(denom) > 1e-6f) {
            const float diff_x = w.point1.x - position_before.x;
            const float diff_y = w.point1.y - position_before.y;
            const float diff_z = w.point1.z - position_before.z;
            const float t = (diff_x * w.normal.x + diff_y * w.normal.y + diff_z * w.normal.z) / denom;
            if (t > 0.0f && t <= 1.0f && t < result) {
                const float hx = position_before.x + t * d.x - w.point1.x;
                const float hy = position_before.y + t * d.y - w.point1.y;
                const float hz = position_before.z + t * d.z - w.point1.z;

                const float ux = w.point2.x - w.point1.x;
                const float uy = w.point2.y - w.point1.y;
                const float uz = w.point2.z - w.point1.z;

                const float vx = w.point3.x - w.point1.x;
                const float vy = w.point3.y - w.point1.y;
                const float vz = w.point3.z - w.point1.z;

                const float uu = ux * ux + uy * uy + uz * uz;
                const float uv = ux * vx + uy * vy + uz * vz;
                const float vv = vx * vx + vy * vy + vz * vz;
                const float ru = hx * ux + hy * uy + hz * uz;
                const float rv = hx * vx + hy * vy + hz * vz;
                const float det = uu * vv - uv * uv;

                if (det > 1e-6f) {
                    const float u = (ru * vv - rv * uv) / det;
                    const float v = (rv * uu - ru * uv) / det;
                    if (u >= -0.01f && u <= 1.01f && v >= -0.01f && v <= 1.01f) {
                        result = t;
                        hit_wall_index = i;
                    }
                }
            }
        }
    }

    if (result != 2.0f && hit_wall_index >= 0) {
        calculate_bounce(particle, walls[hit_wall_index], result * delta_time, collision_dampening);
        return delta_time * (1.0f - result);
    }

    particle->position = position_after;
    particle->area = get_area_code(particle->position, influence_radius, map_size);
    return 0.0f;
}

void __device__ calculate_bounce(particle_t *particle, const wall_t wall, const float delta_time,
                                 const float collision_dampening) {
    particle->position.x += particle->velocity.x * delta_time;
    particle->position.y += particle->velocity.y * delta_time;
    particle->position.z += particle->velocity.z * delta_time;

    vector3D_t normal = wall.normal;
    const float normal_length = sqrtf(normal.x * normal.x + normal.y * normal.y + normal.z * normal.z);
    if (normal_length > 1e-6f) {
        normal.x /= normal_length;
        normal.y /= normal_length;
        normal.z /= normal_length;
        float dot_product = particle->velocity.x * normal.x +
                            particle->velocity.y * normal.y +
                            particle->velocity.z * normal.z;
        if (dot_product > 0.0f) {
            normal.x = -normal.x;
            normal.y = -normal.y;
            normal.z = -normal.z;
            dot_product = -dot_product;
        }
        const float factor = (1.0f + collision_dampening) * dot_product;
        particle->velocity.x -= factor * normal.x;
        particle->velocity.y -= factor * normal.y;
        particle->velocity.z -= factor * normal.z;

        particle->position.x += normal.x * 0.05f;
        particle->position.y += normal.y * 0.05f;
        particle->position.z += normal.z * 0.05f;
    }
}

float __device__ calculate_distance_squared(const particle_t *particle_a, const particle_t *particle_b) {
    const float dx = particle_a->position.x - particle_b->position.x;
    const float dy = particle_a->position.y - particle_b->position.y;
    const float dz = particle_a->position.z - particle_b->position.z;
    return dx * dx + dy * dy + dz * dz;
}

float __device__ calculate_influence(const particle_t *particle_a, const particle_t *particle_b,
                                     const float max_influence_radius,
                                     const float max_influence_radius_squared) {
    const float distance_squared = calculate_distance_squared(particle_a, particle_b);
    if (distance_squared < max_influence_radius_squared) {
        const float distance = sqrtf(distance_squared);
        const float diff = max_influence_radius - distance;
        return diff * diff * diff;
    }
    return 0.0f;
}

void __global__ kernel_calculate_densities(particle_t *particles, const int count, const float max_influence_radius,
                                           const gpu_area_t *areas, const vector3D_t map_size) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    int x_limit = (int)(map_size.x / max_influence_radius);
    int y_limit = (int)(map_size.y / max_influence_radius);
    int z_limit = (int)(map_size.z / max_influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        particles[i].density = 0.0f;
        const int cell_x = (int)(particles[i].position.x / max_influence_radius);
        const int cell_y = (int)(particles[i].position.y / max_influence_radius);
        const int cell_z = (int)(particles[i].position.z / max_influence_radius);

        for (int dz = -1; dz <= 1; dz++) {
            const int neighbor_z = cell_z + dz;
            if (neighbor_z < 0 || neighbor_z >= z_limit) continue;
            for (int dy = -1; dy <= 1; dy++) {
                const int neighbor_y = cell_y + dy;
                if (neighbor_y < 0 || neighbor_y >= y_limit) continue;
                for (int dx = -1; dx <= 1; dx++) {
                    const int neighbor_x = cell_x + dx;
                    if (neighbor_x < 0 || neighbor_x >= x_limit) continue;

                    const int cell_index = (neighbor_z * y_limit + neighbor_y) * x_limit + neighbor_x;
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
                                        const float delta_time, const gpu_area_t *areas, const vector3D_t map_size,
                                        const float viscosity, wall_t *walls, int wall_count,
                                        float wall_default_push, vector3D_t gravity_force, float friction_multiplier) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    int x_limit = (int)(map_size.x / max_influence_radius);
    int y_limit = (int)(map_size.y / max_influence_radius);
    int z_limit = (int)(map_size.z / max_influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    const float gravity_per_time_x = gravity_force.x * delta_time;
    const float gravity_per_time_y = gravity_force.y * delta_time;
    const float gravity_per_time_z = gravity_force.z * delta_time;

    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        const float pressure = (particles[i].density - target_density) * pressure_multiplier;
        const int cell_x = (int)(particles[i].position.x / max_influence_radius);
        const int cell_y = (int)(particles[i].position.y / max_influence_radius);
        const int cell_z = (int)(particles[i].position.z / max_influence_radius);

        float velocity_change_x = gravity_per_time_x;
        float velocity_change_y = gravity_per_time_y;
        float velocity_change_z = gravity_per_time_z;

        for (int dz = -1; dz <= 1; dz++) {
            const int neighbor_z = cell_z + dz;
            if (neighbor_z < 0 || neighbor_z >= z_limit) continue;
            for (int dy = -1; dy <= 1; dy++) {
                const int neighbor_y = cell_y + dy;
                if (neighbor_y < 0 || neighbor_y >= y_limit) continue;
                for (int dx = -1; dx <= 1; dx++) {
                    const int neighbor_x = cell_x + dx;
                    if (neighbor_x < 0 || neighbor_x >= x_limit) continue;

                    const int cell_index = (neighbor_z * y_limit + neighbor_y) * x_limit + neighbor_x;
                    int limit = areas[cell_index].count;
                    if (limit > MAX_PARTICLES_PER_AREA) {
                        limit = MAX_PARTICLES_PER_AREA;
                    }
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
                                    const float average_pressure = (pressure + pressure2) * 0.5f;
                                    if (average_pressure > 0.0f) {
                                        const float diff = max_influence_radius - distance;
                                        const float pressure_gradient = diff * diff;
                                        const float scale = (pressure_gradient * average_pressure / distance) * delta_time;
                                        velocity_change_x += (particles[i].position.x - particles[neighbor_id].position.x) * scale;
                                        velocity_change_y += (particles[i].position.y - particles[neighbor_id].position.y) * scale;
                                        velocity_change_z += (particles[i].position.z - particles[neighbor_id].position.z) * scale;
                                    }
                                }
                                const float viscosity_relative =
                                        (1.0f - distance / max_influence_radius) * viscosity * delta_time;
                                velocity_change_x += (particles[neighbor_id].velocity.x - particles[i].velocity.x) *
                                                     viscosity_relative;
                                velocity_change_y += (particles[neighbor_id].velocity.y - particles[i].velocity.y) *
                                                     viscosity_relative;
                                velocity_change_z += (particles[neighbor_id].velocity.z - particles[i].velocity.z) *
                                                     viscosity_relative;
                            }
                        }
                    }
                }
            }
        }
        const vector3D_t wall_push = calculate_wall_force(particles + i, walls, wall_count,
                                                          velocity_change_x, velocity_change_y, velocity_change_z,
                                                          max_influence_radius, wall_default_push);
        particles[i].velocity.x = (particles[i].velocity.x + velocity_change_x + wall_push.x) * friction_multiplier;
        particles[i].velocity.y = (particles[i].velocity.y + velocity_change_y + wall_push.y) * friction_multiplier;
        particles[i].velocity.z = (particles[i].velocity.z + velocity_change_z + wall_push.z) * friction_multiplier;
    }
}

vector3D_t __device__ calculate_wall_force(particle_t *particle, wall_t *walls, int wall_count,
                                           float velocity_change_x, float velocity_change_y, float velocity_change_z,
                                           float max_influence_radius, float wall_default_push) {
    vector3D_t wall_force = {0.0f, 0.0f, 0.0f};
    for (int i = 0; i < wall_count; i++) {
        const wall_t w = walls[i];
        const float pdx = particle->position.x - w.point1.x;
        const float pdy = particle->position.y - w.point1.y;
        const float pdz = particle->position.z - w.point1.z;

        const float ux = w.point2.x - w.point1.x;
        const float uy = w.point2.y - w.point1.y;
        const float uz = w.point2.z - w.point1.z;

        const float vx = w.point3.x - w.point1.x;
        const float vy = w.point3.y - w.point1.y;
        const float vz = w.point3.z - w.point1.z;

        const float uu = ux * ux + uy * uy + uz * uz;
        const float uv = ux * vx + uy * vy + uz * vz;
        const float vv = vx * vx + vy * vy + vz * vz;
        const float ru = pdx * ux + pdy * uy + pdz * uz;
        const float rv = pdx * vx + pdy * vy + pdz * vz;
        const float det = uu * vv - uv * uv;
        if (det <= 1e-6f) {
            continue;
        }
        const float u = (ru * vv - rv * uv) / det;
        const float v = (rv * uu - ru * uv) / det;
        if (u < 0.0f || u > 1.0f || v < 0.0f || v > 1.0f) {
            continue;
        }

        const float directional_distance = pdx * w.normal.x + pdy * w.normal.y + pdz * w.normal.z;
        float distance = directional_distance;
        float sign = 1.0f;
        if (distance < 0.0f) {
            distance = -distance;
            sign = -1.0f;
        }
        if (distance < max_influence_radius) {
            const float vel_along_normal = w.normal.x * velocity_change_x +
                                           w.normal.y * velocity_change_y +
                                           w.normal.z * velocity_change_z;
            if (directional_distance * vel_along_normal < 0.0f) {
                const float distance_factor = 1.0f - distance / max_influence_radius;
                const float distance_factor_squared = distance_factor * distance_factor;
                const float force_magnitude = -vel_along_normal * distance_factor_squared;
                const float total_push = force_magnitude + wall_default_push * sign;
                wall_force.x += total_push * w.normal.x;
                wall_force.y += total_push * w.normal.y;
                wall_force.z += total_push * w.normal.z;
            }
        }
    }
    return wall_force;
}

int __device__ get_area_code(const vector3D_t point, const float influence_radius, const vector3D_t size) {
    int x = (int)(point.x / influence_radius);
    int y = (int)(point.y / influence_radius);
    int z = (int)(point.z / influence_radius);

    int x_limit = (int)(size.x / influence_radius);
    int y_limit = (int)(size.y / influence_radius);
    int z_limit = (int)(size.z / influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    if (x < 0) x = 0;
    if (x >= x_limit) x = x_limit - 1;
    if (y < 0) y = 0;
    if (y >= y_limit) y = y_limit - 1;
    if (z < 0) z = 0;
    if (z >= z_limit) z = z_limit - 1;

    return (z * y_limit + y) * x_limit + x;
}

__global__ void kernel_clear_grid(gpu_area_t *areas, int total_areas) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < total_areas) {
        areas[i].count = 0;
    }
}

__global__ void kernel_area_segregation(particle_t *particles, const int count, gpu_area_t *areas,
                                        const float max_influence_radius, const vector3D_t size, const int area_count) {
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

EXPORT void update(particle_t *particles, const int count, float delta_time, const vector3D_t gravity_force,
                   const obstacles_t walls, const int collision_limit, const float max_influence_radius,
                   const float target_density, const float pressure_multiplier, const float collision_dampening,
                   const float viscosity, const vector3D_t map_size, area_t *areas, const float friction_multiplier,
                   float wall_default_push, int substeps) {
    if (count < 0 || (count > 0 && particles == nullptr) || areas == nullptr || substeps <= 0 ||
        max_influence_radius <= 0 || map_size.x <= 0 || map_size.y <= 0 || map_size.z <= 0 ||
        walls.count < 0 || (walls.count > 0 && walls.walls == nullptr)) {
        native_log(3, "CUDA", "update rejected invalid arguments: count=%d substeps=%d walls=%d",
                   count, substeps, walls.count);
        return;
    }
    int x_limit = (int)(map_size.x / max_influence_radius);
    int y_limit = (int)(map_size.y / max_influence_radius);
    int z_limit = (int)(map_size.z / max_influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    int total_areas = x_limit * y_limit * z_limit;
    if (total_areas <= 0) {
        native_log(3, "CUDA", "update rejected invalid area grid: x=%d y=%d z=%d", x_limit, y_limit, z_limit);
        return;
    }
    if (d_particles == nullptr || count != old_count || walls.count != old_wall_count || total_areas != old_total_areas) {
        if (d_particles != nullptr) {
            check_cuda(cudaFree(d_particles), "cudaFree(d_particles)");
            check_cuda(cudaFree(d_walls), "cudaFree(d_walls)");
            check_cuda(cudaFree(d_areas), "cudaFree(d_areas)");
            d_particles = nullptr;
            d_walls = nullptr;
            d_areas = nullptr;
        }
        const size_t particle_buffer_size = (size_t)(count > 0 ? count : 1) * sizeof(particle_t);
        const size_t wall_buffer_size = (size_t)(walls.count > 0 ? walls.count : 1) * sizeof(wall_t);
        if (!check_cuda(cudaMalloc((void **)&d_particles, particle_buffer_size), "cudaMalloc(d_particles)")) {
            return;
        }
        if (!check_cuda(cudaMalloc((void **)&d_walls, wall_buffer_size), "cudaMalloc(d_walls)")) {
            return;
        }
        if (!check_cuda(cudaMalloc((void **)&d_areas, (size_t)total_areas * sizeof(gpu_area_t)), "cudaMalloc(d_areas)")) {
            return;
        }
        old_wall_count = walls.count;
        old_count = count;
        old_total_areas = total_areas;
    }
    if (count > 0 &&
        !check_cuda(cudaMemcpy(d_particles, particles, (size_t)count * sizeof(particle_t), cudaMemcpyHostToDevice),
                    "cudaMemcpy(particles host-to-device)")) {
        return;
    }
    if (walls.count > 0 &&
        !check_cuda(cudaMemcpy(d_walls, walls.walls, (size_t)walls.count * sizeof(wall_t), cudaMemcpyHostToDevice),
                    "cudaMemcpy(walls host-to-device)")) {
        return;
    }
    if (count == 0) {
        return;
    }
    int threads = 256;
    int blocks = (count + threads - 1) / threads;
    int area_blocks = (total_areas + threads - 1) / threads;
    delta_time = delta_time / (float)substeps;
    for (int i = 0; i < substeps; i++) {
        kernel_clear_grid<<<area_blocks, threads>>>(d_areas, total_areas);
        if (!check_kernel_launch("kernel_clear_grid launch")) {
            return;
        }
        kernel_area_segregation<<<blocks, threads>>>(d_particles, count, d_areas, max_influence_radius, map_size,
                                                     total_areas);
        if (!check_kernel_launch("kernel_area_segregation launch")) {
            return;
        }
        kernel_calculate_densities<<<blocks, threads>>>(d_particles, count, max_influence_radius, d_areas, map_size);
        if (!check_kernel_launch("kernel_calculate_densities launch")) {
            return;
        }
        kernel_calculate_forces<<<blocks, threads>>>(d_particles, count, target_density, pressure_multiplier,
                                                     max_influence_radius, delta_time,
                                                     d_areas, map_size, viscosity, d_walls, walls.count,
                                                     wall_default_push, gravity_force, friction_multiplier);
        if (!check_kernel_launch("kernel_calculate_forces launch")) {
            return;
        }
        kernel_change_positions<<<blocks, threads>>>(d_particles, count, delta_time, d_walls, walls.count,
                                                     collision_dampening, collision_limit, max_influence_radius,
                                                     map_size);
        if (!check_kernel_launch("kernel_change_positions launch")) {
            return;
        }
    }
    if (!check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize(update)")) {
        return;
    }
    check_cuda(cudaMemcpy(particles, d_particles, (size_t)count * sizeof(particle_t), cudaMemcpyDeviceToHost),
               "cudaMemcpy(particles device-to-host)");
}

__device__ static void world_to_camera_dev(const vector3D_t p, const camera_t cam,
                                           const float cos_yaw, const float sin_yaw,
                                           const float cos_pitch, const float sin_pitch,
                                           float *out_xc, float *out_yc, float *out_zc) {
    const float dx = p.x - cam.position.x;
    const float dy = p.y - cam.position.y;
    const float dz = p.z - cam.position.z;

    const float x1 = dx * cos_yaw - dz * sin_yaw;
    const float y1 = dy;
    const float z1 = dx * sin_yaw + dz * cos_yaw;

    *out_xc = x1;
    *out_yc = y1 * cos_pitch - z1 * sin_pitch;
    *out_zc = y1 * sin_pitch + z1 * cos_pitch;
}

__global__ void kernel_clear_zbuffer(unsigned long long *zbuffer, size_t total_pixels) {
    size_t idx = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < total_pixels) {
        zbuffer[idx] = 0xFFFFFFFF00000000ULL;
    }
}

__global__ void kernel_resolve_zbuffer(const unsigned long long *zbuffer, uint32_t *frame_buffer, size_t total_pixels) {
    size_t idx = (size_t)blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < total_pixels) {
        frame_buffer[idx] = (uint32_t)(zbuffer[idx] & 0xFFFFFFFFULL);
    }
}

__global__ void drawing_particles(particle_t *particles, const int count, const int radius,
                                  const vector2D_t screen_size, unsigned long long *zbuffer,
                                  const int colour_type, const int pitch,
                                  const float visual_pressure_multiplier, const camera_t camera) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < count) {
        const float fov_rad = (camera.fov > 10.0f ? camera.fov : 60.0f) * 3.14159265f / 180.0f;
        const float focal_length = (screen_size.y * 0.5f) / tanf(fov_rad * 0.5f);
        const float center_x = screen_size.x * 0.5f;
        const float center_y = screen_size.y * 0.5f;
        const float cos_yaw = cosf(camera.yaw);
        const float sin_yaw = sinf(camera.yaw);
        const float cos_pitch = cosf(camera.pitch);
        const float sin_pitch = sinf(camera.pitch);
        const int stride = pitch / 4;
        const int screen_w = (int)screen_size.x;
        const int screen_h = (int)screen_size.y;

        float xc, yc, zc;
        world_to_camera_dev(particles[i].position, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &xc, &yc, &zc);
        if (zc <= 5.0f) {
            return;
        }

        const int x = (int)(xc * focal_length / zc + center_x);
        const int y = (int)(yc * focal_length / zc + center_y);
        int proj_radius = (int)((float)radius * focal_length / zc + 0.5f);
        if (proj_radius < 1) proj_radius = 1;
        if (proj_radius > 64) proj_radius = 64;

        if (x + proj_radius < 0 || x - proj_radius >= screen_w ||
            y + proj_radius < 0 || y - proj_radius >= screen_h) {
            return;
        }

        const float density = particles[i].density;
        float colour_calculation_helper = density / visual_pressure_multiplier;
        if (colour_calculation_helper > 1.0f) {
            colour_calculation_helper = 1.0f;
        }
        if (colour_calculation_helper < 0.0f) {
            colour_calculation_helper = 0.0f;
        }

        int base_r = 0, base_g = 0, base_b = 0;
        if (colour_type == 0) {
            base_r = (int)(colour_calculation_helper * 255.0f);
            base_g = 50;
            base_b = (int)((1.0f - colour_calculation_helper) * 255.0f);
        } else if (colour_type == 1) {
            const float lightness = 1.0f - colour_calculation_helper;
            base_r = (int)(150.0f * lightness);
            base_g = (int)(50.0f + 150.0f * lightness);
            base_b = (int)(150.0f + 105.0f * lightness);
        }

        const int r_sq = proj_radius * proj_radius;
        const float inv_r_sq = 1.0f / (float)(r_sq > 0 ? r_sq : 1);

        for (int dy = -proj_radius; dy <= proj_radius; dy++) {
            const int py = y + dy;
            if (py < 0 || py >= screen_h) continue;
            for (int dx = -proj_radius; dx <= proj_radius; dx++) {
                const int px = x + dx;
                if (px < 0 || px >= screen_w) continue;
                const int dist_sq = dx * dx + dy * dy;
                if (dist_sq <= r_sq) {
                    const float norm_r2 = (float)dist_sq * inv_r_sq;
                    const float pixel_z = zc + norm_r2 * (float)radius;
                    uint32_t depth_int = (pixel_z < 4000000.0f) ? (uint32_t)(pixel_z * 100.0f) : 0xFFFFFFFEU;
                    const float shade = 0.55f + 0.45f * (1.0f - norm_r2);
                    const int r = (int)((float)base_r * shade);
                    const int g = (int)((float)base_g * shade);
                    const int b = (int)((float)base_b * shade);
                    const uint32_t colour = (255U << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
                    const unsigned long long packed = ((unsigned long long)depth_int << 32) | (unsigned long long)colour;
                    const int index = py * stride + px;
                    if (packed < zbuffer[index]) {
                        atomicMin(&zbuffer[index], packed);
                    }
                }
            }
        }
    }
}

__device__ static void draw_line_3d_dev(vector3D_t p1, vector3D_t p2, const camera_t camera,
                                        const float cos_yaw, const float sin_yaw,
                                        const float cos_pitch, const float sin_pitch,
                                        const float focal_length, const vector2D_t screen_size,
                                        uint32_t *frame_buffer, const int pitch, const uint32_t colour) {
    float x1, y1, z1, x2, y2, z2;
    world_to_camera_dev(p1, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &x1, &y1, &z1);
    world_to_camera_dev(p2, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &x2, &y2, &z2);

    const float near_z = 5.0f;
    if (z1 <= near_z && z2 <= near_z) {
        return;
    }
    if (z1 <= near_z) {
        const float t = (near_z - z1) / (z2 - z1);
        x1 = x1 + t * (x2 - x1);
        y1 = y1 + t * (y2 - y1);
        z1 = near_z;
    } else if (z2 <= near_z) {
        const float t = (near_z - z2) / (z1 - z2);
        x2 = x2 + t * (x1 - x2);
        y2 = y2 + t * (y1 - y2);
        z2 = near_z;
    }

    const float cx = screen_size.x * 0.5f;
    const float cy = screen_size.y * 0.5f;
    int start_x = (int)(x1 * focal_length / z1 + cx);
    int start_y = (int)(y1 * focal_length / z1 + cy);
    int end_x = (int)(x2 * focal_length / z2 + cx);
    int end_y = (int)(y2 * focal_length / z2 + cy);

    const int screen_w = (int)screen_size.x;
    const int screen_h = (int)screen_size.y;
    if ((start_x < 0 && end_x < 0) || (start_x >= screen_w && end_x >= screen_w) ||
        (start_y < 0 && end_y < 0) || (start_y >= screen_h && end_y >= screen_h)) {
        return;
    }

    int dx = abs(end_x - start_x);
    int dy = -abs(end_y - start_y);
    int step_x = start_x < end_x ? 1 : -1;
    int step_y = start_y < end_y ? 1 : -1;
    int error = dx + dy;
    int max_steps = (screen_w + screen_h) * 4;
    const int stride = pitch / 4;

    while (max_steps-- > 0) {
        if (start_x >= 0 && start_x < screen_w && start_y >= 0 && start_y < screen_h) {
            frame_buffer[start_y * stride + start_x] = colour;
        }
        if (start_x == end_x && start_y == end_y) {
            break;
        }
        const int error2 = error * 2;
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

__device__ void drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer,
                              int pitch, camera_t camera) {
    const float fov_rad = (camera.fov > 10.0f ? camera.fov : 60.0f) * 3.14159265f / 180.0f;
    const float focal_length = (screen_size.y * 0.5f) / tanf(fov_rad * 0.5f);
    const float cos_yaw = cosf(camera.yaw);
    const float sin_yaw = sinf(camera.yaw);
    const float cos_pitch = cosf(camera.pitch);
    const float sin_pitch = sinf(camera.pitch);

    for (int i = 0; i < wall_count; i++) {
        const wall_t w = walls[i];
        const vector3D_t p1 = w.point1;
        const vector3D_t p2 = w.point2;
        const vector3D_t p3 = w.point3;
        const vector3D_t p4 = {
            p2.x + p3.x - p1.x,
            p2.y + p3.y - p1.y,
            p2.z + p3.z - p1.z
        };
        const uint32_t colour = (i < 6)
            ? ((255U << 24) | (120U << 16) | (140U << 8) | 170U)
            : ((255U << 24) | (255U << 16) | (255U << 8) | 255U);
        draw_line_3d_dev(p1, p2, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d_dev(p2, p4, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d_dev(p4, p3, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d_dev(p3, p1, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
    }
}

__global__ void kernel_drawing_walls(wall_t *walls, int wall_count, vector2D_t screen_size, uint32_t *frame_buffer,
                                     int pitch, camera_t camera) {
    if (threadIdx.x == 0 && blockIdx.x == 0) {
        drawing_walls(walls, wall_count, screen_size, frame_buffer, pitch, camera);
    }
}

EXPORT void drawing(particle_t *particles, const int count, obstacles_t *walls, const int radius,
                    const vector2D_t screen_size, uint32_t *frame_buffer, const int colour_type, const int pitch,
                    const float visual_pressure_multiplier, const camera_t camera) {
    if (count < 0 || (count > 0 && (particles == nullptr || d_particles == nullptr)) ||
        walls == nullptr || walls->count < 0 || (walls->count > 0 && d_walls == nullptr) ||
        frame_buffer == nullptr || radius < 0 || screen_size.x <= 0 || screen_size.y <= 0 ||
        pitch <= 0 || visual_pressure_multiplier == 0) {
        native_log(3, "CUDA", "drawing rejected invalid arguments: count=%d walls=%p frame_buffer=%p pitch=%d",
                   count, (void *)walls, (void *)frame_buffer, pitch);
        return;
    }
    const size_t total_pixels = (size_t)(pitch / 4) * (size_t)screen_size.y;
    const size_t required_buffer_size = total_pixels * sizeof(uint32_t);
    if (current_frame_buffer_pixels < total_pixels) {
        if (d_frame_buffer != nullptr) {
            check_cuda(cudaFree(d_frame_buffer), "cudaFree(d_frame_buffer)");
            d_frame_buffer = nullptr;
        }
        if (d_zbuffer != nullptr) {
            check_cuda(cudaFree(d_zbuffer), "cudaFree(d_zbuffer)");
            d_zbuffer = nullptr;
        }
        if (!check_cuda(cudaMalloc((void **)&d_frame_buffer, required_buffer_size), "cudaMalloc(d_frame_buffer)")) {
            return;
        }
        if (!check_cuda(cudaMalloc((void **)&d_zbuffer, total_pixels * sizeof(unsigned long long)), "cudaMalloc(d_zbuffer)")) {
            return;
        }
        current_frame_buffer_pixels = total_pixels;
    }

    int threads = 256;
    int pixel_blocks = (int)((total_pixels + threads - 1) / threads);
    kernel_clear_zbuffer<<<pixel_blocks, threads>>>(d_zbuffer, total_pixels);
    if (!check_kernel_launch("kernel_clear_zbuffer launch")) {
        return;
    }

    int blocks = (count + threads - 1) / threads;
    if (count > 0) {
        drawing_particles<<<blocks, threads>>>(d_particles, count, radius, screen_size,
                                               d_zbuffer, colour_type, pitch,
                                               visual_pressure_multiplier, camera);
        if (!check_kernel_launch("drawing_particles launch")) {
            return;
        }
    }

    kernel_resolve_zbuffer<<<pixel_blocks, threads>>>(d_zbuffer, d_frame_buffer, total_pixels);
    if (!check_kernel_launch("kernel_resolve_zbuffer launch")) {
        return;
    }

    kernel_drawing_walls<<<1, 1>>>(d_walls, walls->count, screen_size, d_frame_buffer, pitch, camera);
    if (!check_kernel_launch("kernel_drawing_walls launch")) {
        return;
    }
    if (!check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize(drawing)")) {
        return;
    }
    check_cuda(cudaMemcpy(frame_buffer, d_frame_buffer, required_buffer_size, cudaMemcpyDeviceToHost),
               "cudaMemcpy(frame_buffer device-to-host)");
}
