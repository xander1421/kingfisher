# Wrapper toolchain: the cmake crate cannot pass -DANDROID_ABI, and the NDK's
# own toolchain file reads it as a cache variable, so set it here and delegate.
set(ANDROID_ABI arm64-v8a CACHE STRING "")
set(ANDROID_PLATFORM android-28 CACHE STRING "")
set(ANDROID_STL c++_static CACHE STRING "")
include("/Users/victorianikolenko/Library/Android/sdk/ndk/28.2.13676358/build/cmake/android.toolchain.cmake")
