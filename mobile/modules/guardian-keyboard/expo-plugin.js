/**
 * Expo Config Plugin — Guardian Keyboard (iOS + Android)
 *
 * This plugin is registered in app.json and runs during `eas build`.
 * It adds both the iOS keyboard extension and Android IME service
 * so that "Guardian Keyboard" appears in system keyboard settings.
 *
 * What it does:
 * iOS:
 *   1. Copies KeyboardViewController.swift into the Xcode project
 *   2. Copies Info.plist as the extension's config
 *   3. Adds the keyboard extension target with correct bundle ID
 *   4. Enables App Group for shared settings (companion species, PC host)
 *
 * Android:
 *   1. Adds <service> declaration for FiresideKeyboardService to AndroidManifest
 *   2. Copies method.xml to res/xml/
 *   3. Copies FiresideKeyboardService.java to the source tree
 *
 * Usage: Add to app.json plugins:
 *   ["./modules/guardian-keyboard/expo-plugin"]
 */
const {
    withXcodeProject,
    withInfoPlist,
    withAndroidManifest,
    withDangerousMod,
} = require("@expo/config-plugins");
const path = require("path");
const fs = require("fs");

const EXTENSION_NAME = "GuardianKeyboard";
const EXTENSION_BUNDLE_ID = "com.valhalla.companion.guardian-keyboard";

function withGuardianKeyboard(config) {
    // ── iOS: Add keyboard extension target ──
    config = withInfoPlist(config, (config) => {
        // App Group entitlements handled in app.json ios.entitlements
        return config;
    });

    config = withXcodeProject(config, async (config) => {
        const xcodeProject = config.modResults;
        const extensionDir = path.join(__dirname, "ios");

        const swiftPath = path.join(extensionDir, "KeyboardViewController.swift");
        const plistPath = path.join(extensionDir, "Info.plist");

        if (!fs.existsSync(swiftPath) || !fs.existsSync(plistPath)) {
            console.warn(
                "[GuardianKeyboard] Swift/plist files not found. " +
                "Extension will not be added."
            );
            return config;
        }

        // Add PBXGroup for the extension
        const extGroup = xcodeProject.addPbxGroup(
            ["KeyboardViewController.swift", "Info.plist"],
            EXTENSION_NAME,
            EXTENSION_NAME
        );

        // Add extension target
        const target = xcodeProject.addTarget(
            EXTENSION_NAME,
            "app_extension",
            EXTENSION_NAME,
            EXTENSION_BUNDLE_ID
        );

        // Add build phase for Swift source
        xcodeProject.addBuildPhase(
            ["KeyboardViewController.swift"],
            "PBXSourcesBuildPhase",
            "Sources",
            target.uuid
        );

        // Copy files to Xcode project directory
        const iosProjectDir = path.join(
            config.modRequest.platformProjectRoot,
            EXTENSION_NAME
        );

        if (!fs.existsSync(iosProjectDir)) {
            fs.mkdirSync(iosProjectDir, { recursive: true });
        }

        fs.copyFileSync(swiftPath, path.join(iosProjectDir, "KeyboardViewController.swift"));
        fs.copyFileSync(plistPath, path.join(iosProjectDir, "Info.plist"));

        console.log(`[GuardianKeyboard] Added ${EXTENSION_NAME} target to Xcode project`);
        return config;
    });

    // ── Android: Add IME service to manifest ──
    config = withAndroidManifest(config, (config) => {
        const manifest = config.modResults;
        const app = manifest.manifest.application[0];

        // Check if service already exists
        if (!app.service) app.service = [];
        const existing = app.service.find(
            (s) => s.$?.["android:name"] === ".FiresideKeyboardService"
        );
        if (existing) return config;

        // Add the IME service declaration
        app.service.push({
            $: {
                "android:name": ".FiresideKeyboardService",
                "android:label": "Guardian Keyboard",
                "android:permission": "android.permission.BIND_INPUT_METHOD",
                "android:exported": "true",
            },
            "intent-filter": [
                {
                    action: [
                        { $: { "android:name": "android.view.InputMethod" } },
                    ],
                },
            ],
            "meta-data": [
                {
                    $: {
                        "android:name": "android.view.im",
                        "android:resource": "@xml/method",
                    },
                },
            ],
        });

        console.log("[GuardianKeyboard] Added FiresideKeyboardService to AndroidManifest.xml");
        return config;
    });

    // ── Android: Copy Java source + method.xml ──
    config = withDangerousMod(config, [
        "android",
        async (config) => {
            const androidDir = path.join(__dirname, "android");
            const projectRoot = config.modRequest.platformProjectRoot;

            // Copy method.xml to res/xml/
            const xmlDir = path.join(projectRoot, "app", "src", "main", "res", "xml");
            if (!fs.existsSync(xmlDir)) {
                fs.mkdirSync(xmlDir, { recursive: true });
            }
            const methodSrc = path.join(androidDir, "method.xml");
            if (fs.existsSync(methodSrc)) {
                fs.copyFileSync(methodSrc, path.join(xmlDir, "method.xml"));
                console.log("[GuardianKeyboard] Copied method.xml to res/xml/");
            }

            // Copy Java source to the right package directory
            const javaDir = path.join(
                projectRoot, "app", "src", "main", "java",
                "com", "valhalla", "companion"
            );
            if (!fs.existsSync(javaDir)) {
                fs.mkdirSync(javaDir, { recursive: true });
            }
            const javaSrc = path.join(androidDir, "FiresideKeyboardService.java");
            if (fs.existsSync(javaSrc)) {
                fs.copyFileSync(javaSrc, path.join(javaDir, "FiresideKeyboardService.java"));
                console.log("[GuardianKeyboard] Copied FiresideKeyboardService.java");
            }

            return config;
        },
    ]);

    return config;
}

module.exports = withGuardianKeyboard;
