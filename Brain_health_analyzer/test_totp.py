#!/usr/bin/env python3
"""
Test script for TOTP implementation
Run this to verify TOTP functionality before using in the app
"""

import pyotp
import qrcode
import time
from io import BytesIO
import base64

def test_totp_basic():
    """Test basic TOTP functionality"""
    print("=== Testing Basic TOTP Functionality ===")
    
    # Generate a secret
    secret = pyotp.random_base32()
    print(f"Generated secret: {secret}")
    
    # Create TOTP object
    totp = pyotp.TOTP(secret)
    
    # Generate current code
    current_code = totp.now()
    print(f"Current TOTP code: {current_code}")
    
    # Verify the code
    is_valid = totp.verify(current_code)
    print(f"Code verification: {'✅ PASS' if is_valid else '❌ FAIL'}")
    
    # Test with wrong code
    wrong_code = "000000"
    is_invalid = totp.verify(wrong_code)
    print(f"Wrong code rejection: {'✅ PASS' if not is_invalid else '❌ FAIL'}")
    
    return secret

def test_qr_code_generation(secret, email="test@healthcare.com"):
    """Test QR code generation"""
    print("\n=== Testing QR Code Generation ===")
    
    try:
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=email,
            issuer_name="Healthcare App Test"
        )
        print(f"Provisioning URI: {provisioning_uri}")
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"QR code generated successfully (length: {len(qr_code_base64)} chars)")
        print("✅ QR Code generation: PASS")
        
        return qr_code_base64
        
    except Exception as e:
        print(f"❌ QR Code generation: FAIL - {e}")
        return None

def test_time_window():
    """Test TOTP time window tolerance"""
    print("\n=== Testing Time Window Tolerance ===")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    
    # Get current code
    current_code = totp.now()
    
    # Test with different time windows
    for window in [0, 1, 2]:
        is_valid = totp.verify(current_code, valid_window=window)
        print(f"Window {window}: {'✅ PASS' if is_valid else '❌ FAIL'}")

def test_backup_codes():
    """Test backup code generation and verification"""
    print("\n=== Testing Backup Codes ===")
    
    import random
    import json
    
    # Generate backup codes (simulate the function)
    codes = []
    for _ in range(10):
        code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        codes.append(code)
    
    print(f"Generated {len(codes)} backup codes")
    
    # Test verification
    stored_codes = json.dumps(codes)
    test_code = codes[0]  # Use first code
    
    # Simulate verification
    codes_list = json.loads(stored_codes)
    if test_code in codes_list:
        codes_list.remove(test_code)
        updated_codes = json.dumps(codes_list)
        print(f"✅ Backup code verification: PASS")
        print(f"Remaining codes: {len(json.loads(updated_codes))}")
    else:
        print("❌ Backup code verification: FAIL")

def main():
    """Run all tests"""
    print("🔐 Healthcare App TOTP Implementation Test")
    print("=" * 50)
    
    try:
        # Test basic functionality
        secret = test_totp_basic()
        
        # Test QR code generation
        qr_code = test_qr_code_generation(secret)
        
        # Test time windows
        test_time_window()
        
        # Test backup codes
        test_backup_codes()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        print("\nNext steps:")
        print("1. Run your Flask app")
        print("2. Go to patient/doctor profile")
        print("3. Enable TOTP")
        print("4. Scan QR code with Google Authenticator")
        print("5. Test login with TOTP code")
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install pyotp qrcode Pillow")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()