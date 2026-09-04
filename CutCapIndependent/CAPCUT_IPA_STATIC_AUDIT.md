# CapCut 19.3.0 IPA static feature audit

Source inspected: uploaded `CutCap.ipa` / `Payload/CapCut.app`

This document records only what is actually present in the submitted IPA. It distinguishes bundled rendering/algorithm code from resource catalogs and ML models that are referenced but not present in the package.

## Package size / structure

- App bundle: ~730 MB
- Files: 7,195
- Top-level resource bundles: 134
- App extensions: 5
- Frameworks: 11
- Main editor/localization exposes a very large feature surface; presence of a UI string/icon is not treated as proof that the creative material/model itself is bundled.

## Major editor modules actually bundled

- `LVEditor.bundle`
- `LVEditorCommon.bundle`
- `LVEditorEffect.bundle`
- `LVEditorText.bundle`
- `LVEditorAudio.bundle`
- `LVPhotoEditor.bundle`
- `LVFigureEditor.bundle`
- `LVMaskEditor.bundle`
- `LVExport.bundle`
- `LVCamera.bundle`
- `Retouch.bundle`
- `LVEditorAIGC.bundle`
- `LVEditorAIClipper.bundle`
- `LVEditorAIMusic.bundle`
- `LVAISound.bundle`
- `LVAIDigitalPortrait.bundle`
- `LVGenAI.bundle`
- `LVGenAIBizUI.bundle`
- `LVMaterialGenerate.bundle`
- template, publishing, search, subscription and material modules

## Color / grading engine: strongly bundled locally

`LVEditorCommon.bundle/AdjustResource.bundle` contains ~1,407 files / ~12 MB of shader/effect resources.

Observed bundled processing families include:

- Brightness / exposure-style brightness generations
- Contrast
- Saturation
- Temperature
- Tint / tone
- Highlights
- Shadows
- Fade
- Vignette
- Sharpen
- Black & white
- Curves
- HSL
- Primary color wheel
- Log color wheel
- Detail level
- Dehaze
- Backlight processing
- Color correction
- Color migration / color-match plumbing
- Smart color adjustment
- Splendor / enhancement path
- Blend / blit stages
- LUT support

A real `.cube` LUT is bundled:

- `AdjustResource.bundle/color_adjustment/AmazingFilter_lut/Alexa LogC to Rec709.cube`

The app also contains Metal/GLES shader implementations for the above paths, not only UI controls.

## Built-in filter resources actually in the IPA

The full CapCut filter catalog is **not** stored offline in the IPA.

Direct built-in filter/effect resources observed:

- `LVEditorCommon.bundle/FilterResource.bundle/innerFilter/darkmask`
- `LVEditorCommon.bundle/FilterResource.bundle/innerFilter/yuantu`
- a second `yuantu` copy in `LVEditor.bundle/FilterResource.bundle`
- scene-recognition filter resources under `RetouchFilter.bundle/Scene_Recognition/` for indoor, outdoor, prepose portrait, night and salt scenes
- `LVEditor.bundle/FilterResource.bundle/AI_trans_linear` contains an actual bundled transition/effect graph with shader/Lua resources

Conclusion: the renderer and adjustment infrastructure is local, but the large searchable named filter/effect catalog is material-driven and normally downloaded.

## Chroma key: bundled locally

`LVEditorCommon.bundle/ChromaResource.bundle` contains:

- `ChromaMatting`
- `ChromaMatting_v2`
- Metal and GLES shaders

This is a genuine local chroma-key pipeline resource.

## Cutout / matting: pipeline bundled, important models missing

`LVEditorCommon.bundle/MattingResource.bundle` contains algorithm graphs and blend/refinement resources for:

- `ai_matting`
- `ai_matting_gru`
- `ai_matting_video_object`
- `ai_matting_video_object_preview`
- `camera_matting`
- `custom_matting`
- `interactive`
- `saliency_matting`
- `tag_matting`
- stroke blend
- stroke blend + dilate/erode

Manual editing support is also local:

