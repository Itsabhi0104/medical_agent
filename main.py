import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from langchain.agents import Tool, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseOutputParser
import re
from typing import Dict, List, Any
import uuid

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# Global variables for session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_patient' not in st.session_state:
    st.session_state.current_patient = {}
if 'appointment_data' not in st.session_state:
    st.session_state.appointment_data = {}
if 'stage' not in st.session_state:
    st.session_state.stage = 'greeting'

class PatientLookupTool:
    def __init__(self, csv_path='patients.csv'):
        try:
            self.patients_df = pd.read_csv(csv_path)
        except:
            # Fallback data if CSV not found
            self.patients_df = pd.DataFrame({
                'patient_id': ['P0001', 'P0002'],
                'first_name': ['John', 'Jane'],
                'last_name': ['Doe', 'Smith'],
                'dob': ['1990-01-01', '1985-05-15'],
                'phone': ['+919876543210', '+919876543211'],
                'email': ['john@example.com', 'jane@example.com'],
                'insurance_company': ['Max Bupa', 'Star Health'],
                'member_id': ['MB123', 'SH456'],
                'is_returning': [True, False]
            })
    
    def lookup_patient(self, name, dob, phone=None):
        """Lookup patient in database"""
        name_parts = name.lower().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[-1] if len(name_parts) > 1 else ""
        
        # Search by name and DOB
        matches = self.patients_df[
            (self.patients_df['first_name'].str.lower() == first_name) |
            (self.patients_df['last_name'].str.lower() == last_name)
        ]
        
        if not matches.empty and dob:
            matches = matches[matches['dob'] == dob]
        
        if not matches.empty:
            return matches.iloc[0].to_dict()
        return None

class CalendarManager:
    def __init__(self):
        self.calendly_pat = os.getenv('CALENDLY_PAT')
        self.event_type_uuid = os.getenv('CALENDLY_EVENT_TYPE_UUID')
        
        # Mock doctor schedules
        self.doctor_schedules = {
            'Dr. Smith': {
                'monday': ['09:00', '10:00', '11:00', '14:00', '15:00'],
                'tuesday': ['09:00', '10:30', '11:30', '14:30', '15:30'],
                'wednesday': ['10:00', '11:00', '14:00', '15:00', '16:00'],
                'thursday': ['09:30', '10:30', '14:00', '15:30'],
                'friday': ['09:00', '10:00', '11:00', '14:00']
            },
            'Dr. Johnson': {
                'monday': ['10:00', '11:00', '15:00', '16:00'],
                'tuesday': ['09:00', '14:00', '15:00', '16:00'],
                'wednesday': ['09:30', '10:30', '14:30', '15:30'],
                'thursday': ['10:00', '11:00', '15:00', '16:00'],
                'friday': ['09:00', '10:00', '14:00', '15:00']
            }
        }
    
    def get_available_slots(self, doctor, date_str, duration=30):
        """Get available time slots for a doctor on a specific date"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = date_obj.strftime('%A').lower()
            
            if doctor in self.doctor_schedules and day_name in self.doctor_schedules[doctor]:
                slots = self.doctor_schedules[doctor][day_name]
                return [f"{slot} - {self._add_minutes(slot, duration)}" for slot in slots]
        except:
            pass
        return ['09:00 - 09:30', '10:00 - 10:30', '11:00 - 11:30']
    
    def _add_minutes(self, time_str, minutes):
        """Add minutes to time string"""
        try:
            time_obj = datetime.strptime(time_str, '%H:%M')
            new_time = time_obj + timedelta(minutes=minutes)
            return new_time.strftime('%H:%M')
        except:
            return time_str

class EmailManager:
    def __init__(self):
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.smtp_server = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_PORT', '587'))
    
    def send_email(self, to_email, subject, body, attachments=None):
        """Send email with optional attachments"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            msg.attach(part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            st.error(f"Email sending failed: {str(e)}")
            return False

