from odoo.tests.common import TransactionCase

class TestFcmDevice(TransactionCase):

    def setUp(self):
        super(TestFcmDevice, self).setUp()
        self.Partner = self.env['res.partner']
        self.FcmDevice = self.env['fcm.device']

    def test_fcm_device_creation(self):
        """Test creating an FCM device record."""
        partner = self.Partner.create({'name': 'Test Partner'})
        device = self.FcmDevice.create({
            'partner_id': partner.id,
            'token': 'test_token_123',
            'device_type': 'android'
        })
        self.assertEqual(device.token, 'test_token_123')
        self.assertEqual(device.partner_id, partner)

    def test_fcm_token_uniqueness(self):
        """Test that FCM tokens must be unique."""
        partner = self.Partner.create({'name': 'Test Partner'})
        self.FcmDevice.create({
            'partner_id': partner.id,
            'token': 'duplicate_token',
        })
        with self.assertRaises(Exception):
            self.FcmDevice.create({
                'partner_id': partner.id,
                'token': 'duplicate_token',
            })
