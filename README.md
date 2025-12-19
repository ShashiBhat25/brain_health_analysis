# Brain Health Analysis System

A comprehensive healthcare AI system for doctors, caretakers, and patients with advanced EEG brain signal analysis capabilities.

## Features

### For Patients
- 🔐 Secure signup and login with Aadhar ID + TOTP
- 🛡️ Two-factor authentication with Google Authenticator
- 👨‍⚕️ Select and manage doctors
- 📋 View prescriptions and medical records
- 🧠 AI-powered brain signal analysis (EEG)
- 📊 Visual EEG signal charts
- 👤 Profile management with 2FA settings

### For Doctors
- 🔐 Secure signup and login (auto-generated Doctor ID) + TOTP
- 🛡️ Two-factor authentication with backup codes
- 👥 Manage patient list
- 📝 Create digital prescriptions with file upload or camera
- 🔍 Search and verify patients
- 📊 View patient brain signal reports
- 🔒 Digital signature for prescription integrity
- 👤 Profile management with 2FA settings

### For Caretakers
- 🔐 Secure signup and login (auto-generated Caretaker ID)
- 👥 Add and manage multiple patients
- 📋 View patient prescriptions (access-controlled)
- 🔒 Secure patient data access
- 👤 Profile management

### AI Brain Signal Analysis
- 🧠 Random Forest Classifier (98.46% accuracy)
- 📊 Real-time EEG signal visualization
- 🎯 4-class classification:
  - Normal
  - Pre-seizure
  - Seizure
  - Post-seizure
- 📁 Multiple input methods: CSV upload, text input, manual entry
- 📧 Share reports with doctors

## Technology Stack

- **Backend:** Flask (Python)
- **Database:** MySQL
- **ML Model:** scikit-learn (Random Forest)
- **Frontend:** Bootstrap 5, HTML5, CSS3, JavaScript
- **Visualization:** Chart.js
- **File Handling:** Werkzeug
- **Data Processing:** Pandas, NumPy

## Installation

### Prerequisites
- Python 3.8+
- MySQL Server
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/ShashiBhat25/brain_health_analysis.git
cd brain_health_analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install flask mysql-connector-python pandas numpy scikit-learn joblib werkzeug pyotp qrcode Pillow
```

3. Configure MySQL:
- Create a MySQL database named `healthcare_system`
- Update database credentials in `Doctors_prescription_patient_1/app.py`:
```python
db_config = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password'
}
```

4. Run the application:
```bash
cd Doctors_prescription_patient_1
python app.py
```

5. Access the application:
- Open browser and navigate to `http://localhost:5000`

## Two-Factor Authentication Setup

### Enable TOTP Security

1. **Create Account**: Sign up as patient, doctor, or caretaker
2. **Login**: Use your credentials to access your profile
3. **Enable 2FA**: Go to Profile → Two-Factor Authentication
4. **Install App**: Download Google Authenticator on your phone
5. **Scan QR Code**: Use the app to scan the displayed QR code
6. **Verify Setup**: Enter the 6-digit code from your app
7. **Save Backup Codes**: Store the 10 backup codes securely

### Supported Authenticator Apps
- Google Authenticator (Recommended)
- Microsoft Authenticator  
- Authy
- 1Password
- Any RFC 6238 compliant TOTP app

### Using TOTP
- **Login**: Enter username/password + 6-digit TOTP code
- **Backup**: Use backup codes if phone unavailable
- **Management**: Enable/disable 2FA in profile settings

## Project Structure

```
brain_health_analysis/
├── Doctors_prescription_patient_1/
│   ├── app.py                          # Main Flask application
│   ├── Best_Model.pkl                  # Trained ML model
│   ├── test_totp.py                    # TOTP functionality tests
│   ├── totp_demo.py                    # Interactive TOTP demo
│   ├── TOTP_README.md                  # Detailed TOTP documentation
│   ├── static/
│   │   ├── style.css                   # Custom styles
│   │   └── uploads/prescriptions/      # Uploaded prescription files
│   ├── templates/                      # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── setup_totp.html             # TOTP setup wizard
│   │   ├── totp_backup_codes.html      # Backup codes display
│   │   ├── patient_*.html
│   │   ├── doctor_*.html
│   │   └── caretaker_*.html
│   └── EEG-Brainwave-Sensor-Dataset/  # Training dataset
├── sleep-final_eeg.ipynb               # Jupyter notebook for model training
├── .gitignore
└── README.md
```

## Database Schema

### Tables
- `patients` - Patient information
- `doctors` - Doctor information
- `caretaker` - Caretaker information
- `patient_doctors` - Patient-doctor relationships
- `caretaker_patients` - Caretaker-patient relationships
- `prescriptions` - Digital prescriptions with file attachments
- `brain_reports` - EEG analysis reports
- `patient_otp` - OTP verification records

## Model Training

To retrain the model with your own data:

1. Prepare your EEG dataset in CSV format (85 features + 1 class label)
2. Update the dataset path in `train_model.py`
3. Run training:
```bash
python train_model.py
```

The model uses:
- **Algorithm:** Random Forest Classifier
- **Features:** 85 EEG signal features
- **Classes:** 0 (Normal), 1 (Pre-seizure), 2 (Seizure), 3 (Post-seizure)
- **Accuracy:** 98.46%

## Security Features

- 🔒 **Two-Factor Authentication (TOTP)**: Google Authenticator integration
- 🔐 **Backup Codes**: Recovery options for lost devices
- 🔑 **QR Code Setup**: Easy authenticator app configuration
- ✅ **Access Control**: Role-based patient data protection
- 🔏 **Digital Signatures**: Prescription integrity verification
- 🛡️ **File Upload Validation**: Secure document handling
- 🔑 **Unique ID Generation**: Auto-generated secure identifiers
- 🔐 **Session Management**: Secure authentication state

## Usage

### Patient Workflow
1. Sign up with Aadhar ID
2. Select doctors from available list
3. Upload EEG data for analysis
4. View results and share with doctors
5. Access prescriptions from doctors

### Doctor Workflow
1. Sign up (auto-generated Doctor ID)
2. Search for patients by Aadhar ID
3. View patient details and history
4. Create prescriptions (with optional file/photo)
5. View brain signal reports from patients

### Caretaker Workflow
1. Sign up (auto-generated Caretaker ID)
2. Add patients by Aadhar ID
3. View patient prescriptions
4. Manage multiple patients

## Clear Database

To reset the database:
```bash
python clear_database.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is for educational and research purposes.

## Author

Shashi Bhat

## Acknowledgments

- EEG dataset from Kaggle
- scikit-learn for ML algorithms
- Flask framework
- Bootstrap for UI components
