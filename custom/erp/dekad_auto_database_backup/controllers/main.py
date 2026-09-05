# File: dekad_auto_database_backup/controllers/main.py

import os
from odoo import http
from odoo.http import request, Stream
from odoo.exceptions import AccessError

class BackupController(http.Controller):

    @http.route('/dekad/backup/download/<int:log_id>', type='http', auth='user')
    def download_backup(self, log_id, **kw):
        """
        Download a backup file using the path stored in the log.
        """
        # Check security
        log = request.env['dekad.backup.log'].sudo().browse(log_id)
        if not log.exists():
            return request.not_found()
        
        # Ensure current user has read access to the log (security check)
        try:
            log.with_user(request.env.user).check_access('read')
        except AccessError:
            raise AccessError("You do not have permission to access this backup.")

        if not log.file_path or not os.path.exists(log.file_path):
            return request.not_found()

        # Get file name from path
        filename = os.path.basename(log.file_path)
        
        # Manually create Stream object for absolute paths to bypass file_path restriction
        import mimetypes
        stat = os.stat(log.file_path)
        stream = Stream(
            type='path',
            path=log.file_path,
            mimetype=mimetypes.guess_type(log.file_path)[0],
            download_name=filename,
            etag=f'{int(stat.st_mtime)}-{stat.st_size}',
            last_modified=stat.st_mtime,
            size=stat.st_size,
        )
        return stream.get_response(as_attachment=True)
