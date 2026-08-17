plugins { id("com.android.application") }
android {
    namespace = "net.kingfisher"
    compileSdk = 35
    defaultConfig {
        applicationId = "net.kingfisher"
        minSdk = 29                 // getCurrentThermalStatus() is API 29+
        targetSdk = 35
        versionCode = 1
        ndk { abiFilters += "arm64-v8a" }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging { jniLibs { useLegacyPackaging = false } }   // 16 KB alignment path
}
