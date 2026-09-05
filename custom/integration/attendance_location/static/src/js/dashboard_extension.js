/** @odoo-module **/

import { HrDashboard } from '@hrms_dashboard/js/dashboard';
import { patch } from '@web/core/utils/patch';
import { onMounted, useState } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { _t } from '@web/core/l10n/translation';

// Utility: Get user geolocation from browser
function getLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            return reject(new Error('Geolocation not supported.'));
        }
        navigator.geolocation.getCurrentPosition(
            position => resolve(position),
            error => reject(error),
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    });
}

// Extend HrDashboard to handle patient-aware attendance
patch(HrDashboard.prototype, {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.effect = useService('effect');

        this.state = useState({
            ...this.state,
            selectedPatientId: null,
            patients: [],
            patientsReady: false,
        });

        onMounted(async () => {
            // Load assigned patients for the current employee
            this.state.patients = await this.orm.call('hr.employee', 'fetch_patients', []);
            this.state.patientsReady = true;

            // Show banner if already checked in
            if (
                this.state.login_employee.attendance_state === 'checked_in' &&
                this.state.login_employee.patient_name
            ) {
                this._displayCheckInBanner(this.state.login_employee.patient_name);
            }
        });
    },

    // Trigger attendance with location + optional patient
    async attendance_sign_in_out() {
        if (!this.state.patientsReady) {
            this.notification.add(_t('Loading patients, please wait...'), { type: 'warning' });
            return;
        }

        const isCheckIn = this.state.login_employee?.attendance_state === 'checked_out';

        // Restore previous selection (if modal used)
        const stored = sessionStorage.getItem("selectedPatientId");
        if (stored) {
            this.state.selectedPatientId = parseInt(stored, 10);
            sessionStorage.removeItem("selectedPatientId");
        }

        if (isCheckIn) {
            // Case 1: Multiple patients — show selection modal
            if (this.state.patients.length > 1 && !this.state.selectedPatientId) {
                this.showPatientSelectionModal();
                return;
            }

            // Case 2: One patient — use automatically
            if (this.state.patients.length === 1 && !this.state.selectedPatientId) {
                this.state.selectedPatientId = this.state.patients[0].id;
            }

            // Case 3: No patients — allow check-in without patient
            if (this.state.patients.length === 0) {
                this.state.selectedPatientId = null;
            }

            // Fallback: Unexpected state
            if (this.state.selectedPatientId === undefined) {
                this.notification.add(_t('Please select a patient.'), { type: 'danger' });
                return;
            }
        } else {
            this.state.selectedPatientId = null;  // Reset for check-out
        }

        // Get geolocation
        let latitude = null, longitude = null;
        try {
            const pos = await getLocation();
            latitude = pos.coords.latitude;
            longitude = pos.coords.longitude;

            const accuracy = pos.coords.accuracy;
            if (accuracy > 100) {
                this.notification.add(_t(`Warning: Low location accuracy (~${Math.round(accuracy)}m)`), {
                    type: 'warning',
                });
            }
        } catch {
            this.notification.add(_t('⚠️ Location not available. Ensure GPS and permissions are enabled.'), {
                type: 'danger',
            });
        }

        // Call server method to register attendance
        const res = await this.orm.call(
            'hr.attendance',
            'location_attendance',
            [this.state.selectedPatientId, latitude, longitude]
        );

        if (res.error) {
            this.notification.add(res.error, { type: 'danger' });
        } else {
            const msg = res.status === 'checked_in'
                ? _t('Checked In')
                : _t('Checked Out');
            this.effect.add({ message: msg, type: 'rainbow_man', fadeout: 'fast' });

            // Update UI banner and employee state
            if (res.status === 'checked_in') {
                const patient = this.state.patients.find(p => p.id === this.state.selectedPatientId);
                this.state.login_employee.patient_name = patient ? patient.name : '';
                this._displayCheckInBanner(this.state.login_employee.patient_name);
            } else {
                this.state.login_employee.patient_name = '';
                this._removeCheckInBanner();
            }

            this.state.login_employee.attendance_state = res.status;
            this.state.selectedPatientId = null;
        }
    },

    // Show modal for selecting a patient
    showPatientSelectionModal() {
        const modal = document.createElement('div');
        modal.classList.add('modal', 'fade', 'show');
        modal.style.display = 'block';
        modal.innerHTML = `
          <div class="modal-backdrop fade show"></div>
          <div class="modal-dialog animate-modal">
            <div class="modal-content p-3 position-relative">
              <button class="btn-close-modal" aria-label="Close" style="position:absolute;top:10px;right:15px;font-size:1.5rem;background:none;border:none;">×</button>
              <div class="modal-header border-bottom-0">
                <h5 class="modal-title">Select Patient</h5>
              </div>
              <div class="modal-body">
                <ul class="list-group">
                  ${this.state.patients.map(
                      (p) => `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                      <span>${p.name}</span>
                      <button class="btn btn-sm btn-primary" data-patient-id="${p.id}">Select</button>
                    </li>`
                  ).join('')}
                </ul>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modal);

        modal.querySelector('.btn-close-modal').addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        modal.querySelectorAll('button[data-patient-id]').forEach((btn) => {
            btn.addEventListener('click', (ev) => {
                const id = parseInt(ev.currentTarget.dataset.patientId, 10);
                sessionStorage.setItem("selectedPatientId", id);
                document.body.removeChild(modal);
                this.attendance_sign_in_out(); // Retry sign-in
            });
        });
    },

    // Display check-in banner
    _displayCheckInBanner(patientName) {
        this._removeCheckInBanner();
        const banner = document.createElement('div');
        banner.id = 'patient-checkin-banner';
        banner.className = 'alert alert-info mt-2';
        banner.style.textAlign = 'center';
        banner.innerHTML = `Checked in ${patientName ? `with: <strong>${patientName}</strong>` : 'without patient'}`;
        const dashboard = document.querySelector('.oe_hr_dashboard') || document.body;
        dashboard.insertBefore(banner, dashboard.firstChild);
    },

    // Remove existing banner
    _removeCheckInBanner() {
        const banner = document.getElementById('patient-checkin-banner');
        if (banner) {
            banner.remove();
        }
    }
});
