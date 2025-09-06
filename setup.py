import os
import pandas as pd
from datetime import datetime

def create_directories():
    """Create necessary directories"""
    directories = ['forms', 'data', 'exports']
    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"Created directory: {dir_name}")

def create_sample_forms():
    """Create sample form files"""
    forms_dir = 'forms'
    
    # Create a simple text file as sample form
    sample_form_content = """
PATIENT INTAKE FORM

Patient Name: ________________________
Date of Birth: _______________________
Address: _____________________________
Phone: _______________________________
Email: _______________________________

Medical History:
Previous Surgeries: __________________
Current Medications: _________________
Allergies: ___________________________
Emergency Contact: ___________________

Please fill out this form completely and bring it to your appointment.
    """
    
    with open(os.path.join(forms_dir, 'patient_intake_form.txt'), 'w') as f:
        f.write(sample_form_content)
    
    print("Sample forms created in forms/ directory")

def verify_patients_csv():
    """Verify patients.csv exists"""
    if not os.path.exists('patients.csv'):
        print("⚠️  patients.csv not found. Make sure to add your patients.csv file to the project directory.")
        return False
    else:
        try:
            df = pd.read_csv('patients.csv')
            print(f"✅ patients.csv loaded successfully with {len(df)} patients")
            return True
        except Exception as e:
            print(f"❌ Error reading patients.csv: {e}")
            return False

def verify_env_file():
    """Verify .env file exists with required variables"""
    if not os.path.exists('.env'):
        print("⚠️  .env file not found. Creating sample .env file...")
        sample_env = """# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# Calendar Configuration
CALENDLY_PAT=your_calendly_pat_here
CALENDLY_EVENT_TYPE_UUID=your_event_type_uuid_here
TZ=Asia/Kolkata

# Email Configuration
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587

# Verification Mode
VERIFY_MODE=real
"""
        with open('.env', 'w') as f:
            f.write(sample_env)
        print("❌ Please update .env file with your actual API keys and credentials")
        return False
    else:
        print("✅ .env file found")
        return True

def main():
    """Main setup function"""
    print("🚀 Setting up Medical Appointment Scheduler...")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Create sample forms
    create_sample_forms()
    
    # Verify files
    env_ok = verify_env_file()
    csv_ok = verify_patients_csv()
    
    print("\n" + "=" * 50)
    if env_ok and csv_ok:
        print("✅ Setup completed successfully!")
        print("\nTo run the application:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Update your .env file with real API keys")
        print("3. Run: streamlit run main.py")
    else:
        print("⚠️  Setup completed with warnings. Please address the issues above.")
    
    print("\n📋 Checklist:")
    print("□ Install dependencies: pip install -r requirements.txt")
    print("□ Update .env file with real API keys")
    print("□ Ensure patients.csv is in the project directory")
    print("□ Run: streamlit run main.py")

if __name__ == "__main__":
    main()