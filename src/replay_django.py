#!/usr/bin/env python
import sys
import os
import time
import codecs
import hashlib
import struct
import MySQLdb


def hash(str):
    h = hashlib.md5()
    h.update(str)
    return struct.unpack('q', h.digest()[:8])[0]

if __name__ == "__main__":
    db = MySQLdb.connect(host="localhost", user="root", passwd="root", db="voyage", charset="utf8")
    c = db.cursor()
    f = codecs.open("/mnt/bbc", "r", "utf-8")

    start = time.time()
    t0 = 0
    t1 = 0
    t2 = 0
    i = 0
    for line in f:
        type = line[0]

        if(type == "0"):
            s0 = time.time()
            if(c.execute("select * from tovisit order by id limit 1")):
                id = c.fetchone()[0]
                c.execute("delete from tovisit where id=%s", (id,))
            else:
                print "nothing to pop!"

            t0 += time.time() - s0
            continue
        arg = line[2:].strip()
        if(type == "1"):
            s1 = time.time()
            c.execute(u"select exists(select * from visited where url=%s)",(arg,))
            c.fetchone()
            t1 += time.time() - s1
        elif(type == "2"):
            s2 = time.time()
            try:
                c.execute(u"insert into visited values (%s)", (arg,))
            except MySQLdb.IntegrityError:
                pass
            c.execute(u"insert into tovisit values (default, %s)", [arg])
            t2 += time.time() - s2
        i+=1
        if(i > 10000000):
            break
        if i % 10000 == 0:
            print i
            db.commit()
    c.close()
    db.commit()
    db.close()

    print "elapsed time: " + str((time.time() - start))
    print "t0:", t0
    print "t1:", t1
    print "t2:", t2
    
