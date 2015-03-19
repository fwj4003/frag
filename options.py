# coding: utf8

"""命令行解析工具
"""

import argparse


class OptionParser(object):

    """命令行解析器
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.args = None

    def define(self, shortcut, name, type_, default, help_):
        """定义

        @shortcut, str, 快捷命令
        @name, str, 完成命令
        @type_, type, 类型
        @default, type, 默认值
        @help, str, 帮助
        """
        self.parser.add_argument(
            "-%s" % shortcut, "--%s" % name, help=help_,
            type=type_, default=default)

    def parse_command_line(self):
        """解析命令行

        """
        self.args = self.parser.parse_args()

    def __getattr__(self, name):
        """获取参数值

        @name, str, 属性名
        """
        return getattr(self.args, name)


options = OptionParser()


def define(shortcut, name, type_, default, help_):
    """全局的命令行定义,最终调用了OptionParser的define

    @shortcut, str, 快捷命令
    @name, str, 完成命令
    @type, type, 类型
    @default, type, 默认值
    @help, str, 帮助
    """
    return options.define(shortcut, name, type_, default, help_)
