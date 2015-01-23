#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import datetime
import urllib
import urllib2
import urlparse
import StringIO
import gzip
import json
import logging
import functools
import traceback

import MySQLdb

from tornado import gen
from tornado.web import HTTPError

from decimal import Decimal

from lib.form import MultiPartForm
from conf.urlconf import FDFS_UPLOAD_URL
from tornado.httpclient import AsyncHTTPClient, HTTPRequest


@gen.coroutine
def async_fetch(url, method="POST", data=None, timeout=30):
    '''
        异步请求
    '''
    kwargs = {
        "connect_timeout": timeout,
        "request_timeout": timeout,
    }
    if isinstance(url, basestring):
        url = url.strip()
        if data:
            if method == "GET":
                url += '?' + urllib.urlencode(data)
            else:
                kwargs["body"] = urllib.urlencode(data)
        request = HTTPRequest(url, method, **kwargs)
    elif isinstance(url, HTTPRequest):
        request = url
    http_client = AsyncHTTPClient()
    response = None
    for i in range(3):
        try:
            response = yield http_client.fetch(request)
            logging.info(
                "url:%s time: %s" % (request.url, response.request_time))
            break
        except Exception as e:
            logging.warning(
                "url: %s try %d failed: %s", request.url, i, str(e))
            continue
    if not response:
        logging.error("url:%s failed to fetch!" % request.url)
        raise HTTPError(599)
    raise gen.Return(response)


def sync_fetch(url, data=None):
    '''
        同步请求方法,3次请求
    '''
    if data:
        data = urllib.urlencode(data)
    content = None
    for _ in range(3):
        try:
            content = urllib2.urlopen(url, data).read()
            break
        except Exception:
            continue
    if not content:
        logging.error("url:%s failed to fetch!" % url)
        raise Exception("url:%s failed to fetch!" % url)
    return content


def strptime(dtime, fmt):
    """
    for < 2.6
    """
    time_stamp = time.mktime(time.strptime(dtime, fmt))
    return datetime.datetime.fromtimestamp(time_stamp)


def time_start(d, typ):
    if typ == "hour":
        d -= datetime.timedelta(
            minutes=d.minute, seconds=d.second, microseconds=d.microsecond)
    elif typ == "day":
        d -= datetime.timedelta(
            hours=d.hour, minutes=d.minute, seconds=d.second, microseconds=d.microsecond)
    elif typ == "week":
        d -= datetime.timedelta(
            days=d.weekday(), hours=d.hour, minutes=d.minute, seconds=d.second, microseconds=d.microsecond)
    elif typ == "month":
        d -= datetime.timedelta(
            days=d.day - 1, hours=d.hour, minutes=d.minute, seconds=d.second, microseconds=d.microsecond)
    else:
        raise Exception("wrong type %s" % (typ,))
    return d


def strftime_day(dtime):
    """
    for simplariy
    """
    return str(time_start(dtime, "day"))


def gzip_compress(data):
    zbuf = StringIO.StringIO()
    zfile = gzip.GzipFile(mode='wb', compresslevel=9, fileobj=zbuf)
    zfile.write(data)
    zfile.close()
    return zbuf.getvalue()


def gzip_decompress(data):
    zbuf = StringIO.StringIO(data)
    zfile = gzip.GzipFile(fileobj=zbuf)
    data = zfile.read()
    zfile.close()
    return data


def url_add_params(url, escape=True, **params):
    """
    add new params to given url
    """
    pr = urlparse.urlparse(url)
    query = dict(urlparse.parse_qsl(pr.query))
    query.update(params)
    prlist = list(pr)
    if escape:
        prlist[4] = urllib.urlencode(query)
    else:
        prlist[4] = '&'.join(['%s=%s' % (k, v) for k, v in query.items()])
    return urlparse.ParseResult(*prlist).geturl()


def time_next(d, typ):
    if typ == "hour":
        d += datetime.timedelta(hours=1)
    elif typ == "day":
        d += datetime.timedelta(days=1)
    elif typ == "week":
        d += datetime.timedelta(days=7)
    elif typ == "month":
        year = d.year + 1 if d.month == 12 else d.year
        month = 1 if d.month == 12 else d.month + 1
        d = datetime.datetime(year, month, 1)
    else:
        raise Exception("wrong type %s" % (typ,))
    return time_start(d, typ)


