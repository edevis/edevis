import sys
import tty
import termios

Esc = "\x1b"

class EscPressedException(Exception):
    def __init__(self, message="ESC wurde gedrückt – Aktion abgebrochen."):
        super().__init__(message)

def getchar(info = None):
    # Info message
    if info:
        print(f"{info}", end="", flush=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)  # liest 1 Zeichen sofort
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    # Zeilenumbruch
    if info:
        print()

    return ch


def input_char(info, selection = ['j', 'n']):
    print(f"{info}\nAuswahl [{' / '.join(selection)}] / Esc -> Quit : ", end="", flush=True)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    ch = ''
    while True:
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)  # liest 1 Zeichen sofort
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            if ch in selection:
                print()  # Neue Zeile nach der Eingabe
                return ch
            if ch == Esc:
                print()
                raise EscPressedException()
    