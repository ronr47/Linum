plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.example.linum"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.linum"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

dependencies {
    // Add dependencies here
}
