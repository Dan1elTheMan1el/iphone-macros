from utils import wordHunter, anagrammer
from pynput import keyboard

# Keyboard listener for stop functionality
def on_press(key):
    if key == keyboard.Key.shift_r:
        print("\n⚠️  Right Shift pressed - stopping macro...")
        wordHunter.stop_flag = True
        anagrammer.stop_flag = True

# Start keyboard listener in background thread
listener = keyboard.Listener(on_press=on_press)
listener.start()

print("Welcome to iPhone macros!\n1. Word Hunt\n2. Anagrams")
choice = int(input("Select a macro to run: "))
print("Press Right Shift at any time to stop the macro.\n")
if choice == 1:
    letters = input("Enter letters row-wise: ").upper()
    wordHunter.solveWordHunt(letters)
elif choice == 2:
    letters = input("Enter letters: ").strip().upper()
    anagrammer.solveAnagrams(letters)