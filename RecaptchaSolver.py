import os
import urllib.request
import random
import pydub
import speech_recognition
import time
from typing import Optional
from nodriver.core.tab import Tab


class RecaptchaSolver:
    """A class to solve reCAPTCHA challenges using audio recognition."""

    # Constants
    TEMP_DIR = os.getenv("TEMP") if os.name == "nt" else "/tmp"
    TIMEOUT_STANDARD = 7
    TIMEOUT_SHORT = 1
    TIMEOUT_DETECTION = 0.05

    def __init__(self, tab: Tab) -> None:
        """Initialize the solver with a nodriver Tab.

        Args:
            tab: A nodriver Tab instance for browser interaction
        """
        self.tab = tab

    async def solveCaptcha(self) -> None:
        """Attempt to solve the reCAPTCHA challenge.

        Raises:
            Exception: If captcha solving fails or bot is detected
        """

        # Find main reCAPTCHA iframe
        iframe_inner = await self.tab.select("[title='reCAPTCHA']", self.TIMEOUT_STANDARD)

        # Click the checkbox
        checkbox = await iframe_inner.select(".rc-anchor-content", self.TIMEOUT_STANDARD)
        await checkbox.click()

        # Check if solved by just clicking
        if await self.is_solved():
            return

        # Handle audio challenge
        iframe = (await self.tab.xpath("//iframe[contains(@title, 'recaptcha')]"))[0]

        audio_btn = await iframe.select("#recaptcha-audio-button", self.TIMEOUT_STANDARD)
        await audio_btn.click()
        time.sleep(0.3)

        if await self.is_detected():
            raise Exception("Captcha detected bot behavior")

        # Download and process audio
        audio_source = await (iframe.select("#audio-source", self.TIMEOUT_STANDARD))
        src = audio_source.attrs["src"]

        try:
            text_response = self._process_audio_challenge(src)

            response_input = await iframe.query_selector("#audio-response")
            await response_input.send_keys(text_response.lower())

            verify_btn = await iframe.query_selector("#recaptcha-verify-button")
            await verify_btn.click()
            time.sleep(0.4)

            if not await self.is_solved():
                raise Exception("Failed to solve the captcha")

        except Exception as e:
            raise Exception(f"Audio challenge failed: {str(e)}")

    def _process_audio_challenge(self, audio_url: str) -> str:
        """Process the audio challenge and return the recognized text.

        Args:
            audio_url: URL of the audio file to process

        Returns:
            str: Recognized text from the audio file
        """
        mp3_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.mp3")
        wav_path = os.path.join(self.TEMP_DIR, f"{random.randrange(1,1000)}.wav")

        try:
            urllib.request.urlretrieve(audio_url, mp3_path)
            sound = pydub.AudioSegment.from_mp3(mp3_path)
            sound.export(wav_path, format="wav")

            recognizer = speech_recognition.Recognizer()
            with speech_recognition.AudioFile(wav_path) as source:
                audio = recognizer.record(source)

            return recognizer.recognize_google(audio)

        finally:
            for path in (mp3_path, wav_path):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    async def is_solved(self) -> bool:
        """Check if the captcha has been solved successfully."""
        try:
            checkmark = (await self.tab.select_all(".recaptcha-checkbox-checkmark", self.TIMEOUT_SHORT, include_frames=True))[0]
            return "style" in checkmark.attrs
        except Exception as e:
            print(e)
            return False

    async def is_detected(self) -> bool:
        """Check if the bot has been detected."""
        try:
            return await self.tab.find("Try again later", timeout=self.TIMEOUT_DETECTION) is not None
        except Exception:
            return False

    async def get_token(self) -> Optional[str]:
        """Get the reCAPTCHA token if available."""
        try:
            token_el = (await self.tab.select_all("#recaptcha-token", include_frames=True))[0]
            return token_el.attrs["value"]
        except Exception:
            return None
