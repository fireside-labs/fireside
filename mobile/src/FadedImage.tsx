/**
 * FadedImage — Renders an image that blends seamlessly into the dark background.
 *
 * Uses positioned overlay Views around all edges to create a feathered
 * vignette effect, dissolving the image border into the app's #060609 bg.
 * Works with any aspect ratio and supports circular or rounded shapes.
 */
import { View, Image, StyleSheet } from "react-native";
import type { ImageSourcePropType, ViewStyle, ImageStyle } from "react-native";
import { colors } from "./theme";

interface FadedImageProps {
    source: ImageSourcePropType;
    size: number;
    borderRadius?: number;
    style?: ViewStyle;
    /** Edge fade width in pixels — larger = softer blend (default 12) */
    fadeWidth?: number;
    /** Whether to use circular clip (default true) */
    circular?: boolean;
}

const BG = colors.bgPrimary; // #060609

export default function FadedImage({
    source,
    size,
    borderRadius: customBorderRadius,
    style,
    fadeWidth = 12,
    circular = true,
}: FadedImageProps) {
    const br = customBorderRadius ?? (circular ? size / 2 : 12);
    const fadeColor = BG;

    return (
        <View
            style={[
                {
                    width: size,
                    height: size,
                    borderRadius: br,
                    overflow: "hidden",
                },
                style,
            ]}
        >
            {/* The actual image */}
            <Image
                source={source}
                style={{
                    width: size,
                    height: size,
                    borderRadius: br,
                } as ImageStyle}
                resizeMode="cover"
            />

            {/* Edge fade overlays — 4 graduated bands per edge */}
            {/* Top edge */}
            <View style={[styles.fadeEdge, styles.fadeTop, {
                height: fadeWidth,
                backgroundColor: fadeColor,
                opacity: 0.7,
                borderBottomLeftRadius: br,
                borderBottomRightRadius: br,
            }]} />
            <View style={[styles.fadeEdge, styles.fadeTop, {
                height: fadeWidth * 0.6,
                backgroundColor: fadeColor,
                opacity: 0.9,
            }]} />

            {/* Bottom edge */}
            <View style={[styles.fadeEdge, styles.fadeBottom, {
                height: fadeWidth,
                backgroundColor: fadeColor,
                opacity: 0.7,
                borderTopLeftRadius: br,
                borderTopRightRadius: br,
            }]} />
            <View style={[styles.fadeEdge, styles.fadeBottom, {
                height: fadeWidth * 0.6,
                backgroundColor: fadeColor,
                opacity: 0.9,
            }]} />

            {/* Left edge */}
            <View style={[styles.fadeEdge, styles.fadeLeft, {
                width: fadeWidth,
                backgroundColor: fadeColor,
                opacity: 0.7,
                borderTopRightRadius: br,
                borderBottomRightRadius: br,
            }]} />
            <View style={[styles.fadeEdge, styles.fadeLeft, {
                width: fadeWidth * 0.6,
                backgroundColor: fadeColor,
                opacity: 0.9,
            }]} />

            {/* Right edge */}
            <View style={[styles.fadeEdge, styles.fadeRight, {
                width: fadeWidth,
                backgroundColor: fadeColor,
                opacity: 0.7,
                borderTopLeftRadius: br,
                borderBottomLeftRadius: br,
            }]} />
            <View style={[styles.fadeEdge, styles.fadeRight, {
                width: fadeWidth * 0.6,
                backgroundColor: fadeColor,
                opacity: 0.9,
            }]} />

            {/* Corner strengthen — thin ring at the very edge */}
            <View style={[styles.ring, {
                borderRadius: br,
                borderWidth: 2,
                borderColor: fadeColor,
            }]} />
        </View>
    );
}

const styles = StyleSheet.create({
    fadeEdge: {
        position: "absolute",
        zIndex: 2,
    },
    fadeTop: {
        top: 0,
        left: 0,
        right: 0,
    },
    fadeBottom: {
        bottom: 0,
        left: 0,
        right: 0,
    },
    fadeLeft: {
        top: 0,
        bottom: 0,
        left: 0,
    },
    fadeRight: {
        top: 0,
        bottom: 0,
        right: 0,
    },
    ring: {
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 3,
    },
});