def time_diff(d, num):
    d += datetime.timedelta(days=num)
    return d


def pack_model(inst, dic):
    if not isinstance(dic, dict):
        raise Exception("Invalid Type : %s" % type(dic))
    for k, v in dic.items():
        setattr(inst, k, v)
    return inst


def encode_data(s):
    if isinstance(s, dict):
        result = {}
        for k, v in s.items():
            result[k] = encode_data(v)
    elif isinstance(s, (list, tuple)):
        result = []
        for i in s:
            result.append(encode_data(i))
    else:
        result = to_str(s)
    return result


def to_str(s):
    if isinstance(s, unicode):
        return s.encode("utf-8")
    return s


def escape_str(s):
    '''
        转义字符串,防止SQL注入
    '''
    return MySQLdb.escape_string(s)


REGX = u'[\u4e00-\u9fa5a-zA-Z0-9]'


def intercept(content, regx=REGX):
    '''
        截取字符串
        @regx, unicode, 正则
        @content, 内容
        return str
    '''
    content = to_unicode(content)
    res = re.findall(regx, content)
    return ''.join(res).encode("utf8")


def is_num(num_str, flag=","):
    '''
        字符串是否为数字
    '''
    if not num_str:
        return True
    # 如果是数字直接返回True
    if num_str.isdigit():
        return True
    # 否则认为是符号分割的字符串,默认为逗号
    ns = num_str.split(flag)
    for s in ns:
        if not s.isdigit():
            return False
    return True


@gen.coroutine
def fdfs_upload(fdfs_uri, path_or_handle, timeout=10):
    '''
        上传到FDFS
    '''
    file_name = fdfs_uri.split('/')[-1]
    form = MultiPartForm()
    if isinstance(path_or_handle, basestring):
        with open(path_or_handle) as f:
            form.add_file("file", file_name, f)
    else:
        form.add_file("file", str(file_name), path_or_handle)
    body = str(form)
    headers = {
        "Content-Type": form.get_content_type(),
        "Content-Length": len(body)
    }
    url = "%s/fdfs/uniadd?file_uri=%s" % (FDFS_UPLOAD_URL, fdfs_uri)
    request = HTTPRequest(
        url, method="POST", headers=headers, body=body,
        connect_timeout=timeout, request_timeout=timeout)
    response = yield async_fetch(request)
    result = json.loads(response.body)
    if result["code"] != 0:
        raise
    raise gen.Return(result["body"]["file_id"])


@gen.coroutine
def fdfs_delete(file_uri, timeout=10):
    '''
        删除FDFS资源
    '''
    url = "%s/fdfs/unidel?file_uri=%s" % (FDFS_UPLOAD_URL, file_uri)
    request = HTTPRequest(
        url, method="GET", headers=None, body=None,
        connect_timeout=timeout, request_timeout=timeout)
    response = yield async_fetch(request)
    result = json.loads(response.body)
    if result["code"] != 0:
        raise
    raise gen.Return(result["body"]["file_id"])


def get_month_diff(self, mod=1):
    '''
        获取月日期差
    '''
    def fmt_month(m):
        # 月份补0
        if m < 10:
            m = "%s%s" % ("0", str(m))
        return str(m)
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    if mod == 1:
        if month == 1:
            pre_month = 12
            pre_year = year - 1
        else:
            pre_month = month - 1
            if pre_month < 10:
                pre_month = fmt_month(pre_month)
                pre_year = year
        pre = "%s-%s" % (str(pre_year), fmt_month(pre_month))
    elif mod == 2:
        pre = "%s-%s" % (str(year - 1), fmt_month(month))
    # 当前年月
    cur = "%s-%s" % (str(year), fmt_month(month))
    return pre, cur


def format_num(s, regx=r'\d*\.*\d+'):
    rows = re.findall(regx, s)
    return rows[0] if rows else None


def round_num(num, n=2):
    '''
        四舍五入
    '''
    num = Decimal(str(num))
    return round(num, n)


def to_unicode(s):
    if not isinstance(s, unicode):
        if isinstance(s, (int, float, long)):
            s = str(s)
        return unicode(s, 'utf-8')
    return s


