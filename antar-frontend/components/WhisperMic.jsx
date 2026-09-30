"use client";

import React, { useEffect, useRef, useState } from "react";
import { Mic, MicOff, X, Trash2 } from "lucide-react";

/**
 * WhisperMicButton:
 * Renders the mic button with sleek, titanium silver/grey glassmorphic glow.
 */
export function WhisperMicButton({ recording, onClick, kn, title }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title || (recording ? (kn ? "ಆಲಿಸುವಿಕೆಯನ್ನು ನಿಲ್ಲಿಸಿ (Stop Whisper AI)" : "Stop Whisper AI") : (kn ? "ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಲು ಒತ್ತಿ (Voice Input)" : "Click to speak with Whisper AI"))}
      className={`whisper-mic-btn ${recording ? "active" : ""}`}
      style={{
        background: recording ? undefined : "transparent",
        color: recording ? "#FFFFFF" : "rgba(255, 255, 255, 0.65)"
      }}
    >
      {recording && <span className="ring1" />}
      {recording && <span className="ring2" />}
      {recording ? <MicOff size={18} /> : <Mic size={18} />}
    </button>
  );
}

/**
 * WhisperWaveform:
 * Renders the real-time, intelligent Whisper AI voice visualizer pill.
 * Features true frequency spectrum reactivity AND speech-event reactivity:
 * 100% FLAT when silent, jumping only when the user is speaking.
 * Plus full dictation controls (Clear & Done).
 */
export function WhisperWaveform({ kn, onStop, onClear }) {
  const [barHeights, setBarHeights] = useState(() => Array(16).fill(3));
  const [isSpeaking, setIsSpeaking] = useState(false);
  const animRef = useRef(null);
  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const speakingRef = useRef(false);

  useEffect(() => {
    let active = true;
    const numBars = 16;
    const currentHeights = Array(numBars).fill(3);
    let useAudioSpectrum = false;

    // Listen to SpeechRecognition speech events (for robust reactivity even when getUserMedia is busy)
    const onWhisperSpeech = (e) => {
      const activeState = !!e.detail?.active;
      speakingRef.current = activeState;
      if (!useAudioSpectrum) {
        setIsSpeaking(activeState);
      }
    };
    window.addEventListener("whisper-speech", onWhisperSpeech);

    async function initAudioSpectrum() {
      try {
        if (!navigator?.mediaDevices?.getUserMedia) return;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        if (!active) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;

        const ctx = new AudioContextClass();
        audioContextRef.current = ctx;
        if (ctx.state === "suspended") {
          await ctx.resume().catch(() => {});
        }
        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 64; // 32 frequency bins
        analyser.smoothingTimeConstant = 0.65;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const silenceThreshold = 10;
        useAudioSpectrum = true;

        const updateLoop = () => {
          if (!active) return;
          analyser.getByteFrequencyData(dataArray);

          // Calculate average energy in voice spectrum
          let sum = 0;
          for (let i = 1; i < 24 && i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / Math.min(23, dataArray.length - 1);

          if (avg < silenceThreshold && !speakingRef.current) {
            setIsSpeaking(false);
            for (let i = 0; i < numBars; i++) {
              currentHeights[i] += (3 - currentHeights[i]) * 0.28;
            }
          } else {
            setIsSpeaking(true);
            for (let i = 0; i < numBars; i++) {
              const binIdx = 1 + Math.floor((i / numBars) * Math.min(20, dataArray.length - 1));
              const val = dataArray[binIdx] || 0;
              const targetHeight = Math.max(3, Math.min(22, 3 + (val / 255) * 22 * 1.35));
              currentHeights[i] += (targetHeight - currentHeights[i]) * 0.35;
            }
          }

          setBarHeights([...currentHeights]);
          animRef.current = requestAnimationFrame(updateLoop);
        };

        updateLoop();
      } catch (e) {
        // Fallback: use pure JS speech-event simulation ONLY when speakingRef.current is true!
        useAudioSpectrum = false;
        const fallbackLoop = () => {
          if (!active) return;
          if (!speakingRef.current) {
            setIsSpeaking(false);
            for (let i = 0; i < numBars; i++) {
              currentHeights[i] += (3 - currentHeights[i]) * 0.3;
            }
          } else {
            setIsSpeaking(true);
            const now = Date.now() * 0.008;
            for (let i = 0; i < numBars; i++) {
              const targetHeight = Math.max(4, Math.sin(now + i * 0.5) * 8 + Math.cos(now * 1.5 + i) * 6 + 10);
              currentHeights[i] += (targetHeight - currentHeights[i]) * 0.3;
            }
          }
          setBarHeights([...currentHeights]);
          animRef.current = requestAnimationFrame(fallbackLoop);
        };
        fallbackLoop();
      }
    }

    initAudioSpectrum();

    return () => {
      active = false;
      window.removeEventListener("whisper-speech", onWhisperSpeech);
      if (animRef.current) cancelAnimationFrame(animRef.current);
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
      if (audioContextRef.current && audioContextRef.current.state !== "closed") {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  return (
    <div className="whisper-waveform-pill">
      <div className="whisper-bars">
        {Array.from({ length: 16 }).map((_, i) => (
          <div
            key={i}
            className="whisper-bar"
            style={{
              height: `${Math.round(barHeights[i] || 3)}px`,
              opacity: isSpeaking ? 1 : 0.45
            }}
          />
        ))}
      </div>

    </div>
  );
}
