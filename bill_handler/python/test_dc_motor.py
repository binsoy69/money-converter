import curses
from gpiozero import Motor, PWMOutputDevice
from time import sleep

# Setup motor and PWM
motor = Motor(forward=20, backward=21)
enable_pin = PWMOutputDevice(16)

speed = 0.5  # Initial speed
speed_step = 0.1

def apply_speed(stdscr):
    enable_pin.value = speed
    stdscr.addstr(2, 0, f"[SPEED] Current speed: {speed:.1f}   ")
    stdscr.refresh()

def main(stdscr):
    global speed
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    stdscr.clear()
    stdscr.addstr(0, 0, "Use arrow keys to control the motor:")
    stdscr.addstr(1, 0, "←: Backward  →: Forward  ↓: Stop")
    stdscr.addstr(3, 0, "↑: Increase speed  ↓: Decrease speed")
    stdscr.addstr(4, 0, "q: Quit")
    apply_speed(stdscr)

    try:
        while True:
            key = stdscr.getch()

            if key == curses.KEY_RIGHT:
                motor.forward()
                stdscr.addstr(5, 0, "[FORWARD] Motor running forward    ")
            elif key == curses.KEY_LEFT:
                motor.backward()
                stdscr.addstr(5, 0, "[BACKWARD] Motor running backward  ")
            elif key == curses.KEY_DOWN:
                if speed > 0.0:
                    speed = max(0.0, speed - speed_step)
                    apply_speed(stdscr)
            elif key == curses.KEY_UP:
                if speed < 1.0:
                    speed = min(1.0, speed + speed_step)
                    apply_speed(stdscr)
            elif key == ord('s'):
                motor.stop()
                stdscr.addstr(5, 0, "[STOP] Motor stopped               ")
            elif key == ord('q'):
                stdscr.addstr(6, 0, "[EXIT] Quitting...                ")
                stdscr.refresh()
                break

            stdscr.refresh()
            sleep(0.1)

    finally:
        motor.stop()
        enable_pin.off()
        stdscr.addstr(7, 0, "[SHUTDOWN] Motor stopped. Press any key to exit.")
        stdscr.nodelay(False)
        stdscr.getch()

if __name__ == "__main__":
    curses.wrapper(main)
