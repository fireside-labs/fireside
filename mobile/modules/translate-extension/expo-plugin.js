/**
 * Expo Config Plugin — Translate with Ember (iOS Action Extension)
 *
 * This plugin is registered in app.json and runs during `eas build`.
 * It adds the iOS Action Extension target to the Xcode project so that
 * "Translate with Ember" appears in the iOS share/action sheet.
 *
 * What it does:
 * 1. Copies ios/ActionViewController.swift into the Xcode project
 * 2. Copies ios/Info.plist as the extension's Info.plist
 * 3. Adds the extension target with the correct bundle ID
 * 4. Sets the app group entitlement for shared data
 *
 * Usage: Add to app.json plugins:
 *   ["./modules/translate-extension/expo-plugin"]
 *
 * NOTE: This requires EAS Build (not expo start --web).
 * The extension only works on physical iOS devices or simulators
 * after running `eas build` or `npx expo run:ios`.
 */
const { withXcodeProject, withInfoPlist } = require("@expo/config-plugins");
const path = require("path");
const fs = require("fs");

const EXTENSION_NAME = "TranslateWithEmber";
const EXTENSION_BUNDLE_ID = "com.valhalla.companion.translate-action";

function withTranslateExtension(config) {
    // Step 1: Add App Group to main app's entitlements
    config = withInfoPlist(config, (config) => {
        // The entitlements are handled in app.json ios.entitlements
        return config;
    });

    // Step 2: Add extension target to Xcode project
    config = withXcodeProject(config, async (config) => {
        const xcodeProject = config.modResults;
        const extensionDir = path.join(__dirname, "ios");

        // Check if extension files exist
        const swiftPath = path.join(extensionDir, "ActionViewController.swift");
        const plistPath = path.join(extensionDir, "Info.plist");

        if (!fs.existsSync(swiftPath) || !fs.existsSync(plistPath)) {
            console.warn(
                "[TranslateExtension] Swift/plist files not found. " +
                "Extension will not be added. Run from the module directory."
            );
            return config;
        }

        // Add a new PBXGroup for the extension
        const extGroup = xcodeProject.addPbxGroup(
            ["ActionViewController.swift", "Info.plist"],
            EXTENSION_NAME,
            EXTENSION_NAME
        );

        // Add the extension target
        const target = xcodeProject.addTarget(
            EXTENSION_NAME,
            "app_extension",
            EXTENSION_NAME,
            EXTENSION_BUNDLE_ID
        );

        // Add build phase for Swift source
        xcodeProject.addBuildPhase(
            ["ActionViewController.swift"],
            "PBXSourcesBuildPhase",
            "Sources",
            target.uuid
        );

        // Copy files to the extension directory in the iOS project
        const iosProjectDir = path.join(
            config.modRequest.platformProjectRoot,
            EXTENSION_NAME
        );

        if (!fs.existsSync(iosProjectDir)) {
            fs.mkdirSync(iosProjectDir, { recursive: true });
        }

        fs.copyFileSync(swiftPath, path.join(iosProjectDir, "ActionViewController.swift"));
        fs.copyFileSync(plistPath, path.join(iosProjectDir, "Info.plist"));

        console.log(`[TranslateExtension] Added ${EXTENSION_NAME} target to Xcode project`);

        return config;
    });

    return config;
}

module.exports = withTranslateExtension;
