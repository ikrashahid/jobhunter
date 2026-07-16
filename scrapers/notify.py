"""
notify.py — plays a short sound when a run finishes.

You're on macOS, so this uses `afplay` with one of the built-in system
sounds (no extra installs needed). If afplay isn't available (e.g. this
gets run on Linux/Windows later), it falls back to the terminal bell
character, which still makes a sound in most terminals.
"""

import platform
import subprocess


# Any .aiff file in /System/Library/Sounds works here. "Glass" is short
# and pleasant — swap the name if you'd prefer a different built-in sound
# (other options: Ping, Pop, Hero, Submarine).
MAC_SOUND_PATH = "/System/Library/Sounds/Glass.aiff"


def play_done_sound() -> None:
    """
    Plays a short notification sound to signal a run has finished.
    Safe to call even if sound playback isn't available — it just
    prints a fallback message instead of crashing the script.
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        try:
            subprocess.run(
                ["afplay", MAC_SOUND_PATH],
                check=True,
                timeout=5,
            )
            return
        except Exception as e:
            print(f"  (sound playback failed, continuing anyway: {e})")

    # Fallback for non-Mac systems, or if afplay failed for some reason —
    # \a is the terminal "bell" character, most terminals will beep on it.
    print("\a", end="", flush=True)


if __name__ == "__main__":
    # Lets you test the sound on its own: `python notify.py`
    print("Playing done sound...")
    play_done_sound()
    print("Done.")
