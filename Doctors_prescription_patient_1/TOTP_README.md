# TOTP (Two-Factor Authentication) Implementation

## 🔐 Overview

This healthcare application now includes **TOTP (Time-based One-Time Password)** authentication for enhanced security. TOTP provides an additional layer of protection for patient and doctor accounts containing sensitive medical information.

## 🚀 Features Implemented

### ✅ Core TOTP Features
- **QR Code Setup**: Easy setup with authenticator apps
- **6-digit TOTP codes**: Standard 30-second rotating codes
- **Backup Codes**: 10 one-time recovery codes
- **Multi-user Support**: Works for patients, doctors, and caretakers
- **Graceful Fallback**: Backup codes when phone is unavailable

### ✅ Security Features
- **Time Window Tolerance**: 30-second buffer for clock drift
- **One-time Use**: Each backup code can only be used once
- **Secure Storage**: Encrypted secrets in database
- **Session Management**: Proper cleanup of temporary data

### ✅ User Experience
- **Auto-formatting**: Input fields format codes automatically
- **Visual Feedback**: Clear success/error messages
- **Print/Copy Options**: Easy backup code management
- **Mobile Responsive**: Works on all devices

## 📱 Supported Authenticator Apps

- **Google Authenticator** (Recommended)
- **Microsoft Authenticator**
- **Authy**
- **1Password**
- **Any RFC 6238 compliant TOTP app**

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip install pyotp qrcode Pillow
```

### 2. Database Setup
The app automatically creates the necessary database columns:
- `totp_secret` - Stores the user's TOTP secret
- `totp_enabled` - Boolean flag for 2FA status
- `backup_codes` - JSON array of backup codes

### 3. Test Installation
```bash
python test_totp.py
```

## 👥 User Guide

### For Patients

#### Enabling TOTP
1. Login to your account
2. Go to **Profile** → **Two-Factor Authentication**
3. Click **"Enable Two-Factor Authentication"**
4. Install Google Authenticator on your phone
5. Scan the QR code displayed
6. Enter the 6-digit code from your app
7. **Save your backup codes** in a secure location

#### Using TOTP
1. Enter your Aadhar ID and password as usual
2. When prompted, open your authenticator app
3. Enter the current 6-digit code
4. If you don't have your phone, use a backup code

#### Managing TOTP
- **Disable 2FA**: Requires password + current TOTP code
- **Regenerate Backup Codes**: Creates new codes (old ones become invalid)
- **View Status**: Check if 2FA is enabled in your profile

### For Doctors

Same process as patients, but using:
- Email and password for login
- Doctor profile for TOTP management

## 🔧 Technical Implementation

### Database Schema
```sql
-- Added to existing user tables
ALTER TABLE patients ADD COLUMN totp_secret VARCHAR(32);
ALTER TABLE patients ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE patients ADD COLUMN backup_codes TEXT;

ALTER TABLE doctors ADD COLUMN totp_secret VARCHAR(32);
ALTER TABLE doctors ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE doctors ADD COLUMN backup_codes TEXT;

ALTER TABLE caretaker ADD COLUMN totp_secret VARCHAR(32);
ALTER TABLE caretaker ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE caretaker ADD COLUMN backup_codes TEXT;
```

### Key Functions
```python
# Generate TOTP secret
secret = generate_totp_secret()

# Create QR code
qr_code = generate_qr_code(secret, user_email)

# Verify TOTP code
is_valid = verify_totp_code(secret, user_code)

# Generate backup codes
backup_codes = generate_backup_codes()

# Verify backup code
is_valid, updated_codes = verify_backup_code(stored_codes, entered_code)
```

### Security Considerations
- **Secret Storage**: TOTP secrets are stored securely in the database
- **Time Synchronization**: 30-second window tolerance for clock drift
- **Backup Code Consumption**: Each backup code can only be used once
- **Session Security**: Temporary secrets cleared after setup

## 🔒 Security Benefits

### For Healthcare Data
- **HIPAA Compliance**: Meets healthcare security standards
- **Patient Privacy**: Extra protection for medical records
- **Access Control**: Prevents unauthorized account access
- **Audit Trail**: Login attempts are logged

### Technical Security
- **Offline Capability**: Works without internet connection
- **Standardized**: Uses RFC 6238 TOTP standard
- **Time-limited**: Codes expire every 30 seconds
- **Multi-factor**: Combines "something you know" + "something you have"

## 🚨 Troubleshooting

### Common Issues

#### "Invalid TOTP code"
- **Check time sync**: Ensure phone time is accurate
- **Wait for new code**: Current code might have expired
- **Try backup code**: Use if authenticator app issues

#### "TOTP setup session expired"
- **Refresh page**: Start setup process again
- **Clear browser cache**: Remove temporary data

#### "Can't scan QR code"
- **Manual entry**: Use the text secret key instead
- **Check camera permissions**: Allow camera access
- **Try different app**: Some apps scan better than others

### Recovery Options
1. **Backup Codes**: Use one of your saved backup codes
2. **Contact Support**: If all backup codes are used
3. **Account Recovery**: May require identity verification

## 📊 Testing

### Automated Tests
Run the test suite to verify functionality:
```bash
python test_totp.py
```

### Manual Testing Checklist
- [ ] Enable TOTP for patient account
- [ ] Scan QR code with authenticator app
- [ ] Login with TOTP code
- [ ] Login with backup code
- [ ] Disable TOTP
- [ ] Regenerate backup codes

## 🔄 Future Enhancements

### Planned Features
- **SMS Backup**: SMS codes as fallback option
- **Multiple Devices**: Support for multiple authenticator devices
- **Admin Panel**: Manage 2FA for all users
- **Usage Analytics**: Track 2FA adoption rates

### Security Improvements
- **Rate Limiting**: Prevent brute force attacks
- **Device Trust**: Remember trusted devices
- **Geolocation**: Alert on unusual login locations
- **Hardware Keys**: Support for FIDO2/WebAuthn

## 📞 Support

### For Users
- Check this documentation first
- Ensure authenticator app is up to date
- Keep backup codes in a secure location
- Contact system administrator if locked out

### For Developers
- Review the `test_totp.py` file for examples
- Check Flask logs for detailed error messages
- Verify database schema changes were applied
- Test with multiple authenticator apps

## 🎯 Best Practices

### For Users
1. **Use a reputable authenticator app**
2. **Save backup codes securely** (not on your phone)
3. **Enable 2FA on all important accounts**
4. **Keep your phone secure** with a lock screen
5. **Don't share TOTP codes** with anyone

### For Administrators
1. **Encourage 2FA adoption** through user education
2. **Monitor failed login attempts** for security issues
3. **Have account recovery procedures** in place
4. **Regular security audits** of the implementation
5. **Keep dependencies updated** for security patches

---

**🏥 Healthcare App TOTP Implementation**  
*Securing patient data with industry-standard two-factor authentication*