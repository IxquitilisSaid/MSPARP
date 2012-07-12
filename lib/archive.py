import datetime

from model import Log, LogPage

def get_or_create_log(redis, mysql, chat, chat_type):

    # Find existing log or create a new one.

    try:
        log = mysql.query(Log)
        print log
        if chat_type=='match':
            print "chat type is match"
            log_id = redis.get('chat.'+chat+'.log')
            print log_id
            if log_id is None:
                print "no log id"
                raise Exception
            print "log id"
            log = log.filter(Log.id==log_id)
            print log
        else:
            print "chat type is not match"
            log = log.filter(Log.url==chat)
            print log
        print log
        print "getting log"
        log = log.one()
        print "got log"
        print log
        try:
            print "getting latest page"
            latest_page_query = mysql.query(LogPage).filter(LogPage.log_id==log.id)
            print latest_page_query
            print list(latest_page_query)
            latest_page = latest_page_query[-1]
            print latest_page
        except:
            print "no latest page"
            latest_page = new_page(mysql, log)
    except:
        print "not got log"
        url = chat if chat_type!='match' else None
        print url
        log = Log(url=url)
        print log
        mysql.add(log)
        print log
        mysql.flush()
        print log
        print log.id
        if chat_type=='match':
            redis.set('chat.'+chat+'.log', log.id)
        latest_page = new_page(mysql, log)

    return log, latest_page

def new_page(mysql, log, last=0):
    latest_page = LogPage(log_id=log.id, number=last+1, content=u'')
    print latest_page
    mysql.add(latest_page)
    return latest_page

def archive_chat(redis, mysql, chat, chat_type=None, backlog=0):

    if chat_type is None:
        chat_type = redis.get('chat.'+chat+'.type')

    log, latest_page = get_or_create_log(redis, mysql, chat, chat_type)

    print latest_page
    print latest_page.number

    archive_length = redis.llen('chat.'+chat)-backlog

    for n in range(archive_length):
        line = redis.lindex('chat.'+chat, n)
        print len(latest_page.content.encode('utf8'))
        print len(line)
        # Create a new page if the line won't fit on this one.
        #if len(latest_page.content.encode('utf8'))+len(line)>65535:
        if len(latest_page.content.encode('utf8'))+len(line)>65535:
            print "creating a new page"
            latest_page = latest_page = new_page(mysql, log, latest_page.number)
            print "page "+str(latest_page.number)
        latest_page.content += unicode(line, encoding='utf8')+'\n'

    log.time_saved = datetime.datetime.now()

    mysql.commit()

    # Don't delete from redis until we've successfully committed.
    redis.ltrim('chat.'+chat, archive_length, -1)

    return log.id

def delete_chat(redis, chat):

    # Delete type first because it's used to check whether a chat exists.
    redis.delete('chat.'+chat+'.type')

    sessions = redis.lrange('chat.'+chat+'.counter', 0, -1)
    for session in sessions:
        redis.srem('session.'+session+'.chats', chat)
        redis.delete('session.'+session+'.chat.'+chat)

    redis.delete('chat.'+chat+'.counter')
    redis.delete('chat.'+chat+'.characters')
    redis.delete('chat.'+chat+'.log')
    redis.delete('chat.'+chat+'.sessions')
    redis.delete('chat.'+chat)
