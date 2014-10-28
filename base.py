#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado


class BaseHandler(tornado.web.RequestHandler):

    def get_result_and_options(self, arguments):
        '''
        获取参数集
        '''
        result, options = {}, {}
        for arg in arguments:
            value = self.get_argument(arg, None)
            if value:
                options[arg] = value
            result[arg] = value or ""
        return result, options
