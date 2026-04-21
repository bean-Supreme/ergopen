// Generated from server/models.py — keep in sync manually.
// Import from your frontend: import type { ... } from '@/lib/ergopen/types'

export interface DeviceInfo {
  index: number;
  name: string;
  max_input_channels: number;
  default_samplerate: number;
}

export interface Config {
  device: number | null;
  ppr: number;
  sample_rate: number;
}

export interface ConfigUpdate {
  device?: number | null;
  ppr?: number;
}

export interface RecordingInfo {
  filename: string;
  duration_s: number;
  size_bytes: number;
}

export interface ReplayRequest {
  filename: string;
}

/**
 * Broadcast at ~20 fps over /stream WebSocket.
 *
 * waveform  — 512 points, normalized to [-1, 1], last ~100ms of signal
 * fft_freqs — Hz axis for fft_mag (50–600 Hz); also sent once in InitMessage
 * fft_mag   — FFT magnitudes matching fft_freqs
 * freq      — EMA-smoothed fundamental frequency, null when signal is silent
 */
export interface SignalFrame {
  ts: number;            // Unix timestamp (seconds)
  rms: number;
  freq: number | null;
  rpm: number | null;
  watts: number | null;  // uncalibrated estimate
  waveform: number[];
  fft_freqs: number[];
  fft_mag: number[];
  is_active: boolean;
  is_recording: boolean;
  rec_duration: number;
}

// ── WebSocket message envelope ─────────────────────────────────────────────────

/** Sent once when the WebSocket connects. fft_freqs is the constant Hz axis. */
export interface InitMessage {
  type: 'init';
  fft_freqs: number[];
  config: Config;
}

export interface FrameMessage {
  type: 'frame';
  data: SignalFrame;
}

export interface ErrorMessage {
  type: 'error';
  message: string;
}

export type ServerMessage = InitMessage | FrameMessage | ErrorMessage;

// ── REST helpers ───────────────────────────────────────────────────────────────

export const API_BASE = 'http://localhost:8000';
export const WS_URL   = 'ws://localhost:8000/stream';

export async function fetchDevices(): Promise<DeviceInfo[]> {
  const r = await fetch(`${API_BASE}/devices`);
  return r.json();
}

export async function fetchConfig(): Promise<Config> {
  const r = await fetch(`${API_BASE}/config`);
  return r.json();
}

export async function updateConfig(update: ConfigUpdate): Promise<Config> {
  const r = await fetch(`${API_BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  return r.json();
}

export async function startCapture(): Promise<void> {
  await fetch(`${API_BASE}/capture/start`, { method: 'POST' });
}

export async function stopCapture(): Promise<void> {
  await fetch(`${API_BASE}/capture/stop`, { method: 'POST' });
}

export async function startRecording(): Promise<void> {
  await fetch(`${API_BASE}/record/start`, { method: 'POST' });
}

export async function stopRecording(): Promise<RecordingInfo> {
  const r = await fetch(`${API_BASE}/record/stop`, { method: 'POST' });
  return r.json();
}

export async function fetchRecordings(): Promise<RecordingInfo[]> {
  const r = await fetch(`${API_BASE}/recordings`);
  return r.json();
}

export async function startReplay(filename: string): Promise<void> {
  await fetch(`${API_BASE}/replay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename } satisfies ReplayRequest),
  });
}
