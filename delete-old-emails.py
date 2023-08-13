#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-2-Clause

import argparse
import datetime
import configparser
import imaplib
import email.utils
import mailbox
import os
import email
import syslog

__version__ = '1.0'


def Process(config):
    if not os.path.exists(config["backup"]["path"]):
        os.makedirs(config["backup"]["path"], exist_ok=True)

    processTime = datetime.datetime.utcnow()
    cutoffTime = processTime - datetime.timedelta(
        days=int(config["options"]["min_age"])
    )

    conn = imaplib.IMAP4_SSL(config["mailbox"]["server"])
    conn.login(config["mailbox"]["username"], config["mailbox"]["password"])
    _, _ = conn.list()
    conn.select()

    _, data = conn.uid(
        "SEARCH", "(BEFORE {})".format(cutoffTime.strftime("%d-%b-%Y"))
    )
    if data != [b""]:
        uids = data[0].split()
        # Back them up first
        if config["backup"]["type"] == "Maildir":
            md = mailbox.Maildir(config["backup"]["path"])
            md.lock()
            folder = md.add_folder(processTime.strftime("%d-%b-%Y-%H:%M:%S"))

            for uid in uids:
                _, maildata = conn.uid("FETCH", uid, "(RFC822)")
                message = email.message_from_bytes(maildata[0][1])
                folder.add(message)
            md.flush()
            md.unlock()
            syslog.syslog("Backed up {} e-mails".format(len(uids)))
        else:
            syslog.syslog("No backup option specified, skipping backup")

        for uid in uids:
            conn.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        conn.expunge()
        syslog.syslog("Deleted {} e-mails".format(len(uids)))
    else:
        syslog.syslog("No old e-mails found")

    conn.close()
    conn.logout()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-config", nargs="+", type=argparse.FileType("r"))

    args = parser.parse_args()

    for conf in args.config:
        syslog.syslog("Processing configuration '{}'".format(conf.name))
        cp = configparser.ConfigParser()
        cp.read_string(conf.read())
        Process(cp)
