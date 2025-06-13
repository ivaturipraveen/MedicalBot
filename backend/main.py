from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base URL for the medical services API
MEDICAL_API_BASE_URL = "https://medical-assistant1.onrender.com"

# Models
class UserInput(BaseModel):
    message: str
    user_data: dict = {}

class DepartmentRequest(BaseModel):
    department: str

class ChatResponse(BaseModel):
    response: str
    action: str = None
    data: dict = None

# API client with logging
async def call_medical_api(endpoint: str, method: str = "GET", data: dict = None):
    async with httpx.AsyncClient() as client:
        url = f"{MEDICAL_API_BASE_URL}{endpoint}"
        print(f"Calling {method} {endpoint} with data: {data}")
        
        if method == "GET":
            response = await client.get(url, params=data)
        else:  # POST
            response = await client.post(url, json=data)
        
        print(f"Response from {endpoint}: status={response.status_code}")
        return response.status_code, response.json()

@app.post("/doctors")
async def get_doctors(request: DepartmentRequest):
    """
    Get doctors for a specific department
    """
    try:
        department = request.department.strip().capitalize()

        status_code, response = await call_medical_api(
            "/Bland/get-doctors",
            "POST",
            {"department": department}
        )

        print(f"Doctor API response: {response}")

        # 🟢 Use 'doctor_name' as per actual API response
        doctor_str = response.get("doctor_name", "")
        doctors_list = [d.strip() for d in doctor_str.split(",") if d.strip()]

        if status_code == 200 and doctors_list:
            return {"doctors": doctors_list, "department": department}

        raise HTTPException(status_code=404, detail="No doctors found for this department")

    except httpx.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        raise HTTPException(status_code=502, detail=f"Service unavailable: {http_err}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/chat")
