// ASTRA-GUARD Demo Mode Data
// All data in this file is synthetic and intended for demonstration only.
// Force demo mode to remain local-only so production always uses live backend data.
export const DEMO_MODE = import.meta.env.DEV && import.meta.env.VITE_DEMO_MODE === "true";

// Demo mission configuration
export const demoMission = {
  mission_id: "DEMO-001",
  mission_name: "Payload Transfer",
  experiment_id: "EXP001_TARDIGRADE",
  status: "ACTIVE",
  active: true,
  confidence: null,
  deviation: false,
  current_step: 3,
  total_steps: 8,
  completed_steps: 2,
};

// Demo protocol steps
export const demoProtocol = {
  experiment_id: "EXP001_TARDIGRADE",
  experiment_name: "Payload Transfer",
  steps: [
    {
      step_id: "STEP-01",
      order: 1,
      activity: "Identify the payload",
      expected_object: "Payload",
    },
    {
      step_id: "STEP-02",
      order: 2,
      activity: "Check the transfer zone",
      expected_object: "Transfer Zone",
    },
    {
      step_id: "STEP-03",
      order: 3,
      activity: "Move the payload to Zone A",
      expected_object: "Payload",
    },
    {
      step_id: "STEP-04",
      order: 4,
      activity: "Verify payload placement",
      expected_object: "Payload",
    },
    {
      step_id: "STEP-05",
      order: 5,
      activity: "Prepare the receiving zone",
      expected_object: "Receiving Zone",
    },
    {
      step_id: "STEP-06",
      order: 6,
      activity: "Transfer the payload",
      expected_object: "Payload",
    },
    {
      step_id: "STEP-07",
      order: 7,
      activity: "Confirm the final position",
      expected_object: "Payload",
    },
    {
      step_id: "STEP-08",
      order: 8,
      activity: "Complete the experiment",
      expected_object: "Payload",
    },
  ],
};

// Demo mission progress
export const demoProgress = {
  completed_steps: 2,
  total_steps: 8,
  progress_percent: 25,
  current_step: 3,
  completed: false,
};

// Demo mission status
export const demoStatus = {
  status: "CORRECT",
  active: true,
  confidence: null,
  deviation: false,
  step_id: "STEP-03",
  expected_activity: "Move the payload to Zone A",
  expected_object: "Payload",
  detected_object: null,
  guidance: "Demo mode: follow the displayed protocol steps.",
};

// Demo mission summary
export const demoSummary = {
  deviations: 0,
  total_events: 3,
  completed_steps: 2,
  total_steps: 8,
};

// Demo events
export const demoEvents = [
  {
    timestamp: "2026-09-28T14:30:00",
    status: "CORRECT",
    step_id: "STEP-01",
    activity: "Identify the payload",
    detected_object: null,
    confidence: null,
    guidance: "Demo event: payload identification step completed.",
  },
  {
    timestamp: "2026-09-28T14:31:00",
    status: "CORRECT",
    step_id: "STEP-02",
    activity: "Check the transfer zone",
    detected_object: null,
    confidence: null,
    guidance: "Demo event: transfer zone check completed.",
  },
  {
    timestamp: "2026-09-28T14:32:00",
    status: "CORRECT",
    step_id: "STEP-03",
    activity: "Move the payload to Zone A",
    detected_object: null,
    confidence: null,
    guidance: "Demo event: payload transfer is ready for demonstration.",
  },
];

// Demo system health
// Real hardware and AI metrics are intentionally unavailable.
export const demoHealth = {
  status: "DEMO",
  camera: {
    available: false,
    status: "UNAVAILABLE",
  },
  perception: {
    available: false,
    status: "UNAVAILABLE",
  },
  yolo: {
    available: false,
    status: "UNAVAILABLE",
  },
  mediapipe: {
    available: false,
    status: "UNAVAILABLE",
  },
  pipeline: {
    status: "DEMO",
    frames_processed: null,
  },
  detections: null,
  performance: {
    fps: null,
    latency_ms: null,
  },
};

// Demo voice status
export const demoVoiceStatus = {
  available: false,
  enabled: false,
  status: "UNAVAILABLE",
};