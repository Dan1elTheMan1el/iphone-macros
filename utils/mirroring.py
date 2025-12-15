import subprocess
import mss
import numpy as np
import cv2
import os

# Returns (x, y, width, height) of iPhone Mirroring
def getBounds():
    script = f'''
    tell application "System Events" to tell application process "iPhone Mirroring"
        get position of window 1
        get size of window 1
        return {{position of window 1, size of window 1}}
    end tell
    '''
    process = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    output = process.stdout.strip()
    
    coords = output.strip('{}').split(', ')
    output_values = [int(coords[0]) + 8, int(coords[1]) + 38, int(coords[2]) - 16, int(coords[3]) - 46]
    return output_values

# Focus the iPhone Mirroring window
def focusWindow():
    script = '''
    tell application "iPhone Mirroring"
        activate
    end tell
    '''
    subprocess.run(['osascript', '-e', script])

# Scan piece with OCR
def scanPiece(x, y, w, debug=False):
    letterBounds = {"top": y - w/2, "left": x - w/2, "width": w, "height": w}
    
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

    if debug:
        cv2.imwrite("debug_letter.png", inverted_image_array)

    scaled_image = cv2.resize(
        inverted_image_array, 
        (23, 23), #
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
        template_path = os.path.join("resources/ocr_templates" , f"{char}.png")
        template = cv2.imread(template_path, 0)

        result = cv2.matchTemplate(padded_capture, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        score = max_val 
        
        if score > best_match_score:
            best_match_score = score
            best_match_char = char
            
    if best_match_score >= 0.8: 
        return best_match_char
    else:
        return None