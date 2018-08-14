Delete-old-emails
=================

This script deletes old emails from an IMAP mailbox. Optionally, it can backup the emails before deleting them.

Configuration format
--------------------

```ini
[mailbox]
server = mymail.server.com
username = your-email@example.com
password = swordfish

[backup]
type = Maildir
path = /tank/mail/your-email_example_com/.backup/

[options]
min_age = 28
```

The `[backup]` block is optional. `Maildir` is the only supported backup type.