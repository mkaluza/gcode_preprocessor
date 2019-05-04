#!/usr/bin/env python

import sys
import os
import re

label_re = re.compile(r"^(?:(\w+):|[oO](\d+))\s*$")
comment_re = re.compile(r"^[;(]")

m_re = re.compile(r"\bM(?P<number>\d+)", re.I)
#REPEAT label P###
repeat_re = re.compile(r"\bREPEAT\s+(?P<label>\w+)", re.I)
repeat_num_re = re.compile(r"\bREPEAT.*P\s*=?\s*(?P<num>\d+)", re.I)

gotof_re = re.compile(r"\bGOTOF\s+(?P<label>\w+)", re.I)

subprogram_call_label_re = re.compile(r"\bM98.*?[^P](\w+)", re.I)
subprogram_call_fanuc_re = re.compile(r"\bM98.*?P(\d+)", re.I)



M6_lines = ["(M6 macro expansion here)"]


def first(items):
	for i in items:
		if i != None:
			return i


def find_labels(lines):
	labels = {}
	for number, line in enumerate(lines):
		match = label_re.match(line)
		if not match: continue
		name = first(match.groups())
		if name in labels:
			raise ValueError("duplicate label name: %s" % name)
		labels[name] = number
	return labels


def process_m_code(number, line, lines, labels):
	number = int(number)
	if number == 6:
		#toolchange
		return process_lines(M6_lines), False
	elif number == 30:
		#end of subprogram
		return [line], True
	elif number == 98:
		#call subprogram
		match = subprogram_call_fanuc_re.match(line)
		if not match:
			match = subprogram_call_label_re.match(line)
		if not match:
			raise ValueError("Invalid M98 call: \"%s\"" % line)
		name = match.groups()[0]
		if name not in labels:
			raise ValueError("Label not found: %s" % name)
		target = labels[name]
		return process_lines(lines[target:]), False
	elif number == 99:
		#return from subprogram
		return [], True
	else:
		return [line]

def check_label(match, labels):
	label = match.groupdict()["label"]
	if label not in labels:
		raise ValueError("Label not found: %s" % label)
	return label, labels[label]


def process_lines(lines):
	result = []
	labels = find_labels(lines)
	skip_until = -1

	for number, line in enumerate(lines):
		if number < skip_until: continue
		line = line.strip()

		#skip comment
		if comment_re.match(line):
			result.append(line)
			continue

		#M codes processing
		m = m_re.match(line)
		if m:
			m, exit = process_m_code(m.groupdict()["number"], line, lines, labels)
			result.extend(m)
			if exit: break
			continue

		#REPEAT processing
		m = repeat_re.match(line)
		if m:
			label, target = check_label(m, labels)
			if target > number:
				raise ValueError("line %d: REPEAT only allowed backwards" % (number+1,))

			num = repeat_num_re.match(line)
			if num:
				num = int(num.groupdict()["num"])
			else:
				num = 1

			result.extend(process_lines(lines[target:number]) * num)
			continue

		#GOTOF processing
		m = gotof_re.match(line)
		if m:
			label, target = check_label(m, labels)
			if target < number:
				raise ValueError("line %d: GOTOF requires forward jump" % (number+1,))
			skip_until = target
			continue

		#skip labels
		if label_re.match(line): continue

		result.append(line)

	return result


def process_file(name):
	with open(name, 'r') as f:
		lines = f.readlines()

	return process_lines(lines)


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "gcode file name required"
		sys.exit(1)
	res = process_file(sys.argv[1])

	for l in res:
		print l
