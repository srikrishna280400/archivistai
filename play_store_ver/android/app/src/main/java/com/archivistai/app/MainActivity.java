package com.archivistai.app;

import android.os.Bundle;
import android.view.Window;
import android.view.WindowInsetsController;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Bridge;
import com.getcapacitor.Plugin;
import com.getcapacitor.JSObject;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.PluginCall;

import java.util.ArrayList;
import java.util.List;

public class MainActivity extends BridgeActivity {

    /**
     * Custom Capacitor plugin for Google Play Billing.
     *
     * This is a plug-and-play placeholder. When you're ready to ship
     * subscriptions, install the @capacitor-community/google-play-billing
     * plugin (or Capacitor In-App Purchase) and uncomment the wiring
     * below. The web layer calls window.googlePlayBilling.consumePurchase()
     * and window.googlePlayBilling.queryPurchases() — those will be
     * available once the native plugin is installed.
     */
    public static class PlayBillingPlugin extends Plugin {
        @PluginMethod
        public void queryPurchases(PluginCall call) {
            JSObject result = new JSObject();
            result.put("purchases", new ArrayList<>());
            result.put("premium", false);
            result.put("message", "Google Play Billing not yet integrated");
            call.resolve(result);
        }

        @PluginMethod
        public void consumePurchase(PluginCall call) {
            String purchaseToken = call.getString("purchaseToken");
            JSObject result = new JSObject();
            result.put("consumed", false);
            result.put("message", "Google Play Billing not yet integrated");
            call.resolve(result);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Splash screen support
        getSplashScreen().setOnExitAnimationListener(splashScreenInfo -> {
            // Smooth exit animation handled by the theme
        });

        // Register custom plugins
        registerActivityPlugins();

        super.onCreate(savedInstanceState);
    }

    private void registerActivityPlugins() {
        List<Class<? extends Plugin>> plugins = new ArrayList<>();
        // Add your native plugins here:
        // plugins.add(PlayBillingPlugin.class);
        // plugins.add(com.capacitorcommunity.facebooklogin.FacebookLogin.class);
        // plugins.add(com.capacitorcommunity.admob.AdMob.class);
        // plugins.add(com.getcapacitorcommunity.googleplayservices.GooglePlayServices.class);
    }

    /**
     * Handle the share target intent — redirect to the web layer with the URL.
     * The Capacitor share target plugin handles this automatically, but
     * this hook ensures the intent data is preserved across restarts.
     */
    @Override
    protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
    }
}