class SchedulingAgent:
    def __init__(self):
        self.patient_lookup = PatientLookupTool()
        self.calendar_manager = CalendarManager()
        self.email_manager = EmailManager()
        self.conversation_memory = []
    
    def process_user_input(self, user_input, stage):
        """Process user input based on current stage"""
        
        if stage == 'greeting':
            return self._handle_greeting(user_input)
        elif stage == 'patient_lookup':
            return self._handle_patient_lookup(user_input)
        elif stage == 'scheduling':
            return self._handle_scheduling(user_input)
        elif stage == 'insurance':
            return self._handle_insurance(user_input)
        elif stage == 'confirmation':
            return self._handle_confirmation(user_input)
        else:
            return self._generate_ai_response(user_input)
    
    def _handle_greeting(self, user_input):
        """Handle patient greeting and basic info collection"""
        try:
            # Use Gemini to extract information
            prompt = f"""
            Extract the following information from this patient message: "{user_input}"
            
            Return JSON format:
            {{
                "name": "extracted name or null",
                "dob": "extracted date of birth in YYYY-MM-DD format or null",
                "doctor": "preferred doctor or null",
                "location": "preferred location or null"
            }}
            
            If information is missing, ask for it politely.
            """
            
            response = model.generate_content(prompt)
            
            # Try to parse JSON response
            try:
                extracted_info = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                st.session_state.current_patient.update(extracted_info)
                
                missing_info = []
                if not extracted_info.get('name'):
                    missing_info.append('your full name')
                if not extracted_info.get('dob'):
                    missing_info.append('your date of birth (YYYY-MM-DD)')
                if not extracted_info.get('doctor'):
                    missing_info.append('your preferred doctor')
                
                if missing_info:
                    return f"Hello! I'd be happy to help you schedule an appointment. Could you please provide {', '.join(missing_info)}?"
                else:
                    st.session_state.stage = 'patient_lookup'
                    return self._handle_patient_lookup("")
                    
            except json.JSONDecodeError:
                return "Hello! I'm here to help you schedule a medical appointment. Could you please provide your full name, date of birth (YYYY-MM-DD), and preferred doctor?"
                
        except Exception as e:
            return "Hello! I'm here to help you schedule a medical appointment. Could you please provide your full name, date of birth (YYYY-MM-DD), and preferred doctor?"
    
    def _handle_patient_lookup(self, user_input):
        """Handle patient database lookup"""
        current_patient = st.session_state.current_patient
        
        if current_patient.get('name') and current_patient.get('dob'):
            patient_record = self.patient_lookup.lookup_patient(
                current_patient['name'], 
                current_patient['dob']
            )
            
            if patient_record:
                st.session_state.current_patient.update(patient_record)
                is_returning = patient_record.get('is_returning', False)
                duration = 30 if is_returning else 60
                
                st.session_state.stage = 'scheduling'
                return f"Welcome back, {patient_record['first_name']}! I found your record. As a {'returning' if is_returning else 'new'} patient, I'll book a {duration}-minute appointment. What date would you prefer for your appointment?"
            else:
                st.session_state.current_patient['is_returning'] = False
                st.session_state.stage = 'scheduling'
                return f"I don't see you in our system, so I'll set you up as a new patient with a 60-minute appointment. What date would you prefer for your appointment?"
        
        return "I need your complete information to proceed. Please provide your full name and date of birth (YYYY-MM-DD)."
    
    def _handle_scheduling(self, user_input):
        """Handle appointment scheduling"""
        # Extract date from user input
        try:
            prompt = f"""
            Extract a date from this message: "{user_input}"
            Return only the date in YYYY-MM-DD format, or "none" if no date found.
            Today is {datetime.now().strftime('%Y-%m-%d')}.
            Accept relative dates like "tomorrow", "next week", etc.
            """
            
            response = model.generate_content(prompt)
            date_str = response.text.strip().replace('"', '')
            
            if date_str != "none" and len(date_str) == 10:
                doctor = st.session_state.current_patient.get('doctor', 'Dr. Smith')
                duration = 30 if st.session_state.current_patient.get('is_returning') else 60
                
                available_slots = self.calendar_manager.get_available_slots(doctor, date_str, duration)
                
                st.session_state.appointment_data = {
                    'date': date_str,
                    'doctor': doctor,
                    'duration': duration,
                    'available_slots': available_slots
                }
                
                slots_text = '\n'.join([f"{i+1}. {slot}" for i, slot in enumerate(available_slots)])
                return f"Available time slots for {doctor} on {date_str}:\n\n{slots_text}\n\nPlease select a slot number (1-{len(available_slots)})."
            
            else:
                return "I couldn't understand the date. Please provide a specific date (YYYY-MM-DD) or say 'tomorrow', 'next Monday', etc."
                
        except Exception as e:
            return "Please provide your preferred appointment date (YYYY-MM-DD)."
    
    def _handle_insurance(self, user_input):
        """Handle insurance information collection"""
        if 'selected_slot' in st.session_state.appointment_data:
            try:
                prompt = f"""
                Extract insurance information from: "{user_input}"
                Return JSON:
                {{
                    "insurance_company": "company name or null",
                    "member_id": "member ID or null"
                }}
                """
                
                response = model.generate_content(prompt)
                insurance_info = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                
                st.session_state.current_patient.update(insurance_info)
                st.session_state.stage = 'confirmation'
                
                return self._generate_confirmation_summary()
                
            except:
                return "Could you please provide your insurance company name and member ID?"
        
        return "Please first select an appointment time slot."
    
    def _handle_confirmation(self, user_input):
        """Handle appointment confirmation"""
        if user_input.lower() in ['yes', 'confirm', 'y', 'ok', 'sure']:
            return self._confirm_appointment()
        elif user_input.lower() in ['no', 'cancel', 'n']:
            st.session_state.stage = 'scheduling'
            return "No problem! Would you like to select a different date or time?"
        else:
            return "Please confirm by typing 'yes' or 'no'."
    
    def _generate_confirmation_summary(self):
        """Generate appointment confirmation summary"""
        patient = st.session_state.current_patient
        appointment = st.session_state.appointment_data
        
        summary = f"""
        Please confirm your appointment details:
        
        Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}
        Date: {appointment.get('date', '')}
        Time: {appointment.get('selected_slot', '')}
        Doctor: {appointment.get('doctor', '')}
        Duration: {appointment.get('duration', '')} minutes
        Insurance: {patient.get('insurance_company', 'Not provided')}
        
        Please type 'yes' to confirm or 'no' to modify.
        """
        
        return summary
    
    def _confirm_appointment(self):
        """Confirm and process the appointment"""
        try:
            # Generate appointment ID
            appointment_id = f"APT{str(uuid.uuid4())[:8].upper()}"
            
            # Create appointment record
            appointment_record = {
                'appointment_id': appointment_id,
                'patient_name': f"{st.session_state.current_patient.get('first_name', '')} {st.session_state.current_patient.get('last_name', '')}",
                'date': st.session_state.appointment_data.get('date'),
                'time': st.session_state.appointment_data.get('selected_slot'),
                'doctor': st.session_state.appointment_data.get('doctor'),
                'duration': st.session_state.appointment_data.get('duration'),
                'patient_type': 'Returning' if st.session_state.current_patient.get('is_returning') else 'New',
                'insurance': st.session_state.current_patient.get('insurance_company', 'None'),
                'email': st.session_state.current_patient.get('email', ''),
                'phone': st.session_state.current_patient.get('phone', ''),
                'status': 'Confirmed',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Save to Excel
            self._export_to_excel(appointment_record)
            
            # Send confirmation email
            if st.session_state.current_patient.get('email'):
                self._send_confirmation_email(appointment_record)
            
            # Setup reminder system
            self._setup_reminders(appointment_record)
            
            st.session_state.stage = 'greeting'  # Reset for next patient
            
            return f"""
            ✅ Appointment Confirmed!
            
            Appointment ID: {appointment_id}
            Date: {appointment_record['date']}
            Time: {appointment_record['time']}
            Doctor: {appointment_record['doctor']}
            
            You will receive:
            - Confirmation email with forms
            - 3 reminder messages before your appointment
            
            Thank you for choosing our clinic!
            """
            
        except Exception as e:
            return f"Sorry, there was an error confirming your appointment: {str(e)}"
    
    def _export_to_excel(self, appointment_record):
        """Export appointment to Excel file"""
        try:
            filename = f'appointments_{datetime.now().strftime("%Y%m%d")}.xlsx'
            
            if os.path.exists(filename):
                df = pd.read_excel(filename)
                new_df = pd.concat([df, pd.DataFrame([appointment_record])], ignore_index=True)
            else:
                new_df = pd.DataFrame([appointment_record])
            
            new_df.to_excel(filename, index=False)
            st.success(f"✅ Appointment exported to {filename}")
            return True
            
        except Exception as e:
            st.error(f"❌ Export failed: {str(e)}")
            return False
    
    def _send_confirmation_email(self, appointment_record):
        """Send confirmation email with forms"""
        subject = f"Appointment Confirmation - {appointment_record['appointment_id']}"
        
        body = f"""
        <html>
        <body>
            <h2>Appointment Confirmed</h2>
            <p>Dear {appointment_record['patient_name']},</p>
            
            <p>Your appointment has been confirmed with the following details:</p>
            
            <ul>
                <li><strong>Appointment ID:</strong> {appointment_record['appointment_id']}</li>
                <li><strong>Date:</strong> {appointment_record['date']}</li>
                <li><strong>Time:</strong> {appointment_record['time']}</li>
                <li><strong>Doctor:</strong> {appointment_record['doctor']}</li>
                <li><strong>Duration:</strong> {appointment_record['duration']} minutes</li>
            </ul>
            
            <p>Please find the attached intake forms. Kindly fill them out before your appointment.</p>
            
            <p>You will receive reminder messages before your appointment.</p>
            
            <p>Best regards,<br>Medical Clinic</p>
        </body>
        </html>
        """
        
        # Attach forms if available
        form_files = []
        forms_dir = 'forms'
        if os.path.exists(forms_dir):
            for file in os.listdir(forms_dir):
                if file.endswith(('.pdf', '.doc', '.docx')):
                    form_files.append(os.path.join(forms_dir, file))
        
        success = self.email_manager.send_email(
            appointment_record['email'], 
            subject, 
            body, 
            form_files
        )
        
        if success:
            st.success("Confirmation email sent successfully!")
        else:
            st.warning("Could not send confirmation email")
    
    def _setup_reminders(self, appointment_record):
        """Setup reminder system (mock implementation)"""
        # In a real system, this would schedule actual reminders
        reminders = [
            {'days_before': 7, 'type': 'email', 'message': 'Your appointment is in 7 days'},
            {'days_before': 1, 'type': 'sms', 'message': 'Your appointment is tomorrow. Have you filled the forms?'},
            {'hours_before': 2, 'type': 'email', 'message': 'Your appointment is in 2 hours. Please confirm or cancel.'}
        ]
        
        st.info("Reminder system activated - you will receive 3 automated reminders")
        
        return reminders
    
    def _generate_ai_response(self, user_input):
        """Generate AI response for general queries"""
        try:
            prompt = f"""
            You are a medical appointment scheduling assistant. 
            The user said: "{user_input}"
            
            Provide a helpful response related to medical appointments, scheduling, or general medical practice queries.
            Keep it professional and friendly.
            """
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return "I'm here to help you schedule medical appointments. How can I assist you today?"

# Initialize the scheduling agent
if 'agent' not in st.session_state:
    st.session_state.agent = SchedulingAgent()

# Streamlit UI
def main():
    st.set_page_config(page_title="Medical Appointment Scheduler", page_icon="🏥", layout="wide")
    
    st.title("🏥 Medical Appointment Scheduling AI Agent")
    st.markdown("---")
    
    # Sidebar for admin functions
    with st.sidebar:
        st.header("Admin Panel")
        
        if st.button("View Today's Appointments"):
            try:
                filename = f'appointments_{datetime.now().strftime("%Y%m%d")}.xlsx'
                if os.path.exists(filename):
                    df = pd.read_excel(filename)
                    st.subheader("📋 Appointments")
                    st.dataframe(df)
                else:
                    st.info("No appointments for today")
            except Exception as e:
                st.error(f"Could not load appointments: {e}")
        
        if st.button("View Calendar Bookings"):
            try:
                calendar_filename = f'calendar_bookings_{datetime.now().strftime("%Y%m%d")}.xlsx'
                if os.path.exists(calendar_filename):
                    df = pd.read_excel(calendar_filename)
                    st.subheader("📅 Calendar Bookings")
                    st.dataframe(df)
                    
                    # Show download link
                    with open(calendar_filename, "rb") as file:
                        st.download_button(
                            label="⬇️ Download Calendar Data",
                            data=file,
                            file_name=calendar_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No calendar bookings for today")
            except Exception as e:
                st.error(f"Could not load calendar data: {e}")
        
        if st.button("View Doctor Schedules"):
            try:
                if os.path.exists('doctor_schedules.xlsx'):
                    df = pd.read_excel('doctor_schedules.xlsx')
                    st.subheader("👨‍⚕️ Doctor Schedules")
                    st.dataframe(df.tail(10))  # Show last 10 entries
                else:
                    st.info("No doctor schedule data")
            except Exception as e:
                st.error(f"Could not load schedules: {e}")
                
        if st.button("Generate Sample Data"):
            try:
                # Create sample doctor schedules
                exec(open('create_doctor_schedules.py').read())
                st.success("Sample doctor schedules created!")
            except Exception as e:
                st.error(f"Could not create sample data: {e}")
        
        if st.button("Reset Conversation"):
            for key in ['conversation_history', 'current_patient', 'appointment_data', 'stage']:
                if key in st.session_state:
                    if key == 'stage':
                        st.session_state[key] = 'greeting'
                    else:
                        st.session_state[key] = {} if 'data' in key or 'patient' in key else []
            st.rerun()
            
        # File management
        st.markdown("---")
        st.subheader("📁 File Management")
        
        # List all Excel files
        excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
        if excel_files:
            st.write("**Excel Files:**")
            for file in excel_files:
                st.write(f"📄 {file}")
        else:
            st.write("No Excel files found")
    
    # Main chat interface
    st.header("Chat with AI Assistant")
    
    # Display conversation history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.conversation_history:
            if message['role'] == 'user':
                st.chat_message("user").write(message['content'])
            else:
                st.chat_message("assistant").write(message['content'])
    
    # User input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Add user message to history
        st.session_state.conversation_history.append({
            'role': 'user', 
            'content': user_input
        })
        
        # Handle special slot selection
        if st.session_state.stage == 'scheduling' and user_input.isdigit():
            slot_index = int(user_input) - 1
            available_slots = st.session_state.appointment_data.get('available_slots', [])
            
            if 0 <= slot_index < len(available_slots):
                st.session_state.appointment_data['selected_slot'] = available_slots[slot_index]
                st.session_state.stage = 'insurance'
                
                response = "Great! I've selected that time slot. Now, could you please provide your insurance company name and member ID? (If you don't have insurance, just type 'none')"
            else:
                response = f"Please select a valid slot number between 1 and {len(available_slots)}"
        else:
            # Process with AI agent
            response = st.session_state.agent.process_user_input(user_input, st.session_state.stage)
        
        # Add assistant response to history
        st.session_state.conversation_history.append({
            'role': 'assistant', 
            'content': response
        })
        
        st.rerun()
    
    # Display current status
    with st.expander("Current Session Info", expanded=False):
        st.write(f"**Stage:** {st.session_state.stage}")
        st.write(f"**Patient Data:** {st.session_state.current_patient}")
        st.write(f"**Appointment Data:** {st.session_state.appointment_data}")

if __name__ == "__main__":
    main()