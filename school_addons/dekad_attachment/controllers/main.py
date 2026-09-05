import json
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.mail.controllers.attachment import AttachmentController  # Corrected import path


class AttachmentControllerInherited(AttachmentController):

    @http.route('/mail/attachment/upload', methods=['POST'], type='http', auth='public')
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        max_file_size = 5 * 1024 * 1024  # Set max file size to 5 MB
        ufile.seek(0, 2)  # Move to the end of the file
        file_size = ufile.tell()  # Get the current position (file size)
        ufile.seek(0)  # Reset file pointer to the start

        if file_size > max_file_size:
            print('data here')
            attachment_data = {'error': _("Attachment File size cannot exceed 5 MB!")}
            return request.make_response(
                data=json.dumps(attachment_data),
                headers=[('Content-Type', 'application/json')]
            )
        else:
            # Call the original method from the parent class
            res = super(AttachmentControllerInherited, self).mail_attachment_upload(
                ufile, thread_id, thread_model, is_pending=is_pending, **kwargs
            )
            return res