def match_contain(arga, argb, ignore_symbol=True):
    if not arga or not argb:
        return False
    arga = to_unicode(arga)
    argb = to_unicode(argb)
    # 忽略符号
    if ignore_symbol:
        arga = intercept(arga)
        argb = intercept(argb)
    if len(arga) < len(argb):
        arga, argb = argb, arga
    return True if argb in arga else False


def match_similar(arga, argb, ratio=0.7):
    arga = to_unicode(arga)
    argb = to_unicode(argb)

    count = 0  # 匹配数
    start = 0  # 匹配起始索引值

    if len(arga) < len(argb):
        arga, argb = argb, arga
    for s in argb:
        # 依次匹配
        pos = arga.find(s, start)
        if pos >= 0:
            # 匹配成功,修改下次查询索引,并增加匹配数
            start = pos + 1
            count += 1
    return True if float(count) / float(len(arga)) >= ratio else False


def camel_to_underline(camel_format):
    '''
        驼峰 转 下划线
    '''
    underline_format = ''
    if isinstance(camel_format, str) or isinstance(camel_format, unicode):
        for _s_ in camel_format:
            underline_format += _s_ if not _s_.isupper(
            ) else '_' + _s_.lower()
    elif isinstance(camel_format, dict):
        underline_format = {}
        for key, value in camel_format.items():
            if isinstance(value, (list, dict)):
                value = camel_to_underline(value)
            underline_format[camel_to_underline(key)] = value
    elif isinstance(camel_format, list):
        underline_format = []
        for item in camel_format:
            underline_format.append(camel_to_underline(item))
    return underline_format


def underline_to_camel(underline_format):
    '''
        下划线 转 驼峰
    '''
    camel_format = ''
    if isinstance(underline_format, str) \
            or isinstance(camel_format, unicode):
        for (i, _s_) in enumerate(underline_format.split('_')):
            if i:
                camel_format += _s_.capitalize()
            else:
                camel_format += _s_
    elif isinstance(underline_format, dict):
        camel_format = {}
        for key, value in underline_format.items():
            if isinstance(value, datetime.datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, (list, dict)):
                value = underline_to_camel(value)
            camel_format[underline_to_camel(key)] = value
    elif isinstance(underline_format, list):
        camel_format = []
        for item in underline_format:
            camel_format.append(underline_to_camel(item))
    return camel_format


class NotImplemetedError(Exception):

    def __init__(self, method_name):
        self.method = method_name

    def __str__(self):
        return "%s: Instance method %s not implemented!"\
            % ("NotImplemetedError", self.method)


def catch_error(func):
    """用以捕获方法异常的装饰器
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        """包装
        """
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            logging.error(str(e))
            logging.error(traceback.format_exc())
    return wrapper


def url_concat(url, args):
    """在指定URL新增参数

    @args, dict, 参数字典
    """
    if not args:
        return url
    if url[-1] not in ('?', '&'):
        url += '&' if ('?' in url) else '?'
    return url + urllib.urlencode(args)


def force_utf8(data):
    """数据转换为utf8

    @data: 待转换的数据
    @return: utf8编码
    """
    if isinstance(data, unicode):
        return data.encode('utf-8')
    elif isinstance(data, list):
        for idx, i in enumerate(data):
            data[idx] = force_utf8(i)
    elif isinstance(data, dict):
        for i in data:
            data[i] = force_utf8(data[i])
    return data


def format_timestamp(timestamp, fmt="%Y-%m-%d %H:%M:%S"):
    """格式化时间戳

    @timestamp, float, time.time()时间戳
    @fmt, str, 格式模版
    @return 年月日时分秒
    """
    return time.strftime(fmt, time.localtime(timestamp))


class Timer(object):
    """定时器，定时执行指定的函数

    """

    def __init__(self, start, interval):
        """
        @start, int, 延迟执行的秒数
        @interval, int, 每次执行的间隔秒数
        """
        self.start = start
        self.interval = interval

    def run(self, func, *args, **kwargs):
        """运行定时器

        @func, callable, 要执行的函数
        """
        time.sleep(self.start)
        while True:
            func(*args, **kwargs)
            time.sleep(self.interval)
