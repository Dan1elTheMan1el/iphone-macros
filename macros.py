from utils import wordHunter, anagrammer, wordBiter
from pynput import keyboard
import os

# Keyboard listener for stop functionality
def on_press(key):
    if key == keyboard.Key.alt_r:
        print("\nRight Alt pressed - stopping macro...")
        wordHunter.stop_flag = True
        anagrammer.stop_flag = True
        wordBiter.stop_flag = True
    elif key == keyboard.Key.enter:
        wordBiter.scan_ocr = True
# Start keyboard listener in background thread
listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Welcome to iPhone macros!\n1. Word Hunt\n2. Anagrams\n3. Word Bites")
choice = int(input("Select a macro to run: "))
print("Press Right Alt at any time to stop the macro.\n")
if choice == 1:
    letters = input("Enter letters row-wise: ").upper()
    wordHunter.solveWordHunt(letters)
elif choice == 2:
    letters = input("Enter letters: ").strip().upper()
    anagrammer.solveAnagrams(letters)
elif choice == 3:
    wordBiter.solveWordBites()