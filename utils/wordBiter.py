from utils.mirroring import *
import json
from pynput.mouse import Controller, Button
import time
import cv2
import mss
import numpy as np
import os

stop_flag = False

scan_ocr = False

def parseBoardOCR(bounds, deviceParams):
    lw = deviceParams["wordBites"]["letter_size"] / deviceParams["referenceWidth"] * bounds[2]
    boardText = ""
    for r in range(9):
        for c in range(8):
            letterPos = tileCoords(r, c, bounds, deviceParams)
            letterBounds = {"top": letterPos[1] - lw/2, "left": letterPos[0] - lw/2, "width": lw, "height": lw}
            
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
                boardText += best_match_char
            else:
                boardText += " "
    return boardText

def parsePieces(boardText):
    boardText = boardText.replace("1", " ").replace("2", "  ").replace("3", "   ").replace("4", "    ").replace("5", "     ").replace("6", "      ").replace("7", "       ").replace("8", "        ")
    pieces = []
    board = [boardText.upper()[i:i+8]for i in range(0, 9*8, 8)]
    checked = [[False for _ in range(8)] for _ in range(9)]
    for r in range(9):
        for c in range(8):
            if board[r][c] == " " or checked[r][c]:
                continue
            elif c < 7 and board[r][c+1] != " ":
                # Horizontal piece
                pieces.append({
                    "letters": board[r][c] + board[r][c+1],
                    "dir": "x",
                    "pos": [r, c],
                    "id": len(pieces)
                })
                checked[r][c+1] = True
            elif r < 8 and board[r+1][c] != " ":
                # Vertical piece
                pieces.append({
                    "letters": board[r][c] + board[r+1][c],
                    "dir": "y",
                    "pos": [r, c],
                    "id": len(pieces)
                })
                checked[r+1][c] = True
            else:
                # Single letter piece
                pieces.append({
                    "letters": board[r][c],
                    "dir": "x",
                    "pos": [r, c],
                    "id": len(pieces)
                })
    return pieces

def initializeBoard(pieces):
    board = [["." for _ in range(8)] for _ in range(9)]
    for piece in pieces:
        for i, letter in enumerate(piece["letters"]):
            if piece["dir"] == "x":
                row, col = piece["pos"][0], piece["pos"][1] + i
            else:
                row, col = piece["pos"][0] + i, piece["pos"][1]
            board[row][col] = letter
    return board

def buildWord(word, pieces, dir):
    for piece in pieces:
        letters = piece["letters"]
        if piece["dir"] == dir and word.startswith(letters):
            if len(word) == len(letters):
                return (True, [piece["id"]])
            else:
                piece["letters"] = "*"
                found, ids = buildWord(word[len(letters):], pieces, dir)
                piece["letters"] = letters
                if found:
                    return (True, [piece["id"]] + ids)
        elif piece["dir"] != dir and word[0] in letters:
            if len(word) == 1:
                return (True, [piece["id"]])
            else:
                piece["letters"] = "*"
                found, ids = buildWord(word[1:], pieces, dir)
                piece["letters"] = letters
                if found:
                    return (True, [piece["id"]] + ids)
    return (False, [])

def getAllWords(pieces):
    scrabbleDict = open("resources/dictionary.txt").read().splitlines()
    words = []
    for word in scrabbleDict:
        if len(word) < 3 or len(word) > 9:
            continue
        points = [0, 0, 0, 100, 400, 800, 1400, 1800, 2200, 2600]
        found, ids = buildWord(word, pieces, "x")
        if found and len(word) < 9:
            words.append((word, ids, "x", points[len(word)]))
        else:
            found, ids = buildWord(word, pieces, "y")
            if found:
                words.append((word, ids, "y", points[len(word)]))

    # For each word, count total points building from start to fin
    # Already sorted alphabetically, so check if one word starts with the one before and remove
    i = 0
    while i < len(words) - 1:
        if words[i+1][0].startswith(words[i][0]):
            words[i+1] = (words[i+1][0], words[i+1][1], words[i+1][2], words[i+1][3] + words[i][3])
            words.pop(i)
        else:
            i += 1

    return sorted(words, key=lambda x: -x[3])

def tileCoords(r, c, bounds, params):
    TL, BR = params["wordBites"]["top_left"], params["wordBites"]["bottom_right"]
    x, y, w, _ = bounds
    pixX = x + (TL[0] + (BR[0] - TL[0]) / 7 * c) / params["referenceWidth"] * w
    pixY = y + (TL[1] + (BR[1] - TL[1]) / 8 * r) / params["referenceWidth"] * w
    return int(pixX), int(pixY)

