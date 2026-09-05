// attendance_location/static/src/js/checkedin_card.js
/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * Check-in card component that displays patient info
 * if the employee is currently checked in with a patient.
 */
export class CheckInPatientCard extends Component {
    static template = "attendance_location.CheckInPatientCard";

    setup() {
        this.employee = this.env.services.user.employee;
    }

    /**
     * Returns true if employee is checked in with a patient.
     */
    get isCheckedIn() {
        const emp = this.props.login_employee;
        return emp?.attendance_state === 'checked_in' && !!emp.patient_name;
    }

    /**
     * Returns the name of the currently assigned patient.
     */
    get patientName() {
        return this.props.login_employee.patient_name || "";
    }
}
