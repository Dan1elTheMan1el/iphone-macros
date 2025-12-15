from utils import wordHunter, anagrammer, wordBiter
from pynput import keyboard

# Keyboard listener for start/stop functionality
def on_press(key):
    if key == keyboard.Key.alt_r:
        print("\nRight Alt pressed - stopping macro...")
        anagrammer.stop_flag = True
        wordHunter.stop_flag = True
        wordBiter.stop_flag = True
    elif key == keyboard.Key.alt_l:
        wordBiter.scan_ocr = True
        wordHunter.scan_ocr = True

# Start keyboard listener in background thread
listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Welcome to iPhone macros!\n1. Anagrams\n2. Word Hunt\n3. Word Bites")
choice = int(input("Select a macro to run: "))
if choice == 1:
    letters = input("Enter letters: ").strip().upper()
    anagrammer.solveAnagrams(letters)
elif choice == 2:
    size = int(input("Enter size: ").strip())
    print("Press Left Alt to begin scan...")
    wordHunter.solveWordHunt(size)
elif choice == 3:
    print("Press Left Alt to begin scan...")
    wordBiter.solveWordBites()