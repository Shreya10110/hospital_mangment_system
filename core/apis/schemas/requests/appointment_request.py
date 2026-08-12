"""Validated request body for multi-hospital doctor appointments."""
from core.models.domain import AppointmentCreate

class AppointmentBookingRequest(AppointmentCreate):
    pass
