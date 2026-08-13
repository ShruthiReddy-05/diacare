"""
Test all Sarvam AI bulbul:v3 TTS voices.
Generates a WAV file for each speaker so you can compare and pick one.
"""

import base64
import os
import time
from sarvamai import SarvamAI

API_KEY = os.environ.get("SARVAM_API_KEY", "your_api_key_here")

SPEAKERS = [
    "shubh", "aditya", "ritu", "priya", "neha", "rahul", "pooja", "rohan",
    "simran", "kavya", "amit", "dev", "ishita", "shreya", "ratan", "varun",
    "manan", "sumit", "roopa", "kabir", "aayan", "ashutosh", "advait",
    "anand", "tanya", "tarun", "sunny", "mani", "gokul", "vijay", "shruti",
    "suhani", "mohit", "kavitha", "rehan", "soham", "rupali"
]

TEXT = "வணக்கம், இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?"
LANG = "ta-IN"

client = SarvamAI(api_subscription_key=API_KEY)
output_dir = "sarvam_test_voices"
os.makedirs(output_dir, exist_ok=True)

for speaker in SPEAKERS:
    print(f"Generating: {speaker}...", end=" ")
    try:
        response = client.text_to_speech.convert(
            model="bulbul:v3",
            text=TEXT,
            target_language_code=LANG,
            speaker=speaker,
            pace=1.0,
        )

        if hasattr(response, 'audios') and response.audios:
            audio_b64 = response.audios[0]
        elif isinstance(response, dict) and 'audios' in response:
            audio_b64 = response['audios'][0]
        else:
            print(f"⚠️  Unexpected response: {response}")
            continue

        wav_bytes = base64.b64decode(audio_b64)
        filename = os.path.join(output_dir, f"sarvam_{speaker}.wav")
        with open(filename, "wb") as f:
            f.write(wav_bytes)

        print(f"✅ ({len(wav_bytes)} bytes)")
    except Exception as e:
        print(f"❌ {e}")

    time.sleep(0.5)  # small delay to avoid rate limits

print(f"\nDone! Files saved in '{output_dir}/'")
