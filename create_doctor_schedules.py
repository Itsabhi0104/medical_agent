import pandas as pd
from datetime import datetime, timedelta

# Create sample doctor schedules
def create_doctor_schedules():
    # Generate dates for next 30 days
    start_date = datetime.now().date()
    dates = [start_date + timedelta(days=i) for i in range(30)]
    
    # Dr. Smith schedule
    dr_smith_schedule = []
    for date in dates:
        day_name = date.strftime('%A')
        if day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            slots = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
            for slot in slots:
                dr_smith_schedule.append({
                    'doctor': 'Dr. Smith',
                    'date': date.strftime('%Y-%m-%d'),
                    'day': day_name,
                    'time_slot': slot,
                    'duration': '30min',
                    'available': True
                })
    
    # Dr. Johnson schedule
    dr_johnson_schedule = []
    for date in dates:
        day_name = date.strftime('%A')
        if day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            slots = ['10:00', '11:00', '14:00', '15:00', '16:00']
            for slot in slots:
                dr_johnson_schedule.append({
                    'doctor': 'Dr. Johnson',
                    'date': date.strftime('%Y-%m-%d'),
                    'day': day_name,
                    'time_slot': slot,
                    'duration': '30min',
                    'available': True
                })
    
    # Combine schedules
    all_schedules = dr_smith_schedule + dr_johnson_schedule
    
    # Create DataFrame and save to Excel
    df = pd.DataFrame(all_schedules)
    df.to_excel('doctor_schedules.xlsx', index=False)
    print("Doctor schedules created successfully!")

if __name__ == "__main__":
    create_doctor_schedules()