Delete-old-emails
=================

This script deletes old emails from an IMAP mailbox and optionally downloads them locally for backup. 

Configuration format
--------------------

.. code::

    [mailbox]
    server = mymail.server.com
    username = your-email@example.com
    password = swordfish

    [backup]
    type = Maildir
    path = /tank/mail/your-email_example_com/.backup/

    [options]
    min_age = 28

The ``[backup]`` block is optional. Only ``Maildir`` is supported as the backup type.