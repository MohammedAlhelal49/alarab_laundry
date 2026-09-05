// attendance_location/static/src/js/attendance_location.js
/** @odoo-module **/

import { registry } from '@web/core/registry';

registry.category('actions').add('get_gps_coordinates', (env, action) => {
    const notification = env.services.notification;
    const orm = env.services.orm;
    const reloadAction = { type: 'ir.actions.client', tag: 'reload' };

    // Check if geolocation is supported
    if (!navigator.geolocation) {
        notification.add("Geolocation is not supported by your browser.", { type: 'danger' });
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;
            const timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');

            try {
                await orm.call('res.partner', 'write', [
                    [action.context.partner_id],
                    {
                        gps_latitude: latitude,
                        gps_longitude: longitude,
                        gps_last_updated: timestamp,
                    },
                ]);
                notification.add("GPS coordinates updated successfully.", { type: 'success' });
                env.services.action.doAction(reloadAction);
            } catch (error) {
                notification.add("Failed to save GPS coordinates on the server.", { type: 'danger' });
                console.error('Error saving GPS coordinates:', error);
            }
        },
        (error) => {
            notification.add(`Failed to retrieve location: ${error.message}`, { type: 'danger' });
            console.error('Geolocation error:', error);
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
        }
    );
});