async def chat(user_input: UserInput):
    message = user_input.message
    user_data = user_input.user_data
    
    # Initial state - no user data (first greeting)
    if not user_data.get("state"):
        return ChatResponse(
            response="Hello! I'm your medical assistant. I'm here to help you with appointments. Could you please share your name?",
            action="request_name",
            data={"state": "awaiting_name"}
        )
    
    # Handle different states and intents
    current_state = user_data.get("state")
    
    if current_state == "awaiting_name":
        # Get name from the message
        name = message.strip()
        
        return ChatResponse(
            response="Thanks! Now, please provide your date of birth.",
            action="request_dob",
            data={"state": "awaiting_dob", "name": name}
        )
    
    elif current_state == "awaiting_name_dob_phone":
        # For backward compatibility - redirect to new flow
        name = message.strip()
        
        return ChatResponse(
            response="Thanks! Now, please provide your date of birth.",
            action="request_dob",
            data={"state": "awaiting_dob", "name": name}
        )
    
    elif current_state == "awaiting_dob":
        name = user_data.get("name", "")
        dob = message.strip() # Take DOB as-is
        
        return ChatResponse(
            response="Thank you! Finally, please provide your phone number along with your country code(Eg:+91/+1).",
            action="request_phone",
            data={"state": "awaiting_phone", "name": name, "dob": dob}
        )
    
    elif current_state == "awaiting_dob_phone":
        # For backward compatibility
        name = user_data.get("name", "")
        dob = message.strip()
        
        return ChatResponse(
            response="Thank you! Now, please provide your phone number along with your country code(Eg:+91/+1).",
            action="request_phone",
            data={"state": "awaiting_phone", "name": name, "dob": dob}
        )
    
    elif current_state == "awaiting_phone":
        name = user_data.get("name", "")
        dob = user_data.get("dob", "")
        phone = message.strip() # Take phone as-is
        
        # For validation, just use phone and DOB as requested
        status_code, response = await call_medical_api(
            "/Bland/validate-users",
            "POST",
            {"phone": phone, "dob": dob}
        )
        print(status_code,response)
        
        if status_code == 200 and response["message"] == "Patient exists.":
            # User exists
            user_id = response.get("patient_id")
            # Extract first name from name if available
            name_parts = name.split(maxsplit=1)
            first_name = name_parts[0] if len(name_parts) > 0 else ""
            
            # Check for appointments using /Bland/get-appointment
            status_code, appointments = await call_medical_api(
                "/Bland/get-appointment",
                "POST",
                {"pid": user_id}
            )
            
            if status_code == 200 and appointments.get("appointment"):
                # Format appointment details
                doctor_name = appointments.get("doctor_name")
                department = appointments.get("department")
                date = appointments.get("Sdate")
                time = appointments.get("Stime")
                appointment_details = f"You have an appointment with  {doctor_name} from {department} department on {date} at {time}."
                
                return ChatResponse(
                    response=f"Welcome back, {first_name}! {appointment_details} Would you like to cancel this appointment or book a new one?",
                    action="show_existing_appointment",
                    data={"state": "authenticated", "user_id": user_id, "appointments": appointments, 
                          "doctor_name": doctor_name, "department": department, "date": date, "time": time, "phone": phone}
                )
            else:
                return ChatResponse(
                    response=f"Welcome back, {first_name}! You don't have any upcoming appointments. Would you like to book one?",
                    action="offer_booking",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
        elif status_code == 201 and response["message"]=="Patient does not exist.":
            # User doesn't exist, need to collect first name and last name for account creation
            name_parts = name.split(maxsplit=1)
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[1]
                
                # Create user directly if we have all information
                status_code, response = await call_medical_api(
                    "/Bland/create-user",
                    "POST",
                    {"first_name": first_name, "last_name": last_name, "dob": dob, "phone": phone}
                )
                
                if status_code == 201:
                    user_id = response.get("patient_id")
                    return ChatResponse(
                        response=f"Thank you, {first_name}! Your account has been created successfully. Would you like to book an appointment now?",
                        action="offer_booking",
                        data={"state": "authenticated", "user_id": user_id, "phone": phone}
                    )
                else:
                    return ChatResponse(
                        response="I need more information to create your account. What is your first name?",
                        action="request_first_name",
                        data={"state": "awaiting_first_name", "dob": dob, "phone": phone}
                    )
            else:
                return ChatResponse(
                    response="I couldn't find your records. Let me create a new account for you. What is your first name?",
                    action="request_first_name",
                    data={"state": "awaiting_first_name", "dob": dob, "phone": phone, "full_name": name}
                )
        else:
            # Error in API call - try again with all information
            return ChatResponse(
                response="I'm having trouble verifying your information. Let's try again with just your phone number and date of birth.",
                action="request_phone",
                data={"state": "awaiting_phone", "name": name, "dob": dob}
            )
    
    elif current_state == "awaiting_first_name":
        first_name = message.strip()
        dob = user_data.get("dob", "")
        phone = user_data.get("phone", "")
        full_name = user_data.get("full_name", "")
        
        # Try to extract last name from full name if available
        if full_name and " " in full_name:
            name_parts = full_name.split(maxsplit=1)
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            return ChatResponse(
                response=f"Thank you! Is '{last_name}' your last name? (yes/no)",
                action="confirm_last_name",
                data={"state": "awaiting_last_name_confirmation", "first_name": first_name, "dob": dob, "phone": phone, "last_name": last_name}
            )
        else:
            return ChatResponse(
                response=f"Thank you! What is your last name?",
                action="request_last_name",
                data={"state": "awaiting_last_name", "first_name": first_name, "dob": dob, "phone": phone}
            )
    
    elif current_state == "awaiting_last_name_confirmation":
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        dob = user_data.get("dob", "")
        phone = user_data.get("phone", "")
        
        if "yes" in message.lower() or "correct" in message.lower() or "right" in message.lower():
            # Create user using /Bland/create-user endpoint - passing data directly
            status_code, response = await call_medical_api(
                "/Bland/create-user",
                "POST",
                {"first_name": first_name, "last_name": last_name, "dob": dob, "phone": phone}
            )
            
            if status_code == 201:
                user_id = response.get("patient_id")
                return ChatResponse(
                    response=f"Thank you, {first_name}! Your account has been created successfully. Would you like to book an appointment now?",
                    action="offer_booking",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
            else:
                return ChatResponse(
                    response="I'm sorry, there was an issue creating your account. Please try again later or contact our support team.",
                    action="error",
                    data={"state": "error", "phone": phone}
                )
        else:
            return ChatResponse(
                response="What is your last name?",
                action="request_last_name",
                data={"state": "awaiting_last_name", "first_name": first_name, "dob": dob, "phone": phone}
            )
    
    elif current_state == "awaiting_last_name":
        last_name = message.strip()
        first_name = user_data.get("first_name", "")
        dob = user_data.get("dob", "")
        phone = user_data.get("phone", "")
        
        # Create user using /Bland/create-user endpoint - passing data directly
        status_code, response = await call_medical_api(
            "/Bland/create-user",
            "POST",
            {"first_name": first_name, "last_name": last_name, "dob": dob, "phone": phone}
        )
        
        if status_code == 201:
            user_id = response.get("patient_id")
            return ChatResponse(
                response=f"Thank you, {first_name}! Your account has been created successfully. Would you like to book an appointment now?",
                action="offer_booking",
                data={"state": "authenticated", "user_id": user_id, "phone": phone}
            )
        else:
            return ChatResponse(
                response="I'm sorry, there was an issue creating your account. Please try again later or contact our support team.",
                action="error",
                data={"state": "error", "phone": phone}
            )
    
    elif current_state == "authenticated":
        user_id = user_data.get("user_id")
        phone = user_data.get("phone", "")
        
        # Handle appointment booking
        if "book" in message.lower() or "appointment" in message.lower() or "yes" in message.lower():
            departments = ["Cardiology", "Neurology", "General Physician"]
            return ChatResponse(
                response="What department would you like to book an appointment with?",
                action="show_options",
                data={"state": "awaiting_department", "user_id": user_id, "phone": phone, 
                      "options": departments}
            )
        
        # Handle "No" response to terminate conversation
        elif "no" in message.lower():
            return ChatResponse(
                response="Thank you for using our Medical Appointment Booking System. Have a great day!",
                action="conversation_end",
                data={"state": "conversation_ended"}
            )
        
        # Handle appointment checking
        elif "check" in message.lower():
            status_code, appointments = await call_medical_api(
                "/Bland/get-appointment",
                "POST",
                {"pid": user_id}
            )
            
            if status_code == 200 and appointments.get("appointment"):
                doctor_name = appointments.get("doctor_name")
                department = appointments.get("department")
                date = appointments.get("Sdate")
                time = appointments.get("Stime")
                
                return ChatResponse(
                    response=f"You have an appointment with  {doctor_name} from {department} department on {date} at {time}.",
                    action="show_existing_appointment",
                    data={"state": "authenticated", "user_id": user_id, "appointments": appointments, 
                          "doctor_name": doctor_name, "department": department, "date": date, "time": time, "phone": phone}
                )
            else:
                return ChatResponse(
                    response="You don't have any upcoming appointments. Would you like to book one now?",
                    action="offer_booking",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
        
        # Handle appointment cancellation
        elif "cancel" in message.lower():
            status_code, appointments = await call_medical_api(
                "/Bland/get-appointment",
                "POST",
                {"pid": user_id}
            )
            
            if status_code == 200 and appointments.get("appointment"):
                doctor_name = appointments.get("doctor_name")
                department = appointments.get("department")
                date = appointments.get("Sdate")
                time = appointments.get("Stime")
                
                return ChatResponse(
                    response=f"You have an appointment with  {doctor_name} from {department} department on {date} at {time}. Would you like to cancel this appointment? Please confirm by saying 'yes' or 'no'.",
                    action="confirm_cancellation",
                    data={"state": "awaiting_cancellation_confirmation", "user_id": user_id, 
                          "doctor_name": doctor_name, "department": department, 
                          "date": date, "time": time, "phone": phone}
                )
            else:
                return ChatResponse(
                    response="You don't have any appointments to cancel. Would you like to book an appointment instead?",
                    action="offer_booking",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
        
        else:
            return ChatResponse(
                response="How can I assist you today? You can book a new appointment, check your existing appointments, or cancel an appointment.",
                action="offer_options",
                data={"state": "authenticated", "user_id": user_id, "phone": phone}
            )
    
    elif current_state == "awaiting_department":
        department = message.strip()
        phone = user_data.get("phone", "")
        
        # Get doctors in the selected department
        status_code, response = await call_medical_api(
            "/Bland/get-doctors",
            "POST",
            {"department": department}
        )
        
        if status_code == 200 :
            doctors = response["doctor_name"]
            doctors_list = doctors.split(", ")
            print(f"Retrieved doctors for {department}: {doctors_list}")
            
            return ChatResponse(
                response=f"We have the following doctors in {department}. Which doctor would you like to book an appointment with?",
                action="show_options",
                data={"state": "awaiting_doctor", "user_id": user_data.get("user_id"),
                      "department": department, "phone": phone,
                      "doctors": doctors_list,
                      "options": doctors_list}
            )
        else:
            print(f"Failed to get doctors for {department}. Status code: {status_code}, Response: {response}")
            return ChatResponse(
                response="I couldn't find information about that department. Please choose from Cardiology, Neurology, or General Physician.",
                action="request_department",
                data={"state": "awaiting_department", "user_id": user_data.get("user_id"), "phone": phone}
            )
    
    elif current_state == "awaiting_doctor":
        doctor_name = message.strip()
        department = user_data.get("department")
        phone = user_data.get("phone", "")
        
        # Get available dates for the selected doctor
        status_code, response = await call_medical_api(
            "/Bland/fetch-date",
            "POST",
            {"d_name": doctor_name}
        )
        
        if status_code == 200 and "available_dates" in response:
            available_dates = response.get("available_dates")
            matched_doctor = response.get("doctor_name")
            
            if available_dates:
                return ChatResponse(
                    response=f"{matched_doctor} is available on the following dates. Please select a date for your appointment.",
                    action="show_options",
                    data={"state": "awaiting_date", "user_id": user_data.get("user_id"), 
                          "doctor_name": matched_doctor, "department": department,
                          "available_dates": available_dates, "phone": phone,
                          "options": available_dates}
                )
            else:
                # Try to get the doctors list again to show as options
                doctors_status, doctors_response = await call_medical_api(
                    "/Bland/get-doctors",
                    "POST",
                    {"department": department}
                )
                
                doctors_list = []
                if doctors_status == 200 and "response" in doctors_response:
                    doctors = doctors_response.get("response")
                    doctors_list = doctors.split(", ")
                
                return ChatResponse(
                    response=f"I'm sorry, {matched_doctor} doesn't have any available appointments in the next 7 days. Would you like to try another doctor?",
                    action="show_options",
                    data={"state": "awaiting_doctor", "user_id": user_data.get("user_id"), 
                          "department": department, "phone": phone,
                          "options": doctors_list}
                )
        else:
            # Try to get the doctors list again to show as options
            doctors_status, doctors_response = await call_medical_api(
                "/Bland/get-doctors",
                "POST",
                {"department": department}
            )
            
            doctors_list = []
            if doctors_status == 200 and "response" in doctors_response:
                doctors = doctors_response.get("response")
                doctors_list = doctors.split(", ")
            
            return ChatResponse(
                response="I couldn't find that doctor. Please check the name and try again.",
                action="show_options",
                data={"state": "awaiting_doctor", "user_id": user_data.get("user_id"), 
                      "department": department, "phone": phone,
                      "options": doctors_list}
            )
    
    elif current_state == "awaiting_date":
        selected_date = message.strip()
        doctor_name = user_data.get("doctor_name")
        department = user_data.get("department")
        phone = user_data.get("phone", "")
        
        # Pass directly to API without format validation
        status_code, response = await call_medical_api(
            "/Bland/time-slot",
            "POST",
            {"d_name": doctor_name, "S_date": selected_date}
        )
        
        if status_code == 200 and "available_slots" in response:
            available_slots = response.get("available_slots")
            
            if available_slots:
                return ChatResponse(
                    response=f"{doctor_name} has the following available time slots on {selected_date}. Please select a time.",
                    action="show_options",
                    data={"state": "awaiting_time", "user_id": user_data.get("user_id"), 
                          "doctor_name": doctor_name, "department": department,
                          "selected_date": selected_date, "available_slots": available_slots, "phone": phone,
                          "options": available_slots}
                )
            else:
                return ChatResponse(
                    response=f"I'm sorry, {doctor_name} doesn't have any available time slots on {selected_date}. Please select another date.",
                    action="show_options",
                    data={"state": "awaiting_date", "user_id": user_data.get("user_id"), 
                          "doctor_name": doctor_name, "department": department,
                          "available_dates": user_data.get("available_dates", []), "phone": phone,
                          "options": user_data.get("available_dates", [])}
                )
        else:
            return ChatResponse(
                response=f"I couldn't retrieve available time slots for that date. Please try a different date.",
                action="show_options",
                data={"state": "awaiting_date", "user_id": user_data.get("user_id"), 
                      "doctor_name": doctor_name, "department": department,
                      "available_dates": user_data.get("available_dates", []), "phone": phone,
                      "options": user_data.get("available_dates", [])}
            )
    
    elif current_state == "awaiting_time":
        selected_time = message.strip()
        doctor_name = user_data.get("doctor_name")
        department = user_data.get("department")
        selected_date = user_data.get("selected_date")
        user_id = user_data.get("user_id")
        phone = user_data.get("phone", "")
        
        # Book the appointment with the backend directly - pass input as-is
        status_code, response = await call_medical_api(
            "/Bland/book-appointment",
            "POST",
            {"dname": doctor_name, "date": selected_date, "sslot": selected_time, 
             "pid": user_id, "phone": phone}
        )
        
        if status_code == 200:
            appointment_id = response.get("appointment_id")
            formatted_date = response.get("appointment_date")
            formatted_time = response.get("appointment_time")
            
            return ChatResponse(
                response=f"Great! Your appointment with  {doctor_name} has been booked for {formatted_date} at {formatted_time}. You will receive a confirmation text message. Is there anything else I can help you with?",
                action="confirm_booking",
                data={"state": "authenticated", "user_id": user_id, "phone": phone,
                      "appointment_id": appointment_id, "doctor_name": doctor_name,
                      "department": department, "date": formatted_date, "time": formatted_time}
            )
        else:
            error_message = response.get("detail", "Unknown error")
            return ChatResponse(
                response=f"I'm sorry, there was an issue booking your appointment: {error_message}. Please try again.",
                action="error_booking",
                data={"state": "awaiting_time", "user_id": user_id, "phone": phone,
                      "doctor_name": doctor_name, "department": department,
                      "selected_date": selected_date, "selected_time": selected_time}
            )
    
    elif current_state == "awaiting_cancellation_confirmation":
        user_id = user_data.get("user_id")
        doctor_name = user_data.get("doctor_name")
        department = user_data.get("department")
        date = user_data.get("date")
        time = user_data.get("time")
        phone = user_data.get("phone", "")
        
        # Cancel the appointment directly through the API
        if "yes" in message.lower() or "confirm" in message.lower():
            status_code, response = await call_medical_api(
                "/Bland/cancel-appointment",
                "POST",
                {"doctor_name": doctor_name, "department": department, 
                 "date": date, "time": time, "pid": user_id}
            )
            
            if status_code == 200:
                return ChatResponse(
                    response="Your appointment has been successfully cancelled. Would you like to book a new appointment?",
                    action="offer_booking",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
            else:
                error_message = response.get("detail", "Unknown error")
                return ChatResponse(
                    response=f"I'm sorry, there was an issue cancelling your appointment: {error_message}. Please try again later or contact our support team.",
                    action="error_cancellation",
                    data={"state": "authenticated", "user_id": user_id, "phone": phone}
                )
        else:
            return ChatResponse(
                response="Your appointment has not been cancelled. How else can I assist you today?",
                action="offer_options",
                data={"state": "authenticated", "user_id": user_data.get("user_id"), "phone": user_data.get("phone", "")}
            )
    
    # Handle conversation_ended state
    elif current_state == "conversation_ended":
        # If user sends another message after conversation ended, restart
        return ChatResponse(
            response="Hello! I'm your medical assistant. I'm here to help you with appointments. Could you please share your name?",
            action="request_name",
            data={"state": "awaiting_name"}
        )
    
    # Default response
    return ChatResponse(
        response="I'm not sure how to help with that. Can you please rephrase or tell me if you'd like to book, check, or cancel an appointment?",
        action="request_clarification",
        data={"state": user_data.get("state", "unknown"), "phone": user_data.get("phone", "")}
    )

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    print("Starting Medical Appointment Booking System...")
    print("API calls to the medical backend will be logged in the terminal.")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  
