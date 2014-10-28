#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
sys.path.append(os.path.dirname(os.path.split(os.path.realpath(__file__))[0]))

import logging
import datetime

from service import Service


class Schedule(object):


    def __init__(self):
        self.conf_list = []

    def register(self, func, hours=[], days=[]):
        '''
        注册定时任务
        '''
        self.conf_list.append([func, hours, days])

    def run(self):
        '''
        执行定时任务
        '''
        count = 0
        now = datetime.datetime.now()
        logging.info('start sched: %s', now.strftime('%Y-%m-%d %H:%M:%S'))
        for func, hours, days in self.conf_list:
            try:
                if now.hour in hours and (not days or now.day in days):
                    ret = func()
                    logging.info('%s --> %s', func.func_name, ret)
                    count += 1
            except Exception, e:
                logging.error('%s', str(e), exc_info=True)
        end = datetime.datetime.now()
        logging.info('end sched: %s, count = %d',
                     end.strftime('%Y-%m-%d %H:%M:%S'), count)
        return count

if __name__ == "__main__":
    sched = Schedule()
    sched.register(func, [1], [])
    sched.run()
