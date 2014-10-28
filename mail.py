#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Abstract: send mail

import logging
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from conf.settings import MAIL_CONF


class Mail(object):

    def __init__(self, smtp=None, user=None, pwd=None, sign=None):
        self.smtp = smtp or MAIL_CONF["mail_host"]
        self.user = user or MAIL_CONF["mail_user"]
        self.pwd = pwd or MAIL_CONF["mail_pass"]
        # 签名
        self.sign = sign or self.user
        self.isauth = True

    def parse_send(self, subject, content, plugin):
        return subject, content, plugin

    def send(self, subject, content, tolist, cclist=[], plugins=[]):
        msg = MIMEMultipart()
        msg.set_charset('utf-8')
        msg['from'] = self.sign
        msg['to'] = ','.join(tolist)
        if cclist:
            msg['cc'] = ','.join(cclist)
        msg['subject'] = subject
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        for plugin in plugins:
            f = MIMEApplication(plugin['content'])
            f.add_header(
                'content-disposition', 'attachment', filename=plugin['subject'])
            msg.attach(f)

        # 防止超时,增加异常重试机制
        for i in range(0, 5):
            try:
                s = smtplib.SMTP(self.smtp)
                break
            except Exception, e:
                logging.error("smtp connection %d failed: %s" % (i, str(e)))
                continue
        s.set_debuglevel(smtplib.SMTP.debuglevel)
        if self.isauth:
            s.docmd("EHLO %s" % self.smtp)
        try:
            s.starttls()
        except smtplib.SMTPException:
            pass
        s.login(self.user, self.pwd)
        r = s.sendmail(self.user, tolist, msg.as_string())
        s.close()
        return r

