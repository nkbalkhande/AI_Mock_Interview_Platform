"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { speechToText } from "./api";

// ---------------------------------------------------------------------------
// useTextToSpeech — browser-native SpeechSynthesis (instant, no server call)
// ---------------------------------------------------------------------------

const TTS_RATE = 1.0;
const TTS_PITCH = 1.0;

export function useTextToSpeech() {
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasError, setHasError] = useState(false);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    utteranceRef.current = null;
    setIsPlaying(false);
  }, []);

  useEffect(() => stop, [stop]);

  const speak = useCallback(
    (text: string) => {
      stop();
      setHasError(false);

      if (!window.speechSynthesis) {
        setHasError(true);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = TTS_RATE;
      utterance.pitch = TTS_PITCH;

      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(
        (v) => v.lang.startsWith("en") && v.name.toLowerCase().includes("female"),
      ) ?? voices.find((v) => v.lang.startsWith("en"));
      if (preferred) utterance.voice = preferred;

      utterance.onstart = () => setIsPlaying(true);
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => {
        setIsPlaying(false);
        setHasError(true);
      };

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [stop],
  );

  return { speak, stop, isLoading: false, isPlaying, hasError };
}

// ---------------------------------------------------------------------------
// useMicRecorder — record microphone → send to STT → get transcript
// ---------------------------------------------------------------------------

type RecorderState = "idle" | "recording" | "transcribing";

export function useMicRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const [transcript, setTranscript] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => stopStream, [stopStream]);

  const startRecording = useCallback(async () => {
    setError(null);
    setTranscript(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.start();
      setState("recording");
    } catch {
      setError("Microphone access denied. Please allow mic permission.");
      setState("idle");
    }
  }, []);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state !== "recording") return;

    const blob = await new Promise<Blob>((resolve) => {
      recorder.onstop = () => {
        resolve(new Blob(chunksRef.current, { type: recorder.mimeType }));
      };
      recorder.stop();
    });

    stopStream();
    setState("transcribing");

    try {
      const text = await speechToText(blob);
      setTranscript(text);
    } catch {
      setError("Transcription failed. Please try again.");
    } finally {
      setState("idle");
    }
  }, [stopStream]);

  const cancelRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state === "recording") {
      recorder.stop();
    }
    stopStream();
    chunksRef.current = [];
    setState("idle");
  }, [stopStream]);

  return {
    state,
    isRecording: state === "recording",
    isTranscribing: state === "transcribing",
    transcript,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
