#!/usr/bin/env python

# SMS XML to HTML
# By Christopher Mitchell, Ph.D.
# https://github.com/smsxml2html

import os,sys
from lxml import etree
import argparse
import base64
import re, string
import time, datetime

STYLESHEET_TEMPLATE = """
.msg_date {
	font-family: 'Courier New', monospaced;
	font-size: 0.75em;
	color: #600000;
	white-space: nowrap;
}
.msg_sender_1, .msg_sender_137 {
	font-family: 'Courier New', monospaced;
	font-size: 0.75em;
	color: #000060;
	white-space: nowrap;
}
.msg_sender_2, .msg_sender_151 {
	font-family: 'Courier New', monospaced;
	font-size: 0.75em;
	color: #006000;
	white-space: nowrap;
}
.mms_img {
	max-height: 50vh;
	border: 0;
}
.month_convos tr {
	vertical-align: text-top;
}
.month_convos td {
	vertical-align: text-top;
}
.toc {
	-moz-column-width: 30em;
	-webkit-column-width: 30em;
	column-width: 30em;
}
"""

class SMSMsg:
	def __init__(self, timestamp, text, type, extra):
		self.timestamp = timestamp
		self.text = text
		self.type = type
		self.extra = extra
		
class MMSMsg(SMSMsg):
	def __init__(self, timestamp = 0, text = "", type = 1, extra = {}):
		SMSMsg.__init__(self, timestamp, text, type, extra)
		self.images = []
		
	def addImage(self, base_path, timestamp, name, mime, data):
		if mime == 'image/png':
			ext = 'png'
		elif mime == 'image/jpeg':
			ext = 'jpg'
		elif mime == 'image/gif':
			ext = 'gif'
		else:
			print("Unknown MIME type '%s' for MMS content; omitting content" % (mime))
			return

		name = str(timestamp) + re.sub('[^A-Za-z0-9_.-]+', '', name) + '.' + ext
		out_path = os.path.join(base_path, name)
		with open(out_path, 'wb') as f:
			try:
				f.write(base64.b64decode(data))
			except TypeError:
				print("Failed to decode base64 for image %s" % (name))
				return
		self.images.append(name)

def parseCarrierNumber(number):
	number = re.sub('[^0-9]', '', number)
	if len(number) == 10:
		number = '1' + number
	return number
	
def parseConversations(root, conversations, users, base_path, carrier_number):
	messages = 0
	for child in root:
		messages += parseConversations(child, conversations, users, base_path, carrier_number)
		if child.tag == 'sms':
			address = parseCarrierNumber(child.attrib['address'])
			date    = int(child.attrib['date'])		# Epoch timestamp
			type    = child.attrib['type']			# 2 = outgoing, 1 = incoming
			name    = child.attrib['contact_name']
			body    = child.attrib['body']
			
			save_msg = SMSMsg(date, body, type, {})
			try:
				conversations[address][date] = save_msg
			except KeyError:
				conversations[address] = {date: save_msg}
			messages += 1
				
			if name and address not in users:
				users[address] = name
		
		elif child.tag == 'mms':
			save_msg = MMSMsg()
			date = int(child.attrib['date'])		# Epoch timestamp
			addresses = {}
			for mms_child in child:
				if mms_child.tag == 'parts':
					for part_child in mms_child:
						if part_child.tag == 'part':
							part_name = part_child.attrib['name']
							part_data = part_child.attrib['data'] if 'data' in part_child.attrib else ""
							part_text = part_child.attrib['text'] if 'text' in part_child.attrib else ""
							part_mime = part_child.attrib['ct']
							if "image" in part_mime:
								save_msg.addImage(base_path, date, part_name, part_mime, part_data)
							elif "text" in part_mime:
								save_msg.text += part_text
				elif mms_child.tag == 'addrs':
					for addr_child in mms_child:
						if addr_child.tag == 'addr':
							parsed_child_address = parseCarrierNumber(addr_child.attrib['address'])
							if carrier_number not in parsed_child_address:
								addresses[parsed_child_address] = addr_child.attrib['type']
				for address, type in addresses.iteritems():
					save_msg.address = address
					save_msg.type = type
					save_msg.timestamp = date
					try:
						conversations[address][date] = save_msg
					except KeyError:
						conversations[address] = {date: save_msg}
					messages += 1
							
	return messages			# Count of messages
				
