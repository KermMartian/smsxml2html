# smsxml2html
Turn SMS Backup and Restore SMS XML files into HTML transcripts
By Chistopher Mitchell, Ph.D.

This tool creates HTML transcripts of SMS/MMS conversations from
[Carbonite SMS Backup and Restore](https://www.carbonite.com/en/apps/call-log-sms-backup-restore)
backup files. It takes one or more XML files, separates them out into one-on-one conversations,
and emits each of those conversations as a separate HTML file. It also parses the URI-encoded
MMS images in these backups and produces picture files you can view, edit, and organize.

Usage
-----
  python smsxml2html.py -o <output_dir> -n <user_carrier_number> <input file> [<input file> ...]

  * <output_dir>: New directory into which to place HTML files and images
  * <user_carrier_number>: The carrier number of the SMS backups' owner, in 1NNNXXXYYYY format
  * <input file>: One or more XML backup files produced by SMS Backup and Restore.