/** @odoo-module **/

import { registry } from '@web/core/registry';

registry.category('actions').add('get_gps_coordinates', async (env, action) => {
    const notification = env.services.notification;
    const orm = env.services.orm;
    const reloadAction = { type: 'ir.actions.client', tag: 'reload' };

    if (!navigator.geolocation) {
        notification.add("Geolocation is not supported by your browser.", { type: 'danger' });
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;

            try {
                await orm.call('hr.employee', 'update_employee_gps', [
                    action.context.employee_id,
                    latitude,
                    longitude
                ]);

                notification.add("GPS coordinates updated successfully.", { type: 'success' });
                env.services.action.doAction(reloadAction);

            } catch (error) {
                notification.add("Failed to save GPS coordinates.", { type: 'danger' });
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