def dumpConversations(base_path, conversations, carrier_number):
	files = 0
	
	with open(os.path.join(base_path, 'stylesheet.css'), 'w') as f:
		f.write(STYLESHEET_TEMPLATE)
	
	for address, conversation in conversations.iteritems():
		output_path = os.path.join(base_path, address + '.html')

		with open(output_path, 'w') as f:
		
			f.write('<html><head><link rel="stylesheet" type="text/css" href="stylesheet.css" /></head><body>' + "\n")

			# Generate the TOC
			prev_month_year = ""
			months = []
			month_amap = {}
			for date in sorted(conversation.keys()):
				msg = conversation[date]
				dt = datetime.datetime.utcfromtimestamp(msg.timestamp / 1000)
				month_year = dt.strftime('%B %Y')
				if month_year != prev_month_year:
					month_year_short = dt.strftime('%y%m')
					months.append(month_year)
					month_amap[month_year] = month_year_short
				prev_month_year = month_year
					
			# Generate the TOC
			f.write('<div class="toc"><ul>')
			for month_year in months:
				f.write('<li><a href="#%s">%s</a>' % (month_amap[month_year], month_year))
			f.write('</ul></div>')

			# Generate the body
			prev_month_year = ""
			for date in sorted(conversation.keys()):
				msg = conversation[date]
				dt = datetime.datetime.utcfromtimestamp(msg.timestamp / 1000)
				month_year = dt.strftime('%B %Y')
				if month_year != prev_month_year:
					if prev_month_year != '':
						f.write('</table>')
					f.write('<a name="%s"></a>' % (month_amap[month_year]))
					f.write("<h2>%s</h2>\n" % (month_year))
					f.write('<table class="month_convos">')
				f.write('<tr>')
				f.write('<td><b><span class="msg_date">%s</span></td><td><span class="msg_sender_%s">%s %s</span></b></td><td>%s' % (dt.strftime('%m/%d/%y %I:%M:%S%p'), msg.type, '<<' if msg.type == "1" else '>>', address if msg.type == "1" else carrier_number, msg.text.encode('utf8')))
				if isinstance(msg, MMSMsg):
					f.write('<br />')
					for image in msg.images:
						f.write('<a href="%s"><img class="mms_img" src="%s" /></a> ' % (image, image))
				f.write('</td></tr>')
				f.write("</tr>\n")
				prev_month_year = month_year

			f.write("</table>\n")
			f.write("</body></html>")
		files += 1
	return files

def main():
	# parse options and get results
	parser = argparse.ArgumentParser(description='Turns SMS Backup and Restore XML into HTML conversations with images')
	parser.add_argument('input', metavar='input', nargs='+', type=str, \
				help='Input XML file')
	parser.add_argument('-o', '--output', type=str, required=True, \
				help='Output directory')
	parser.add_argument('-n', '--number', type=str, required=True, \
				help='User\'s carrier number')
	args = parser.parse_args()
	carrier_number = parseCarrierNumber(args.number)
	
	messages = 0
	conversations = {}
	users = {}
	for input in args.input:
		# Open the input file
		from lxml.etree import XMLParser, parse
		lxml_parser = XMLParser(huge_tree = True)
		tree = etree.parse(input, parser = lxml_parser)
		root = tree.getroot()
		
		# Parse it out
		try:
			os.mkdir(args.output)
		except OSError:
			pass					# Already exists
			print("Parsing conversations from %s" % (input))
		messages += parseConversations(root, conversations, users, args.output, carrier_number)
		
	print("Parsed %d messages in %d conversations with %d known user names" % (messages, len(conversations), len(users)))
	files = dumpConversations(args.output, conversations, carrier_number)
	print("Dumped messages to %d conversation HTML files" % (files))
	
	sys.exit(0)
	
if __name__ == '__main__':
	main()