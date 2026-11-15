#include "definitions.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

static engine_log_callback_t log_callback = NULL;
static float *g_depth_buffer = NULL;
static size_t g_depth_buffer_elements = 0;

EXPORT void set_log_callback(engine_log_callback_t callback) {
    log_callback = callback;
}

static void native_log(int level, const char *format, ...) {
    if (log_callback == NULL) {
        return;
    }
    char message[512];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof(message), format, args);
    va_end(args);
    log_callback(level, "CPU", message);
}

EXPORT void update(particle_t *particles, const int count, float delta_time, const vector3D_t gravity_force,
                   const obstacles_t walls, const int collision_limit, const float max_influence_radius,
                   const float target_density, const float pressure_multiplier, const float collision_dampening,
                   const float viscosity, const vector3D_t map_size, area_t *areas, const float friction_multiplier,
                   float wall_default_push, int substeps) {
    if (particles == NULL || count < 0 || areas == NULL || substeps <= 0 ||
        max_influence_radius <= 0 || map_size.x <= 0 || map_size.y <= 0 || map_size.z <= 0 ||
        walls.count < 0 || (walls.count > 0 && walls.walls == NULL)) {
        native_log(3, "update rejected invalid arguments: particles=%p count=%d areas=%p substeps=%d walls=%d",
                   (void *)particles, count, (void *)areas, substeps, walls.count);
        return;
    }
    delta_time = delta_time / (float)substeps;
    for (int i = 0; i < substeps; i++) {
        area_segregation(particles, count, areas, max_influence_radius, map_size);
        calculate_densities(particles, count, max_influence_radius, areas, map_size);
        calculate_forces(particles, count, target_density, pressure_multiplier, max_influence_radius,
                         delta_time, areas, map_size, viscosity, walls, wall_default_push,
                         gravity_force, friction_multiplier);
        change_positions(particles, count, delta_time, &walls, collision_dampening, collision_limit,
                         max_influence_radius, map_size);
    }
}

