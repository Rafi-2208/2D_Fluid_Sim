cmake_minimum_required(VERSION 4.3)
project(engine_c C)

set(CMAKE_C_STANDARD 11)

add_library(engine_c SHARED physics.c
        definitions.h
)
target_compile_options(engine_c PRIVATE -fopenmp)
target_link_options(engine_c PRIVATE -fopenmp)
find_package(OpenMP REQUIRED)
target_link_libraries(engine_c PRIVATE OpenMP::OpenMP_C)


add_custom_command(TARGET engine_c POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
        "$<TARGET_FILE:engine_c>"
        "${CMAKE_CURRENT_SOURCE_DIR}/../visuals_python/physics_engine_cpu_multi.dll"
)
