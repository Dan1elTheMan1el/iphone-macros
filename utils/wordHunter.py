from utils.mirroring import *
import json
from pynput.mouse import Controller, Button
import time
import mss
import cv2
import numpy as np
import os

# Global flag to stop macro execution (set by keyboard listener in macros.py)
stop_flag = False

scan_ocr = False

def getNeighbors(pos, size):
    neighbors = []
    if pos[0] > 0:
        neighbors.append((pos[0] - 1, pos[1]))
        if pos[1] > 0:
            neighbors.append((pos[0], pos[1] - 1))
            neighbors.append((pos[0] - 1, pos[1] - 1))
        if pos[1] < size - 1:
            neighbors.append((pos[0], pos[1] + 1))
            neighbors.append((pos[0] - 1, pos[1] + 1))
    if pos[0] < size - 1:
        neighbors.append((pos[0] + 1, pos[1]))
        if pos[1] > 0:
            neighbors.append((pos[0], pos[1] - 1))
            neighbors.append((pos[0] + 1, pos[1] - 1))
        if pos[1] < size - 1:
            neighbors.append((pos[0], pos[1] + 1))
            neighbors.append((pos[0] + 1, pos[1] + 1))
    return neighbors

def lettersToArr(letters):
    size = int(len(letters) ** 0.5)
    arr = []
    for i in range(size):
        row = []
        for j in range(size):
            row.append(letters[i * size + j])
        arr.append(row)
    return arr

def buildWord(board, pos, word):
    neighbours = getNeighbors(pos, len(board))
    for neighbor in neighbours:
        if board[neighbor[0]][neighbor[1]] == word[0]:
            if len(word) == 1:
                return [neighbor]
            board[neighbor[0]][neighbor[1]] = '#'
            subpath = buildWord(board, neighbor, word[1:])
            board[neighbor[0]][neighbor[1]] = word[0]
            if subpath is not None:
                return [neighbor] + subpath
    return None

def getLetters(size, bounds, deviceParams):
    lw = deviceParams["wordHunt"][f"{size}x{size}_letter_size"] / deviceParams["referenceWidth"] * bounds[2]
    letters = ""
    for r in range(size):
        for c in range(size):
            tilePos = letterPos(bounds, r, c, size, deviceParams)
            letterBounds = {"top": tilePos[1] - lw/2, "left": tilePos[0] - lw/2, "width": lw, "height": lw}
            
            with mss.mss() as sct:
                img_grab = sct.grab(letterBounds)
                width = img_grab.width
                height = img_grab.height
                
                raw_bytes = img_grab.rgb
                byte_list = list(raw_bytes)
                img_cv = np.array(byte_list, dtype=np.uint8).reshape((height, width, 3))
                
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, final_image_array = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            inverted_image_array = cv2.bitwise_not(final_image_array)

            # cv2.imwrite("debug_letter.png", inverted_image_array)

            scaled_image = cv2.resize(
                inverted_image_array, 
                (23, 23), 
                interpolation=cv2.INTER_NEAREST
            )
            
            padded_capture = cv2.copyMakeBorder(
                scaled_image, 
                10, 10, 10, 10, 
                cv2.BORDER_CONSTANT, value=[255]
            )
            
            best_match_score = -1
            best_match_char = None
            
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                template_path = os.path.join("ocr_templates" , f"{char}.png")
                template = cv2.imread(template_path, 0)

                result = cv2.matchTemplate(padded_capture, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                score = max_val 
                
                if score > best_match_score:
                    best_match_score = score
                    best_match_char = char
                    
            if best_match_score >= 0.8: 
                letters += best_match_char
            else:
                letters += " "
    return letters

# Return position of letter
def letterPos(bounds, row, col, size, deviceParams):
    x, y, w, _ = bounds
    letter_x = x + (deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][0] / deviceParams["referenceWidth"]) * w + col * (deviceParams["wordHunt"][f"{size}x{size}"]["bottom_right"][0] - deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][0]) / deviceParams["referenceWidth"] / (size - 1) * w
    letter_y = y + (deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][1] / deviceParams["referenceWidth"]) * w + row * (deviceParams["wordHunt"][f"{size}x{size}"]["bottom_right"][1] - deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][1]) / deviceParams["referenceWidth"] / (size - 1) * w
    return (int(letter_x), int(letter_y))

# Find all possible paths for words
def findPaths(letters):
    paths = []
    board = lettersToArr(letters)
    scrabbleWords = open("resources/dictionary.txt").read().splitlines()

    for word in scrabbleWords:
        found = False # Only find first occurrence of each word
        if word[0] not in letters or len(word) > len(letters) or len(word) < 3:
            continue
        for r in range(len(board)):
            for c in range(len(board)):
                if board[r][c] == word[0]:
                    board[r][c] = '#'
                    path = buildWord(board, (r, c), word[1:])
                    board[r][c] = word[0]
                    if path is not None:
                        paths.append([(r, c)] + path)
                        found = True
                        break
            if found:
                break
        
    return sorted(paths, key=lambda x: -len(x))

# Solve and input anagram given letters
def solveWordHunt(size):
    mouse = Controller()
    bounds = getBounds()
    deviceParams = json.load(open("resources/deviceParams.json"))

    global stop_flag
    global scan_ocr
    stop_flag = False  # Reset flag at start of macro

    while not scan_ocr:
        time.sleep(0.1)
    
    letters = getLetters(size, bounds, deviceParams)
    print(letters)

    paths = findPaths(letters)
    size = int(len(letters) ** 0.5)
    focusWindow()

    for path in paths:
        x0, y0 = letterPos(bounds, path[0][0], path[0][1], size, deviceParams)
        mouse.position = (x0, y0)
        time.sleep(0.02)
        mouse.press(Button.left)
        
        for pos in path[1:]:
            if stop_flag:
                print("\n⏹️  Macro stopped by user")
                mouse.release(Button.left)
                return
            time.sleep(0.02)
            mouse.position = letterPos(bounds, pos[0], pos[1], size, deviceParams)
        time.sleep(0.02)
        mouse.release(Button.left)