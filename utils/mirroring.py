import subprocess

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