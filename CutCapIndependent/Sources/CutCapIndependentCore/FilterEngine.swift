import CoreImage
import Foundation

public struct ColorAdjustments: Sendable, Hashable {
    public var exposure: Double = 0
    public var brightness: Double = 0
    public var contrast: Double = 1
    public var saturation: Double = 1
    public var vibrance: Double = 0
    public var temperature: Double = 6500
    public var tint: Double = 0
    public var hueRadians: Double = 0
    public var highlights: Double = 1
    public var shadows: Double = 0
    public var gamma: Double = 1
    public var sharpen: Double = 0
    public var vignette: Double = 0

    public init() {}
}

public struct FilterPreset: Sendable, Hashable, Identifiable {
    public let id: String
    public let name: String
    public let adjustments: ColorAdjustments

    public init(id: String, name: String, adjustments: ColorAdjustments) {
        self.id = id
        self.name = name
        self.adjustments = adjustments
    }
}

/// Independent Core Image filter pipeline. It intentionally reproduces editing
/// capabilities (intensity, color controls, curves/LUT-ready architecture) rather
/// than copying any proprietary third-party filter asset.
public enum FilterEngine {
    public static func apply(
        _ adjustments: ColorAdjustments,
        to source: CIImage,
        intensity: Double = 1
    ) -> CIImage {
        let t = max(0, min(1, intensity))
        var image = source

        if adjustments.exposure != 0 {
            image = image.applyingFilter("CIExposureAdjust", parameters: [
                kCIInputEVKey: adjustments.exposure * t
            ])
        }

        image = image.applyingFilter("CIColorControls", parameters: [
            kCIInputBrightnessKey: adjustments.brightness * t,
            kCIInputContrastKey: 1 + (adjustments.contrast - 1) * t,
            kCIInputSaturationKey: 1 + (adjustments.saturation - 1) * t
        ])

        if adjustments.vibrance != 0 {
            image = image.applyingFilter("CIVibrance", parameters: [
                "inputAmount": adjustments.vibrance * t
            ])
        }

        if adjustments.temperature != 6500 || adjustments.tint != 0 {
            let targetTemp = 6500 + (adjustments.temperature - 6500) * t
            let targetTint = adjustments.tint * t
            image = image.applyingFilter("CITemperatureAndTint", parameters: [
                "inputNeutral": CIVector(x: 6500, y: 0),
                "inputTargetNeutral": CIVector(x: targetTemp, y: targetTint)
            ])
        }

        if adjustments.hueRadians != 0 {
            image = image.applyingFilter("CIHueAdjust", parameters: [
                kCIInputAngleKey: adjustments.hueRadians * t
            ])
        }

        if adjustments.highlights != 1 || adjustments.shadows != 0 {
            image = image.applyingFilter("CIHighlightShadowAdjust", parameters: [
                "inputHighlightAmount": 1 + (adjustments.highlights - 1) * t,
                "inputShadowAmount": adjustments.shadows * t
            ])
        }

        if adjustments.gamma != 1 {
            image = image.applyingFilter("CIGammaAdjust", parameters: [
                "inputPower": 1 + (adjustments.gamma - 1) * t
            ])
        }

        if adjustments.sharpen > 0 {
            image = image.applyingFilter("CISharpenLuminance", parameters: [
                kCIInputSharpnessKey: adjustments.sharpen * t
            ])
        }

        if adjustments.vignette > 0 {
            image = image.applyingFilter("CIVignette", parameters: [
                kCIInputIntensityKey: adjustments.vignette * t,
                kCIInputRadiusKey: min(source.extent.width, source.extent.height) * 0.45
            ])
        }

        return image.cropped(to: source.extent)
    }

    public static let presets: [FilterPreset] = [
        preset("clean", "Clean", exposure: 0.08, contrast: 1.04, saturation: 1.03),
        preset("vivid", "Vivid", contrast: 1.12, saturation: 1.22, vibrance: 0.22),
        preset("warm-film", "Warm Film", exposure: -0.05, contrast: 1.10, saturation: 0.92, temperature: 7200, vignette: 0.35),
        preset("cool-film", "Cool Film", contrast: 1.08, saturation: 0.90, temperature: 5600, tint: -4, vignette: 0.25),
        preset("night", "Night", exposure: -0.20, contrast: 1.20, saturation: 0.84, temperature: 5900, sharpen: 0.20),
        preset("sunset", "Sunset", exposure: 0.05, contrast: 1.10, saturation: 1.16, temperature: 7900, tint: 5),
        preset("portrait", "Portrait", exposure: 0.10, contrast: 0.98, saturation: 1.02, vibrance: 0.12, temperature: 6800),
        preset("food", "Food", exposure: 0.10, contrast: 1.08, saturation: 1.20, temperature: 7100, sharpen: 0.18),
        preset("retro", "Retro", exposure: 0.02, contrast: 0.90, saturation: 0.78, temperature: 7600, vignette: 0.45),
        preset("bleach", "Bleach", exposure: 0.12, contrast: 1.26, saturation: 0.55, gamma: 0.92),
        preset("soft", "Soft", exposure: 0.12, contrast: 0.88, saturation: 0.94, highlights: 0.90, shadows: 0.12),
        preset("moody", "Moody", exposure: -0.15, contrast: 1.16, saturation: 0.72, temperature: 6100, vignette: 0.30),
        preset("teal", "Teal", contrast: 1.12, saturation: 1.04, temperature: 5700, tint: -10),
        preset("gold", "Gold", exposure: 0.04, contrast: 1.11, saturation: 1.08, temperature: 8200, tint: 6),
        preset("mono", "Mono", contrast: 1.12, saturation: 0, sharpen: 0.12),
        preset("high-key", "High Key", exposure: 0.30, contrast: 0.92, saturation: 0.90, highlights: 0.86, shadows: 0.18)
    ]

    private static func preset(
        _ id: String,
        _ name: String,
        exposure: Double = 0,
        brightness: Double = 0,
        contrast: Double = 1,
        saturation: Double = 1,
        vibrance: Double = 0,
        temperature: Double = 6500,
        tint: Double = 0,
        highlights: Double = 1,
        shadows: Double = 0,
        gamma: Double = 1,
        sharpen: Double = 0,
        vignette: Double = 0
    ) -> FilterPreset {
        var a = ColorAdjustments()
        a.exposure = exposure
        a.brightness = brightness
        a.contrast = contrast
        a.saturation = saturation
        a.vibrance = vibrance
        a.temperature = temperature
        a.tint = tint
        a.highlights = highlights
        a.shadows = shadows
        a.gamma = gamma
        a.sharpen = sharpen
        a.vignette = vignette
        return FilterPreset(id: id, name: name, adjustments: a)
    }
}