- mask pen
- eraser
- handwrite brush
- cutout brush
- cutout eraser
- recognition brush shaders
- shape masks: rectangle, circle, heart, star, triangle

However, the algorithm graphs reference model packages which are **not files in the submitted IPA**, including:

- `mobilevos_packed`
- `video_saliency_seg_bce`
- `video_saliency_seg_bce_preview`
- `tt_matting_video_gru`
- `tt_interactive_matting`
- `saliency_script_for_cc`
- `ge_seg_lv_script_v1.0.model`

Therefore automatic AI cutout is not fully self-contained in this IPA. The local graph/renderer exists, but required inference resources are acquired separately.

Localization also explicitly states that some photo cutout/background-removal flows upload media to CapCut/Hypic servers.

## Tracking / camera tracking: algorithm code bundled, models external

`LockObjectResource.bundle` contains tracking graphs and Gaussian blur/frame effect resources.

The main executable contains real tracking implementation strings/symbols such as:

- `object_tracking`
- `optical_flow_track`
- `Bingo_ObjectTracking_createHandle`
- `TEBachSmartObjectTrackingAlgorithm`
- `AlgorithmSingleObjectTracking`
- camera tracking controllers
- text/object tracking UI/controller code

Referenced tracking/detection models absent from the IPA include:

- `bingo_objectTracking_v1.0.dat`
- `tt_body_detection_lockon`
- `tt_skeletonlockon`
- `tt_fsnew_base_jianying`
- `lock_obj_det.model`
- `lock_key_point.model`

So the tracking implementation is genuinely compiled into the app, but its full model set is not embedded.

## Stabilization / motion blur / optical flow / slow motion / denoise

The main executable contains real compiled implementations/controllers for:

- video stabilization (`VideoStableController`, `VideoStableManager`, `TwoPassStabilizer`, `TESmartStabilizationUnit`)
- motion blur (`MotionBlurController`, `MotionBlurManager`, `MotionBlurAlgorithm`, `MotionBlurService`)
- optical flow (`DISOpticalFlow`, optical-flow tracking paths)
- smooth slow motion (`SmoothSlowMotionOperation`, manager/controller/task paths)
- video noise reduction (`NoiseReductionAlgorithm`, `NoiseReductionService`)
- deflicker (`DeflickerAlgorithm`, `TELensDeflickerAlgorithm`)
- velocity editing

Additionally, `deflicker.bundle/deflicker.metallib` is bundled.

These are not merely icons; substantial processing code is in the binary.

## Smart crop / auto reframe

`SmartCropResource.bundle` and `SmartCropResourceNew.bundle` contain full algorithm graphs using face detection, object detection, saliency inference and video reframe stages.

Referenced models include:

- `tt_fsnew_base_jianying`
- `tt_body_detection_lockon`
- `nodehub_image_saliency`
- `video_reframe`

Those model resources are not stored as files in this IPA.

## Retouch / beauty

Actual local shader resources are present for legacy beauty and reshape paths, including:

- face smoothing/beauty shader chain
- face mask texture
- face reshape/deformation configuration
- face / nose / eye composer parameters
- local Gaussian blur
- local sharpen
- HSL
- curves
- structure
- HDR shader path
- local masks and local adjustments

The English retouch localization exposes a much larger feature family, including skin smoothing, concealing, teeth whitening, eye brightening, face shape, jaw, chin, nose, lips, body reshape, skin tone, makeup, hair and more.

Not all of those advanced effects are proven to have their complete models/materials bundled; several localization strings explicitly describe server/cloud processing.

## Image enhancement / night enhancement

`RetouchCompile.bundle/image_enhance/config.json` and `night_enhance/config.json` explicitly specify:

- algorithm: `lens_lqir2_xingtu`
- API path: `/media/api/pic/afr/`

This is direct evidence that those enhancement flows use a remote processing API rather than only the local shaders in the IPA.

## Super resolution

Three bundled `.model` files are real ZIP-packaged CoreML packages:

- `bmf-mods/srnn_v1.0_size0.model`
- `bmf-mods/srnn2_v1.0_size0.model`
- `bmf-mods/srhqv2fp16_v1.0_size0.model`

They contain `.mlpackage` / `.mlmodel` and CoreML weight files.

The main executable also contains super-resolution code and references to those paths. It additionally contains cloud/AIGC super-resolution endpoints and UI, so CapCut has multiple SR paths; not every “Super resolution” entry is necessarily routed through these local models.

## Audio / voice / captions

The editor exposes and contains code/UI plumbing for:

- audio extraction
- fade in/out
- volume
- beats / match cut
- voiceover recording
- voice effects / voice changer
- reduce noise
- vocal isolation
- vocal polish / enhance voice
- text-to-speech
- voice clone / custom voices
- auto captions
- auto lyrics
- bilingual captions
- filler-word removal
- transcript/text-based editing
- AI music

A local `audio_metrics_v1.4.model` is bundled.

Voice clone clearly performs upload/generation and consumes credits according to its own localization, so it is not self-contained locally.

The main executable contains speech-recognition service/controller code, but the submitted IPA does not contain an obvious full speech-recognition acoustic/language model package. Auto-caption functionality therefore cannot be assumed to be fully offline from this IPA alone.

## Text

The app includes UI/code/resources for:

- normal text
- fonts
- bold/italic/underline
- alignment
- bubbles
- text effects
- text animations
- text templates
- caption templates
- text drawing/eraser
- text tracking
- text-to-audio / TTS
- text-to-image
- text-to-video
- AI text/template tooling

`LVEditorText.bundle/ai_text.zip` is bundled, but most online template/material catalogs are not.

## Timeline / core editor surface proven by editor assets and executable

The editor exposes controls for at least:

- split / trim / delete / copy / replace
- overlay / PIP
- opacity / blend
- mirror / rotate / crop
- freeze
- reverse
- speed
- velocity effects
- keyframes
- graph interpolation between keyframes
- masks
- customized cutout
- chroma key
- stabilization
- motion blur
- noise reduction
- remove flicker
- optical flow
- filters
- adjustments
- transitions
- effects
- stickers
- animation in/out/combo
- auto reframe
- camera tracking
- text tracking
- canvas/background/aspect ratios
- retouch
- relight
- AI remove / brush / replace / movement / background / effects
- export settings and quality tools

## AI / cloud-heavy feature families exposed by the app

The package exposes UI/business logic for many services whose actual generation is server-backed or depends on remotely supplied models/materials, including examples such as:

- AI background
- AI effects
- AI transitions
- AI remove / inpainting
- AI replace
- AI movement
- AI avatars / digital humans
- AI dubbing / overdub
- voice clone
- AI music
- AI clipper / shorts
- text-to-image
- text-to-video
- AI characters
- AI model / fashion model workflows
- AI packaging / smart edit
- some enhance / relight / image-quality paths

The IPA's localization repeatedly states that media is uploaded to CapCut servers for many of these operations.

## Full creative catalog conclusion

Do **not** equate the number of visible feature names with the number of offline assets.

What the IPA heavily bundles:

1. editor UI/business logic
2. timeline/project logic
3. rendering engine plumbing
4. a large local color-adjustment shader suite
5. selected built-in filter/effect resources
6. chroma-key resources
7. mask/brush/refinement resources
8. tracking/stabilization/motion-blur/noise-reduction/optical-flow implementation code
9. selected beauty/retouch shaders
10. selected CoreML super-resolution packages

What it does **not** bundle as a complete offline library:

1. the full named CapCut filters catalog
2. the full transitions/effects/stickers catalog
3. the full template library
4. most music/sound catalog content
5. multiple ML model packages referenced by matting/tracking/reframe graphs
6. cloud AI generation models
7. CapCut server-side enhancement/generation services

This distinction should drive the rebrand/parity work: preserve and map every local capability that is genuinely in the package, but do not assume a network material/model will survive after CapCut infrastructure is removed.