void change_positions(particle_t *particles, const int count, const float delta_time, const obstacles_t *walls,
                      const float collision_dampening, const int collision_limit, const float influence_radius,
                      const vector3D_t map_size) {
    for (int i = 0; i < count; i++) {
        float time_left = delta_time;
        int counter = 0;
        while (time_left > 0.0f) {
            counter++;
            time_left = calculate_movement_and_wall_collision(particles + i, walls, time_left, collision_dampening,
                                                              influence_radius, map_size);
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

float calculate_movement_and_wall_collision(particle_t *particle, const obstacles_t *walls, const float delta_time,
                                            const float collision_dampening, const float influence_radius,
                                            const vector3D_t map_size) {
    const vector3D_t position_before = particle->position;
    const vector3D_t d = {
        .x = particle->velocity.x * delta_time,
        .y = particle->velocity.y * delta_time,
        .z = particle->velocity.z * delta_time
    };
    const vector3D_t position_after = {
        .x = position_before.x + d.x,
        .y = position_before.y + d.y,
        .z = position_before.z + d.z
    };

    float result = 2.0f;
    int hit_wall_index = -1;

    for (int i = 0; i < walls->count; i++) {
        const wall_t w = walls->walls[i];
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
        calculate_bounce(particle, walls->walls[hit_wall_index], result * delta_time, collision_dampening);
        return delta_time * (1.0f - result);
    }

    particle->position = position_after;
    particle->area = get_area_code(particle->position, influence_radius, map_size);
    return 0.0f;
}

void calculate_bounce(particle_t *particle, const wall_t wall, const float delta_time,
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

float calculate_distance_squared(const particle_t *particle_a, const particle_t *particle_b) {
    const float dx = particle_a->position.x - particle_b->position.x;
    const float dy = particle_a->position.y - particle_b->position.y;
    const float dz = particle_a->position.z - particle_b->position.z;
    return dx * dx + dy * dy + dz * dz;
}

float calculate_influence(const particle_t *particle_a, const particle_t *particle_b, const float max_influence_radius,
                          const float max_influence_radius_squared) {
    const float distance_squared = calculate_distance_squared(particle_a, particle_b);
    if (distance_squared < max_influence_radius_squared) {
        const float distance = sqrtf(distance_squared);
        const float diff = max_influence_radius - distance;
        return diff * diff * diff;
    }
    return 0.0f;
}

void calculate_densities(particle_t *particles, const int count, const float max_influence_radius,
                         const area_t *areas, const vector3D_t map_size) {
    const float max_influence_radius_squared = max_influence_radius * max_influence_radius;
    int x_limit = (int)(map_size.x / max_influence_radius);
    int y_limit = (int)(map_size.y / max_influence_radius);
    int z_limit = (int)(map_size.z / max_influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    for (int i = 0; i < count; i++) {
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
                    const area_t current_area = areas[cell_index];
                    for (int j = 0; j < current_area.count; j++) {
                        const particle_t *neighbor = current_area.particles[j];
                        particles[i].density += calculate_influence(particles + i, neighbor,
                                                                    max_influence_radius,
                                                                    max_influence_radius_squared);
                    }
                }
            }
        }
    }
}

void calculate_forces(particle_t *particles, const int count, const float target_density,
                      const float pressure_multiplier, const float max_influence_radius,
                      const float delta_time, const area_t *areas, const vector3D_t map_size,
                      const float viscosity, obstacles_t obstacles, float wall_default_push,
                      vector3D_t gravity_force, float friction_multiplier) {
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

    for (int i = 0; i < count; i++) {
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
                    const area_t current_area = areas[cell_index];
                    for (int j = 0; j < current_area.count; j++) {
                        const particle_t *neighbor = current_area.particles[j];
                        if (&particles[i] != neighbor) {
                            const float distance_squared = calculate_distance_squared(particles + i, neighbor);
                            if (distance_squared < max_influence_radius_squared) {
                                const float distance = sqrtf(distance_squared);
                                if (0.001f < distance_squared) {
                                    const float pressure2 = (neighbor->density - target_density) * pressure_multiplier;
                                    const float average_pressure = (pressure + pressure2) * 0.5f;
                                    if (average_pressure > 0.0f) {
                                        const float diff = max_influence_radius - distance;
                                        const float pressure_gradient = diff * diff;
                                        const float scale = (pressure_gradient * average_pressure / distance) * delta_time;
                                        velocity_change_x += (particles[i].position.x - neighbor->position.x) * scale;
                                        velocity_change_y += (particles[i].position.y - neighbor->position.y) * scale;
                                        velocity_change_z += (particles[i].position.z - neighbor->position.z) * scale;
                                    }
                                }
                                const float viscosity_relative =
                                        (1.0f - distance / max_influence_radius) * viscosity * delta_time;
                                velocity_change_x += (neighbor->velocity.x - particles[i].velocity.x) * viscosity_relative;
                                velocity_change_y += (neighbor->velocity.y - particles[i].velocity.y) * viscosity_relative;
                                velocity_change_z += (neighbor->velocity.z - particles[i].velocity.z) * viscosity_relative;
                            }
                        }
                    }
                }
            }
        }

        const vector3D_t wall_push = calculate_wall_force(particles + i, obstacles,
                                                          velocity_change_x, velocity_change_y, velocity_change_z,
                                                          max_influence_radius, wall_default_push);
        particles[i].velocity.x = (particles[i].velocity.x + velocity_change_x + wall_push.x) * friction_multiplier;
        particles[i].velocity.y = (particles[i].velocity.y + velocity_change_y + wall_push.y) * friction_multiplier;
        particles[i].velocity.z = (particles[i].velocity.z + velocity_change_z + wall_push.z) * friction_multiplier;
    }
}

