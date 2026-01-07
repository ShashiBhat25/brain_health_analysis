#!/usr/bin/env python3
"""
Interactive TOTP Demo for Healthcare App
This script demonstrates how TOTP works in real-time
"""

import pyotp
import qrcode
import time
import os
from datetime import datetime

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print demo header"""
    print("🔐 Healthcare App - TOTP Demo")
    print("=" * 50)
    print()

def demo_totp_generation():
    """Demonstrate TOTP code generation"""
    print("📱 TOTP Code Generation Demo")
    print("-" * 30)
    
    # Generate a secret (this would be stored in database)
    secret = pyotp.random_base32()
    print(f"Secret Key: {secret}")
    print("(This would be stored securely in the database)")
    print()
    
    # Create TOTP object
    totp = pyotp.TOTP(secret)
    
    print("🕐 Watching TOTP codes change every 30 seconds...")
    print("Press Ctrl+C to continue to next demo")
    print()
    
    try:
        while True:
            current_code = totp.now()
            remaining_time = 30 - (int(time.time()) % 30)
            
            print(f"\r🔢 Current Code: {current_code} | ⏰ Expires in: {remaining_time:2d}s", end="", flush=True)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n")
        return secret

def demo_qr_code(secret):
    """Demonstrate QR code generation"""
    print("\n📱 QR Code Generation Demo")
    print("-" * 30)
    
    totp = pyotp.TOTP(secret)
    
    # Generate provisioning URI
    provisioning_uri = totp.provisioning_uri(
        name="demo@healthcare.com",
        issuer_name="Healthcare App Demo"
    )
    
    print("🔗 Provisioning URI:")
    print(provisioning_uri)
    print()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    print("📱 QR Code (scan with authenticator app):")
    qr.print_ascii(invert=True)
    print()
    
    return totp

def demo_verification(totp):
    """Demonstrate code verification"""
    print("🔍 Code Verification Demo")
    print("-" * 30)
    
    print("Enter TOTP codes to test verification:")
    print("(Enter 'quit' to exit)")
    print()
    
    while True:
        try:
            user_input = input("Enter 6-digit code: ").strip()
            
            if user_input.lower() == 'quit':
                break
                
            if len(user_input) != 6 or not user_input.isdigit():
                print("❌ Invalid format. Please enter 6 digits.")
                continue
            
            # Verify the code
            is_valid = totp.verify(user_input, valid_window=1)
            
            if is_valid:
                print("✅ Code VALID - Login would succeed!")
            else:
                print("❌ Code INVALID - Login would fail!")
                
            print(f"Current valid code: {totp.now()}")
            print()
            
        except KeyboardInterrupt:
            break

def demo_backup_codes():
    """Demonstrate backup code system"""
    print("\n🔑 Backup Codes Demo")
    print("-" * 30)
    
    import random
    import json
    
    # Generate backup codes
    backup_codes = []
    for _ in range(10):
        code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        backup_codes.append(code)
    
    print("Generated backup codes:")
    for i, code in enumerate(backup_codes, 1):
        print(f"{i:2d}. {code}")
    
    print("\n🔍 Testing backup code verification:")
    
    # Simulate using a backup code
    stored_codes = json.dumps(backup_codes)
    test_code = backup_codes[0]
    
    print(f"Trying to use code: {test_code}")
    
    # Verify backup code
    codes_list = json.loads(stored_codes)
    if test_code in codes_list:
        codes_list.remove(test_code)
        updated_codes = json.dumps(codes_list)
        print("✅ Backup code VALID and consumed!")
        print(f"Remaining codes: {len(codes_list)}")
    else:
        print("❌ Backup code INVALID!")
    
    print("\n⚠️  Important: Each backup code can only be used ONCE!")

def demo_security_features():
    """Demonstrate security features"""
    print("\n🛡️  Security Features Demo")
    print("-" * 30)
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    
    print("1. Time Window Tolerance:")
    current_code = totp.now()
    
    for window in [0, 1, 2]:
        is_valid = totp.verify(current_code, valid_window=window)
        print(f"   Window {window} (±{window*30}s): {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    print("\n2. Code Expiration:")
    print(f"   Current code: {current_code}")
    print(f"   Expires in: {30 - (int(time.time()) % 30)} seconds")
    
    print("\n3. Replay Attack Prevention:")
    print("   Each code can only be used once per time window")
    print("   Old codes are automatically rejected")
    
    print("\n4. Offline Capability:")
    print("   ✅ Works without internet connection")
    print("   ✅ Synchronized using device time")

def main():
    """Run the interactive demo"""
    clear_screen()
    print_header()
    
    print("This demo shows how TOTP works in your healthcare app.")
    print("Follow along to understand the security features.")
    print()
    input("Press Enter to start the demo...")
    
    # Demo 1: Code Generation
    clear_screen()
    print_header()
    secret = demo_totp_generation()
    
    # Demo 2: QR Code
    totp = demo_qr_code(secret)
    
    # Demo 3: Verification
    demo_verification(totp)
    
    # Demo 4: Backup Codes
    demo_backup_codes()
    
    # Demo 5: Security Features
    demo_security_features()
    
    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")
    print("\nKey Takeaways:")
    print("✅ TOTP provides strong two-factor authentication")
    print("✅ Codes change every 30 seconds")
    print("✅ Works offline with any authenticator app")
    print("✅ Backup codes provide recovery option")
    print("✅ Perfect for securing healthcare data")
    print("\nNext: Enable TOTP in your healthcare app profile!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Thanks for watching!")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        print("Make sure you have installed: pip install pyotp qrcode")