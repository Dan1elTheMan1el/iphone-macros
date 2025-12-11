from utils.mirroring import *
import json
from pynput.mouse import Controller, Button
import time

# Global flag to stop macro execution (set by keyboard listener in macros.py)
stop_flag = False

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

# Return position of letter
def letterPos(bounds, row, col, size, deviceParams):
    x, y, w, _ = bounds
    letter_x = x + (deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][0] / deviceParams["referenceWidth"]) * w + (col + 0.5) * (deviceParams["wordHunt"][f"{size}x{size}"]["bottom_right"][0] - deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][0]) / deviceParams["referenceWidth"] / size * w
    letter_y = y + (deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][1] / deviceParams["referenceWidth"]) * w + (row + 0.5) * (deviceParams["wordHunt"][f"{size}x{size}"]["bottom_right"][1] - deviceParams["wordHunt"][f"{size}x{size}"]["top_left"][1]) / deviceParams["referenceWidth"] / size * w
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
def solveWordHunt(letters):
    mouse = Controller()
    bounds = getBounds()
    deviceParams = json.load(open("resources/deviceParams.json"))

    global stop_flag
    stop_flag = False  # Reset flag at start of macro
    paths = findPaths(letters)
    size = int(len(letters) ** 0.5)
    for path in paths:
        focusWindow()
        x0, y0 = letterPos(bounds, path[0][0], path[0][1], size, deviceParams)
        mouse.position = (x0, y0)
        time.sleep(0.1)
        mouse.press(Button.left)
        
        for pos in path[1:]:
            if stop_flag:
                print("\n⏹️  Macro stopped by user")
                mouse.release(Button.left)
                return
            time.sleep(0.05)
            mouse.position = letterPos(bounds, pos[0], pos[1], size, deviceParams)
        time.sleep(0.05)
        mouse.release(Button.left)