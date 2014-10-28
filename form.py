#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mimetools
import mimetypes
import itertools
from tornado.httpclient import HTTPRequest


class MultiPartForm(object):

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return "multipart/form-data; boundary=%s" % self.boundary

    def add_field(self, name, value):
        self.form_fields.append((name, value))

    def add_file(self, field_name, file_name, file_handle, mimetype=None):
        body = file_handle.read()
        if not mimetype:
            mimetype = mimetypes.guess_type(file_name)[0] or\
                "application/octet-stream"
            self.files.append((field_name, file_name, mimetype, body))
        return

    def __str__(self):
        parts = []
        part_boundary = "--" + self.boundary
        parts.extend([
            part_boundary, 'Content-Disposition: form-data; name="%s"' % name,
            '', value, ] for name, value in self.form_fields)
        parts.extend([
            part_boundary,
            'Content-Disposition: form-data; name="%s"; filename="%s"' %
            (field_name, file_name),
            "Content-Type: %s" % content_type, '', body, ]
            for field_name, file_name, content_type, body in self.files)
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


def get_file_request(url, file_name, file_path):
    form = MultiPartForm()
    with open(file_path, "rb") as f:
        form.add_file("filename", file_name, f)
    body = str(form)
    headers = {
        "Content-type": form.get_content_type(),
        "Content-length": len(body)
    }
    request = HTTPRequest(
        url, method="POST",
        headers=headers, body=body, connect_timeout=10, request_timeout=10)
    return request
