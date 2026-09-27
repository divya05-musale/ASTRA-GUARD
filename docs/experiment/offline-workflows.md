# Offline Experiment Workflows

## Payload Transfer (EXP006)

The YAML protocol defines eight ordered steps: open rack, confirm open, place the red box in Zone A, place the yellow box in Zone B, verify both placements, close rack, confirm closed, and mark complete.

The detector combines the existing local YOLO output with OpenCV HSV color segmentation. For each detected colored contour it records the measured mask-pixel purity and bounding rectangle. It accepts placement only when the complete rectangle is inside the configured normalized zone and observed continuously for at least one second. A detected box in the wrong region or not fully inside its assigned region is a deviation. Low-purity color masks and incomplete hold durations are uncertain.

Zone rectangles and HSV ranges are in `experiment.yaml`. They are initial configuration values and require calibration against the actual camera view, box colors, and lighting. The rack state currently uses configurable ArUco dictionary `DICT_4X4_50`, default ID 13 for open and 14 for closed. Those IDs are setup defaults, not user-supplied hardware specifications; replace them with the physical rack's tags before operation. Missing fiducials are uncertain, not inferred from generic object detection.

## Plant Monitoring and Watering (EXP007)

The YAML protocol defines nine ordered steps: start session, identify tray, identify plant, identify watering tool, detect a simulated watering interaction, manually confirm watering, capture local image evidence, save the local observation report, and manually confirm completion.

The detector recognizes only configured local ArUco markers 10 (tray), 11 (plant), and 12 (watering tool). A simulated watering event requires markers 11 and 12 within the configured normalized distance and a MediaPipe-tracked hand near the tool marker. Operator confirmation remains distinguishable from marker/vision decisions in session JSON, JSONL history, and CSV exports.

This workflow does not measure water volume or claim that water was physically dispensed. Evidence capture saves the current local camera JPEG; report saving writes a local JSON snapshot. No cloud service is used.

## Local Operation

Select either experiment in the existing dashboard's Experiments view. Start a webcam session there, or choose a local video file and select **Process local video**. Video frames are processed in source order by the existing detector/tracker/mission pipeline; no frame-dropping queue is added. Processing may take longer than real time. The saved session reports source type, frame progress, step decisions, manual confirmations, and local evidence references.

The YOLO weights and MediaPipe hand-landmarker task file must already exist locally. The installed OpenCV build must expose `cv2.aruco` for these experiment strategies. Missing local files or marker capability are reported as errors; runtime model download is disabled. Disconnected-network operation has not yet been tested end to end.