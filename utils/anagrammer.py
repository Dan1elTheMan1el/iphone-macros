from utils.mirroring import *
from pynput.mouse import Controller, Button
import json
import time

stop_flag = False

def getCounts(word):
    counts = {}
    for letter in word:
        if letter in counts:
            counts[letter] += 1
        else:
            counts[letter] = 1
    return counts

def findAnagrams(letters):
    scrabbleWords = list(filter(lambda word: len(word) <= len(letters) and len(word) > 2, open("resources/dictionary.txt").read().splitlines()))
    buildable = []
    counts = getCounts(letters)
    for word in scrabbleWords:
        wordCounts = getCounts(word)
        isAnagram = True
        for letter in wordCounts:
            if letter not in counts or wordCounts[letter] > counts[letter]:
                isAnagram = False
                break
        if isAnagram:
            buildable.append(word)
    
    indeces = {}
    for i, c in enumerate(letters):
        if c not in indeces:
            indeces[c] = [i]
        else:
            indeces[c].append(i)

    orders = []
    for word in sorted(buildable, key=lambda w: -len(w)):
        order = []
        tempIndeces = {k: v[:] for k, v in indeces.items()}
        for letter in word:
            order.append(tempIndeces[letter].pop())
        orders.append(order)
    return orders

def solveAnagrams(letters):
    global stop_flag
    mouse = Controller()
    x, y, w, _ = getBounds()
    deviceParams = json.load(open("resources/deviceParams.json"))

    orders = findAnagrams(letters)
    for orders in orders:
        focusWindow()
        time.sleep(0.1)

        for pos in orders:
            if stop_flag:
                print("\n⏹️  Macro stopped by user")
                return
            mouse.position = int(x + deviceParams["anagrams"]["letter_x_bounds"][0]/deviceParams["referenceWidth"]*w + pos/(len(letters) - 1) * (deviceParams["anagrams"]["letter_x_bounds"][1] - deviceParams["anagrams"]["letter_x_bounds"][0])/deviceParams["referenceWidth"]*w), int(y + deviceParams["anagrams"]["letter_y"]/deviceParams["referenceWidth"]*w)
            time.sleep(0.05)
            mouse.click(Button.left)
        mouse.position = int(x + deviceParams["anagrams"]["enter"][0]/deviceParams["referenceWidth"]*w), int(y + deviceParams["anagrams"]["enter"][1]/deviceParams["referenceWidth"]*w)
        time.sleep(0.05)
        mouse.click(Button.left)