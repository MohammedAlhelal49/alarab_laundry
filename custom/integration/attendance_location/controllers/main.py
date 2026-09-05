from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class HrAttendanceController(http.Controller):

    @http.route('/hr_dashboard_attendance/update_attendance_patient', type="json", auth="user")
    def update_attendance(self, patient_id=None, latitude=None, longitude=None):
        """
        Route to handle attendance check-in/check-out linked with patient and location data.
        """
        _logger.info("Request received: patient_id=%s, latitude=%s, longitude=%s", patient_id, latitude, longitude)

        # Load employee
        employee = request.env.user.employee_id
        if not employee:
            _logger.error("No employee associated with the user.")
            return {'error': 'Employee not found for the current user.'}

        # Load client IP
        client_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR') or request.httprequest.remote_addr
        _logger.info("Detected Client IP: %s", client_ip)

        # Delegate logic to model
        try:
            result = request.env['hr.attendance'].sudo().process_attendance_with_patient(
                patient_id=patient_id,
                latitude=latitude,
                longitude=longitude,
                client_ip=client_ip,
            )
            _logger.info("Attendance processed successfully: %s", result)
            return result
        except Exception as e:
            _logger.exception("Attendance processing failed.")
            return {'error': f"An unexpected error occurred: {str(e)}"}
