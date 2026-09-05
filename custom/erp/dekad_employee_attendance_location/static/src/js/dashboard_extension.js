/** @odoo-module **/

import { HrDashboard } from '@hrms_dashboard/js/dashboard';
import { patch } from '@web/core/utils/patch';
import { useService } from '@web/core/utils/hooks';
import { _t } from '@web/core/l10n/translation';


/* ================== UTIL ================== */

function getLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            return reject(new Error('Geolocation not supported.'));
        }

        navigator.geolocation.getCurrentPosition(
            position => resolve(position),
            error => reject(error),
            {
                enableHighAccuracy: true,
                timeout: 10000
            }
        );
    });
}


/* ================== DASHBOARD PATCH ================== */

patch(HrDashboard.prototype, {

    setup() {
        super.setup();

        this.orm = useService('orm');
        this.notification = useService('notification');
        this.effect = useService('effect');
    },


    /* ================================
       Attendance with GPS
       ================================ */

    async attendance_sign_in_out() {
        let latitude = null;
        let longitude = null;

        try {
            const pos = await getLocation();

            latitude = pos.coords.latitude;
            longitude = pos.coords.longitude;

            if (pos.coords.accuracy > 100) {
                this.notification.add(
                    _t(
                        `Warning: Low accuracy (~${Math.round(
                            pos.coords.accuracy
                        )}m)`
                    ),
                    {
                        type: 'warning'
                    }
                );
            }

        } catch (error) {

            this.notification.add(
                _t('Location not available. Check GPS permissions.'),
                {
                    type: 'danger'
                }
            );
        }


        const res = await this.orm.call(
            'hr.attendance',
            'location_attendance',
            [latitude, longitude]
        );


        if (res.error) {
            this.notification.add(
                res.error,
                {
                    type: 'danger'
                }
            );

            return;
        }


        const msg =
            res.status === 'checked_in'
                ? _t('Checked In')
                : _t('Checked Out');


        this.effect.add({
            message: msg,
            type: 'rainbow_man',
            fadeout: 'fast'
        });


        this.state.login_employee.attendance_state = res.status;
    }

});