import { apiClient } from "@/lib/api-client";

/** POST /voice/tts — convert text to WAV audio. */
export async function textToSpeech(text: string): Promise<Blob> {
  const { data } = await apiClient.post("/voice/tts", { text }, {
    responseType: "blob",
  });
  return data as Blob;
}

/** POST /voice/stt — transcribe audio blob to text. */
export async function speechToText(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  const { data } = await apiClient.post<{ transcript: string }>(
    "/voice/stt",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data.transcript;
}
