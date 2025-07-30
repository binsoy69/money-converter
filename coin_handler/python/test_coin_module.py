import serial
import time

PORT = "/dev/ttyACM0"  
BAUD = 9600

def send_command(ser, cmd):
    ser.write((cmd + '\n').encode())
    print(f"[SENT] {cmd}")

def coin_accept_mode(ser):
    send_command(ser, "ENABLE_COIN")
    print("[INFO] Waiting for coins... Press Ctrl+C to cancel.")
    try:
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line:
                print(f"[ARDUINO] {line}")
    except KeyboardInterrupt:
        send_command(ser, "DISABLE_COIN")
        print("\n[INFO] Coin accept mode exited.")

def coin_dispense_mode(ser):
    try:
        denom = int(input("Enter denomination to dispense (1/5/10/20): "))
        count = int(input("Enter number of coins: "))
        send_command(ser, f"DISPENSE:{denom}:{count}")
        while True:
            line = ser.readline().decode('utf-8').strip()
            if line:
                print(f"[ARDUINO] {line}")
            if "[DONE]" in line:
                break
    except Exception as e:
        print(f"[ERROR] {e}")

def main():
    print("[INFO] Connecting to Arduino...")
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)

    while True:
        print("\n=== COIN HANDLER MENU ===")
        print("1. Accept Coin")
        print("2. Dispense Coin")
        print("3. Exit")
        choice = input("Select an option: ")

        if choice == '1':
            coin_accept_mode(ser)
        elif choice == '2':
            coin_dispense_mode(ser)
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

if __name__ == '__main__':
    main()
