try:
    from coin_handler.python.coin_handler_serial import CoinHandlerSerial
    print("Syntax check passed: CoinHandlerSerial imported successfully.")
except ImportError as e:
    # It might fail due to missing dependencies like serial if not in env, 
    # but we just want to check for SyntaxError in the file itself.
    print(f"ImportError (expected if dependencies missing): {e}")
except SyntaxError as e:
    print(f"SyntaxError: {e}")
    exit(1)
except Exception as e:
    print(f"Other error: {e}")
