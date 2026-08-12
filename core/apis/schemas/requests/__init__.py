from .user_request import UserSignUpRequest, UserLoginRequest
from .hospital_request import HospitalRegistrationRequest
from .doctor_request import DoctorRegistrationRequest
from .appointment_request import AppointmentBookingRequest
from .prescription_request import PrescriptionCreateRequest

__all__ = ["UserSignUpRequest", "UserLoginRequest", "HospitalRegistrationRequest", "DoctorRegistrationRequest", "AppointmentBookingRequest", "PrescriptionCreateRequest"]
