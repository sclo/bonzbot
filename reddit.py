# -*- coding: utf-8 -*-
import irc3
from irc3 import utils
from irc3.plugins.command import command
from irc3.plugins.cron import cron

import praw


_CACHE = {}


@irc3.plugin
class Plugin(object):

    def __init__(self, bot):
        self.bot = bot
        self._r = praw.Reddit(bot.config['reddit']['ua'])
        self._sub = self._r.get_subreddit(utils.as_list(
            bot.config['reddit']['subs'])[0])
        init(bot.config['reddit'])

    def msg_submission(self, target, submission):
        msg_submission(self.bot, target, submission)

    def help(self, target):
        """/r/devel
        usage: !r <action>
        Action can be one of the following:
            * latest: get the latest submission to date
            * last: get the last 10 submissions
        """
        do_strip = False
        for line in self.help.__doc__.splitlines():
            if do_strip:
                line = line[8:]
            self.bot.privmsg(target,line)
            do_strip = True

    @command
    def r(self, mask, target, args):
        """Query /r/devel

        %%r
        %%r <cmd>
        """
        if args['<cmd>'] is None or args['<cmd>'] == 'help':
            self.help(mask.nick)
        elif args['<cmd>'] == "latest":
            self.msg_submission(mask.nick,
                                get_new(sel._sub, limit=1).next())
        elif args['<cmd>'] == "last":
            for submission in get_new(self._sub, limit=10):
                self.msg_submission(mask.nick, submission)
        else:
            self.help(mask.nick)


def lsns():
    global _CACHE
    return filter(lambda x: x != '__all__', _CACHE.keys())

def setcache(ns, key, value):
    """set a cache key in a given namespace"""
    global _CACHE
    if ns not in _CACHE:
        _CACHE[ns] = {}
    _CACHE[ns][key] = value

def getcache(ns, key):
    """get a cache key in a given namespace return None in case of
    missing key
    """
    global _CACHE
    if ns not in _CACHE or key not in _CACHE[ns]:
        return None
    return _CACHE[ns][key]

def init(conf):
    setcache('__all__', 'echo', utils.as_list(conf['echo_channels']))
    setcache('__all__', 'msg', unicode(conf['echo_msg']))
    for sub in utils.as_list(conf['subs']):
        r = praw.Reddit(conf['ua'])
        subobj = r.get_subreddit(sub)
        setcache(sub, 'sub', subobj)
        try:
            setcache(sub, 'latest', get_new(subobj, limit=1).next())
        except StopIteration:
            setcache(sub, 'latest', None)

def msg_submission(bot, target, submission):
    msg = getcache('__all__', 'msg')
    bot.privmsg(target, msg.format(
        title=submission.title,
        author=submission.author.name,
        subname=submission.subreddit.display_name,
        url=submission.url))

def get_new(sub, limit=10):
    try:
        return sub.get_new(limit=limit)
    except irc3.HTTPError:
        return None

def get_latest(sub, latest, offset=0):
    """get a list of submissions made since ``latest`` submission"""
    if offset >= 10:
        return []
    new = []
    lim = 10 + offset * 10
    # FIXME catch StoppIteration and "do the right thing"
    submissions = get_new(sub, limit=lim)
    for i in range(offset * 10):
        submissions.next()
    i = 0
    for submission in submissions:
        if submission.id == latest.id:
            return new
        new.append(submission)
        i += 1
    if i < 10:
        return new
    return new.extend(get_latest(sub, latest, offset + 1))


@cron('*/1 * * * *')
def poll_new(bot):
    for ns in lsns():
        latest = getcache(ns, 'latest')
        sub = getcache(ns, 'sub')
        if latest is None:
            try:
                setcache(ns, 'latest', get_new(sub, limit=1).next())
                for target in get('__all__', 'echo'):
                    msg_submission(bot, target, getcache(ns, 'latest'))
            except StopIteration:
                setcache(ns, 'latest', None)
        else:
            bot.log.info("[reddit] get latest submissions from "
                "'{}'".format(sub.display_name))
            new = get_latest(sub, latest)
            if new:
                setcache(ns, 'latest', new[0])
                for submission in reversed(new):
                    for target in getcache('__all__', 'echo'):
                        msg_submission(bot, target, submission)
