import CoreImage
import CoreVideo
import Foundation
import Vision

public enum BackgroundRemovalError: Error {
    case noMaskProduced
    case cannotCreateMaskImage
}

/// Fully on-device person cutout using Apple Vision.
/// This replaces the server-backed automatic person/background removal path.
public final class BackgroundRemovalEngine: @unchecked Sendable {
    private let context: CIContext

    public init(context: CIContext = CIContext()) {
        self.context = context
    }

    public func personMask(
        for pixelBuffer: CVPixelBuffer,
        quality: VNGeneratePersonSegmentationRequest.QualityLevel = .accurate
    ) throws -> CIImage {
        let request = VNGeneratePersonSegmentationRequest()
        request.qualityLevel = quality
        request.outputPixelFormat = kCVPixelFormatType_OneComponent8

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, options: [:])
        try handler.perform([request])

        guard let result = request.results?.first else {
            throw BackgroundRemovalError.noMaskProduced
        }

        return CIImage(cvPixelBuffer: result.pixelBuffer)
    }

    public func compositeForeground(
        source: CIImage,
        mask: CIImage,
        background: CIImage? = nil,
        featherRadius: Double = 1.5
    ) -> CIImage {
        let sx = source.extent.width / mask.extent.width
        let sy = source.extent.height / mask.extent.height
        var alignedMask = mask.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
            .cropped(to: source.extent)

        if featherRadius > 0 {
            alignedMask = alignedMask
                .applyingFilter("CIGaussianBlur", parameters: [kCIInputRadiusKey: featherRadius])
                .cropped(to: source.extent)
        }

        let bg = background?.cropped(to: source.extent)
            ?? CIImage(color: .clear).cropped(to: source.extent)

        return source.applyingFilter(
            "CIBlendWithMask",
            parameters: [
                kCIInputBackgroundImageKey: bg,
                kCIInputMaskImageKey: alignedMask
            ]
        )
    }

    public func removeBackground(
        from pixelBuffer: CVPixelBuffer,
        quality: VNGeneratePersonSegmentationRequest.QualityLevel = .accurate,
        featherRadius: Double = 1.5
    ) throws -> CIImage {
        let source = CIImage(cvPixelBuffer: pixelBuffer)
        let mask = try personMask(for: pixelBuffer, quality: quality)
        return compositeForeground(source: source, mask: mask, featherRadius: featherRadius)
    }
}