def dragPiece(r1, c1, r2, c2, t, bounds, params, mouse):
    x1, y1 = tileCoords(r1, c1, bounds, params)
    x2, y2 = tileCoords(r2, c2, bounds, params)
    mouse.position = (x1, y1)
    time.sleep(0.02)
    mouse.press(Button.left)
    steps = int(t / 0.02)
    for step in range(1, steps + 1):
        mouse.position = (int(x1 + (x2 - x1) * step / steps), int(y1 + (y2 - y1) * step / steps))
        time.sleep(0.02)
    mouse.release(Button.left)
    time.sleep(0.01)

def findSpot(board, dir, length):
    for r in range(8, -1, -1):
        for c in range(7, -1, -1):
            if length == 1 and board[r][c] == ".":
                return [r, c]
            elif dir == "x" and c + 1 < 8 and board[r][c] == "." and board[r][c+1] == ".":
                return [r, c]
            elif dir == "y" and r + 1 < 9 and board[r][c] == "." and board[r+1][c] == ".":
                return [r, c]
    return None

def getBasePositions(pieces):
    set1 = 0
    setH = 0
    setV = 0
    basePos = []
    for piece in pieces:
        if len(piece["letters"]) == 1:
            basePos.append([set1, 0])
            set1 += 1
        elif piece["dir"] == "x":
            basePos.append([setH, 1])
            setH += 1
        else:
            basePos.append([(setV//2)*2, 3 + (setV % 2)])
            setV += 1
    return basePos

def movePiecesStart(pieces, board, basePos, dragTime, bounds, deviceParams, mouse):
    moveAgain = []
    for i, piece in enumerate(pieces):
        if piece["pos"] == basePos[i]:
            continue

        if board[basePos[i][0]][basePos[i][1]] != ".":
            moveAgain.append(i)
        elif piece["dir"] == "x" and board[basePos[i][0]][basePos[i][1]+1] != ".":
            moveAgain.append(i)
        elif piece["dir"] == "y" and board[basePos[i][0]+1][basePos[i][1]] != ".":
            moveAgain.append(i)
        else:
            dragPiece(piece["pos"][0], piece["pos"][1], basePos[i][0], basePos[i][1], dragTime, bounds, deviceParams, mouse)
            piece["pos"] = basePos[i]
            board = initializeBoard(pieces)
            continue
        freeSpot = findSpot(board, piece["dir"], len(piece["letters"]))
        dragPiece(piece["pos"][0], piece["pos"][1], freeSpot[0], freeSpot[1], dragTime, bounds, deviceParams, mouse)
        piece["pos"] = freeSpot
        board = initializeBoard(pieces)
        moveAgain.append(i)

    for i in moveAgain:
        piece = pieces[i]
        dragPiece(piece["pos"][0], piece["pos"][1], basePos[i][0], basePos[i][1], dragTime, bounds, deviceParams, mouse)
        piece["pos"] = basePos[i]

    board = initializeBoard(pieces)

# Pieces always consist of:
# 6 single letter pieces
# 5 double letter pieces
# Start by moving pieces into compact positions:
# 1 H H V . . . .
# 1 H H V . . . .
# 1 H H . . . . .
# 1 H H . . . . .
# 1 . . . . . . .
# 1 . . . . . . .
# . . . . . . . .
# . . . . . . . .
# . . . . . . . .
# (Col 0: single letters, Col 1-2: double horizontal, Col 3-4: double vertical)

# ========================================================================================


def solveWordBites():
    global stop_flag

    # Find all possible words
    bounds = getBounds()
    deviceParams = json.load(open("resources/deviceParams.json"))
    # pieces = parsePieces(input("Paste board state:\n"))
    print("Press Left Alt to scan the board via OCR...")
    while not scan_ocr:
        time.sleep(0.1)
    boardText = parseBoardOCR(bounds, deviceParams)
    pieces = parsePieces(boardText)

    board = initializeBoard(pieces)
    allWords = getAllWords(pieces)
    print(f"Found {len(allWords)} possible words:")

    # Move pieces to starting positions

    mouse = Controller()
    focusWindow()

    dragTime = 0.02

    basePos = getBasePositions(pieces)

    movePiecesStart(pieces, board, basePos, dragTime, bounds, deviceParams, mouse)

    # Build all words
    for i, word in enumerate(allWords[:-1]):
        # Build current word
        if word[2] == "x":
            col = 0
            for pid in word[1]:
                if stop_flag:
                    print("\nMacro stopped!")
                    return
                piece = pieces[pid]
                if piece["dir"] == "x":
                    if piece["pos"] != [7, col]:
                        dragPiece(piece["pos"][0], piece["pos"][1], 7, col, dragTime, bounds, deviceParams, mouse)
                        piece["pos"] = [7, col]
                    col += len(piece["letters"])
                else:
                    r = piece["letters"].index(word[0][col])
                    if piece["pos"] != [7 - r, col]:
                        dragPiece(piece["pos"][0], piece["pos"][1], 7 - r, col, dragTime, bounds, deviceParams, mouse)
                        piece["pos"] = [7 - r, col]
                    col += 1
        else:
            row = 0
            for pid in word[1]:
                if stop_flag:
                    print("\nMacro stopped!")
                    return
                piece = pieces[pid]
                if piece["dir"] == "y":
                    if piece["pos"] != [row, 6]:
                        dragPiece(piece["pos"][0], piece["pos"][1], row, 6, dragTime, bounds, deviceParams, mouse)
                        piece["pos"] = [row, 6]
                    row += len(piece["letters"])
                else:
                    r = piece["letters"].index(word[0][row])
                    if piece["pos"] != [row, 6 - r]:
                        dragPiece(piece["pos"][0], piece["pos"][1], row, 6 - r, dragTime, bounds, deviceParams, mouse)
                        piece["pos"] = [row, 6 - r]
                    row += 1
        
        # Get filled positions for next word (This is inefficient but fast so whatever)
        nextWord = allWords[i+1]
        # filledPositions = []
        # if nextWord[2] == "x":
        #     col = 0
        #     for pid in nextWord[1]:
        #         piece = pieces[pid]
        #         if piece["dir"] == "x":
        #             filledPositions.append((7, col))
        #             if len(piece["letters"]) == 2:
        #                 filledPositions.append((7, col + 1))
        #             col += len(piece["letters"])
        #         else:
        #             r = piece["letters"].index(nextWord[0][col])
        #             filledPositions.append((7 - r, col))
        #             if len(piece["letters"]) == 2:
        #                 filledPositions.append((6 if r == 1 else 8, col))
        #             col += 1
        # else:
        #     row = 0
        #     for pid in nextWord[1]:
        #         piece = pieces[pid]
        #         if piece["dir"] == "y":
        #             filledPositions.append((row, 6))
        #             if len(piece["letters"]) == 2:
        #                 filledPositions.append((row + 1, 6))
        #             row += len(piece["letters"])
        #         else:
        #             r = piece["letters"].index(nextWord[0][row])
        #             filledPositions.append((row, 6 - r))
        #             if len(piece["letters"]) == 2:
        #                 filledPositions.append((row, 5 if r == 1 else 7))
        #             row += 1
        
        # Return any pieces that are not in the right position and in the way
        for pid in word[1]:
            if stop_flag:
                print("\nMacro stopped!")
                return
            piece = pieces[pid]
            if len(piece["letters"]) == 1:
                otherPos = (9,9)
            else:
                if piece["dir"] == "x":
                    otherPos = (piece["pos"][0], piece["pos"][1] + 1)
                else:
                    otherPos = (piece["pos"][0] + 1, piece["pos"][1])
            if pid not in nextWord[1]:
                dragPiece(piece["pos"][0], piece["pos"][1], basePos[pid][0], basePos[pid][1], dragTime, bounds, deviceParams, mouse)
                piece["pos"] = basePos[pid]
            # elif tuple(piece["pos"]) in filledPositions or otherPos in filledPositions:
            #     dragPiece(piece["pos"][0], piece["pos"][1], basePos[pid][0], basePos[pid][1], dragTime, bounds, deviceParams, mouse)
            #     piece["pos"] = basePos[pid]
            elif nextWord[2] == "x" and (piece["pos"][0] > 5 or otherPos[0] > 5):
                dragPiece(piece["pos"][0], piece["pos"][1], basePos[pid][0], basePos[pid][1], dragTime, bounds, deviceParams, mouse)
                piece["pos"] = basePos[pid]
            elif nextWord[2] == "y" and (piece["pos"][1] > 4 or otherPos[1] > 4):
                dragPiece(piece["pos"][0], piece["pos"][1], basePos[pid][0], basePos[pid][1], dragTime, bounds, deviceParams, mouse)
                piece["pos"] = basePos[pid]
        
        boardState = initializeBoard(pieces)
        print("\n".join(["".join(row) for row in boardState]))
        print("Next Word:")
        print(f"{nextWord[0]} (dir: {nextWord[2]})")
        print("====================")