vector3D_t calculate_wall_force(particle_t *particle, const obstacles_t walls,
                                float velocity_change_x, float velocity_change_y, float velocity_change_z,
                                float max_influence_radius, float wall_default_push) {
    vector3D_t wall_force = {.x = 0.0f, .y = 0.0f, .z = 0.0f};
    for (int i = 0; i < walls.count; i++) {
        const wall_t w = walls.walls[i];
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

int get_area_code(const vector3D_t point, const float influence_radius, const vector3D_t size) {
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

void area_segregation(particle_t *particles, const int count, area_t *areas, const float max_influence_radius,
                      const vector3D_t size) {
    int x_limit = (int)(size.x / max_influence_radius);
    int y_limit = (int)(size.y / max_influence_radius);
    int z_limit = (int)(size.z / max_influence_radius);
    if (x_limit < 1) x_limit = 1;
    if (y_limit < 1) y_limit = 1;
    if (z_limit < 1) z_limit = 1;

    const int area_count = x_limit * y_limit * z_limit;
    for (int i = 0; i < area_count; i++) {
        areas[i].count = 0;
    }
    for (int i = 0; i < count; i++) {
        const int area_code = get_area_code(particles[i].position, max_influence_radius, size);
        if (area_code >= 0 && area_code < area_count && areas[area_code].count < MAX_PARTICLES_PER_AREA) {
            areas[area_code].particles[areas[area_code].count] = particles + i;
            areas[area_code].count++;
        }
    }
}

static void world_to_camera(const vector3D_t p, const camera_t cam, const float cos_yaw, const float sin_yaw,
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

EXPORT void drawing(particle_t *particles, const int count, obstacles_t *walls, const int radius,
                    const vector2D_t screen_size, uint32_t *frame_buffer, const int colour_type, const int pitch,
                    const float visual_pressure_multiplier, const camera_t camera) {
    if (particles == NULL || count < 0 || walls == NULL || walls->count < 0 ||
        (walls->count > 0 && walls->walls == NULL) || frame_buffer == NULL || radius < 0 ||
        screen_size.x <= 0 || screen_size.y <= 0 || pitch <= 0 || visual_pressure_multiplier == 0) {
        native_log(3, "drawing rejected invalid arguments: particles=%p count=%d walls=%p frame_buffer=%p pitch=%d",
                   (void *)particles, count, (void *)walls, (void *)frame_buffer, pitch);
        return;
    }

    const size_t total_pixels = (size_t)(pitch / 4) * (size_t)screen_size.y;
    if (g_depth_buffer_elements < total_pixels) {
        free(g_depth_buffer);
        g_depth_buffer = (float *)malloc(total_pixels * sizeof(float));
        if (g_depth_buffer == NULL) {
            g_depth_buffer_elements = 0;
            native_log(3, "drawing failed to allocate depth buffer");
            return;
        }
        g_depth_buffer_elements = total_pixels;
    }
    for (size_t i = 0; i < total_pixels; i++) {
        g_depth_buffer[i] = 1e30f;
    }

    drawing_particles(particles, count, radius, screen_size, frame_buffer, g_depth_buffer, colour_type, pitch,
                      visual_pressure_multiplier, camera);
    drawing_walls(walls, screen_size, frame_buffer, pitch, camera);
}

void drawing_particles(particle_t *particles, const int count, const int radius, const vector2D_t screen_size,
                       uint32_t *frame_buffer, float *depth_buffer, const int colour_type, const int pitch,
                       const float visual_pressure_multiplier, const camera_t camera) {
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

    for (int i = 0; i < count; i++) {
        float xc, yc, zc;
        world_to_camera(particles[i].position, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &xc, &yc, &zc);
        if (zc <= 5.0f) {
            continue;
        }

        const int x = (int)(xc * focal_length / zc + center_x);
        const int y = (int)(yc * focal_length / zc + center_y);
        int proj_radius = (int)((float)radius * focal_length / zc + 0.5f);
        if (proj_radius < 1) proj_radius = 1;
        if (proj_radius > 64) proj_radius = 64;

        if (x + proj_radius < 0 || x - proj_radius >= screen_w ||
            y + proj_radius < 0 || y - proj_radius >= screen_h) {
            continue;
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
                    const int index = py * stride + px;
                    if (pixel_z < depth_buffer[index]) {
                        depth_buffer[index] = pixel_z;
                        const float shade = 0.55f + 0.45f * (1.0f - norm_r2);
                        const int r = (int)((float)base_r * shade);
                        const int g = (int)((float)base_g * shade);
                        const int b = (int)((float)base_b * shade);
                        frame_buffer[index] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
                    }
                }
            }
        }
    }
}

static void draw_line_3d(vector3D_t p1, vector3D_t p2, const camera_t camera,
                         const float cos_yaw, const float sin_yaw, const float cos_pitch, const float sin_pitch,
                         const float focal_length, const vector2D_t screen_size,
                         uint32_t *frame_buffer, const int pitch, const uint32_t colour) {
    float x1, y1, z1, x2, y2, z2;
    world_to_camera(p1, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &x1, &y1, &z1);
    world_to_camera(p2, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, &x2, &y2, &z2);

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

void drawing_walls(obstacles_t *walls, vector2D_t screen_size, uint32_t *frame_buffer, int pitch, camera_t camera) {
    const float fov_rad = (camera.fov > 10.0f ? camera.fov : 60.0f) * 3.14159265f / 180.0f;
    const float focal_length = (screen_size.y * 0.5f) / tanf(fov_rad * 0.5f);
    const float cos_yaw = cosf(camera.yaw);
    const float sin_yaw = sinf(camera.yaw);
    const float cos_pitch = cosf(camera.pitch);
    const float sin_pitch = sinf(camera.pitch);

    for (int i = 0; i < walls->count; i++) {
        const wall_t w = walls->walls[i];
        const vector3D_t p1 = w.point1;
        const vector3D_t p2 = w.point2;
        const vector3D_t p3 = w.point3;
        const vector3D_t p4 = {
            .x = p2.x + p3.x - p1.x,
            .y = p2.y + p3.y - p1.y,
            .z = p2.z + p3.z - p1.z
        };
        const uint32_t colour = (i < 6) ? ((120 << 16) | (140 << 8) | 170) : ((255 << 16) | (255 << 8) | 255);
        draw_line_3d(p1, p2, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d(p2, p4, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d(p4, p3, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
        draw_line_3d(p3, p1, camera, cos_yaw, sin_yaw, cos_pitch, sin_pitch, focal_length, screen_size, frame_buffer, pitch, colour);
    }
}
