cmake_minimum_required(VERSION 3.20)
set(CMAKE_CUDA_COMPILER "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3/bin/nvcc.exe")

project(engine_c_gpu LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)

set(CMAKE_CUDA_RUNTIME_LIBRARY Static)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

set(CMAKE_CUDA_ARCHITECTURES "75;80;86;89")

add_library(engine_c_gpu SHARED physics.cu definitions.h)

target_compile_options(engine_c_gpu PRIVATE
        $<$<COMPILE_LANGUAGE:CUDA>:-Xcompiler=/MT$<$<CONFIG:Debug>:d>>
        $<$<COMPILE_LANGUAGE:CXX>:/MT$<$<CONFIG:Debug>:d>>
)

add_custom_command(TARGET engine_c_gpu POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy
        "$<TARGET_FILE:engine_c_gpu>"
        "${CMAKE_CURRENT_SOURCE_DIR}/../visuals_python/physics_engine_gpu.dll"
)