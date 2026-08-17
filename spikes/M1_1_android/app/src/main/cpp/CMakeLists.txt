cmake_minimum_required(VERSION 3.22)
project(kfjni C)
add_library(hyperonc SHARED IMPORTED)
set_target_properties(hyperonc PROPERTIES IMPORTED_LOCATION
    ${CMAKE_CURRENT_SOURCE_DIR}/../jniLibs/${ANDROID_ABI}/libhyperonc.so)
add_library(kfjni SHARED kfjni.c)
target_include_directories(kfjni PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(kfjni hyperonc log)
