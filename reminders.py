# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, deterministic local reminder parser. Every result is previewed in the UI."""
from datetime import datetime, timedelta
import math
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
DAY = r'(?:today|tomorrow|' + '|'.join(WEEKDAYS) + r'|\d{4}-\d{2}-\d{2})'
CLOCK = r'(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight)'
SUFFIX = re.compile(r'(?P<when>\bin\s+\d+\s+(?:seconds?|minutes?|hours?|days?)|\b(?:on\s+)?' + DAY + r'(?:\s+(?:at\s+)?' + CLOCK + r')?|\bat\s+' + CLOCK + r')\s*[.!]?$', re.I)


def local_zone():
    try:
        if os.environ.get('TZ'):
            return ZoneInfo(os.environ['TZ'].lstrip(':'))
        with Path('/etc/localtime').open('rb') as handle:
            return ZoneInfo.from_file(handle)
    except (OSError, ValueError, KeyError):
        return datetime.now().astimezone().tzinfo


def valid_due(value):
    if value in ('', None):
        return 0
    try:
        due = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Choose a valid reminder date.') from exc
    if not math.isfinite(due) or not 0 <= due <= 32_503_680_000:
        raise ValueError('Choose a valid reminder date.')
    return due


def parse(text, *, separate=False, now=None):
    text = str(text).strip()
    now = now or datetime.now(local_zone())
    match = SUFFIX.search(text)
    if not match:
        if separate and text:
            raise ValueError('Try “tomorrow at 3pm”, “Friday at 9am”, or “in 20 minutes”.')
        return {'body': text, 'due': 0, 'label': '', 'expression': ''}
    if separate and text[:match.start()].strip():
        raise ValueError('Use a date and time, such as “tomorrow at 3pm”.')
    expression = match['when'].lower().strip()
    relative = re.fullmatch(r'in\s+(\d+)\s+(second|minute|hour|day)s?', expression)
    if relative:
        amount = int(relative[1]) * {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}[relative[2]]
        if not 1 <= amount <= 366 * 86400:
            raise ValueError('Choose a reminder within the next year.')
        due = datetime.fromtimestamp(now.timestamp() + amount, now.tzinfo)
    else:
        parts = re.fullmatch(r'(?:on\s+)?(?P<day>' + DAY + r')?(?:\s*(?:at\s+)?(?P<clock>' + CLOCK + r'))?', expression, re.I)
        if not parts:
            raise ValueError('Choose a valid reminder date and time.')
        day, clock = parts['day'], parts['clock']
        date = now.date()
        if day == 'tomorrow':
            date += timedelta(days=1)
        elif day in WEEKDAYS:
            date += timedelta(days=(WEEKDAYS.index(day) - date.weekday()) % 7)
        elif day and day not in ('today', 'tomorrow'):
            try:
                date = datetime.strptime(day, '%Y-%m-%d').date()
            except ValueError as exc:
                raise ValueError('That date does not exist.') from exc
        hour, minute = 9, 0
        if clock:
            clock = clock.replace(' ', '').lower()
            if clock in ('noon', 'midnight'):
                hour = 12 if clock == 'noon' else 0
            else:
                time_match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', clock)
                hour, minute = int(time_match[1]), int(time_match[2] or 0)
                meridiem = time_match[3]
                if minute > 59 or hour > 23 or (meridiem and not 1 <= hour <= 12):
                    raise ValueError('Choose a valid time, such as 3pm or 15:30.')
                if meridiem:
                    hour = hour % 12 + (12 if meridiem == 'pm' else 0)
                elif ':' not in clock and 1 <= hour <= 7:
                    # Bare afternoon hours are shown explicitly in the preview.
                    hour += 12
        due = datetime(date.year, date.month, date.day, hour, minute, tzinfo=now.tzinfo)
        if due.timestamp() <= now.timestamp():
            if day in WEEKDAYS:
                due += timedelta(days=7)
            elif day is None:
                due += timedelta(days=1)
            else:
                raise ValueError('That time has passed. Choose a future reminder.')
        roundtrip = datetime.fromtimestamp(due.timestamp(), now.tzinfo)
        if roundtrip.replace(tzinfo=None) != due.replace(tzinfo=None):
            raise ValueError('That local time is skipped by daylight saving. Choose another time.')
    if due.timestamp() - now.timestamp() > 366 * 86400:
        raise ValueError('Choose a reminder within the next year.')
    return {'body': text[:match.start()].rstrip(' ,;') if not separate else '',
            'due': due.timestamp(), 'label': due.strftime('%a, %b %d · %-I:%M %p %Z'),
            'expression': text[match.start():].strip()}
