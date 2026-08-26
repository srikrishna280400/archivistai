# Capacitor
-keep class com.getcapacitor.** { *; }
-keep interface com.getcapacitor.** { *; }

# Google Play Services / Ads
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**

# JavaScript interfaces
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Material3
-keepclassmembers class * {
    @androidx.annotation.DoNotStrip <methods>;
}

# Keep R.java
-keepclassmembers class **.R$* {
    public static <fields>;
}