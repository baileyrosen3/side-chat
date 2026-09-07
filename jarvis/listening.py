# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, testable listening policies; these do not identify a speaker."""
import re
from collections import deque


def pause_seconds(text, base, adaptive=True):
    """Allow a little more time for an unfinished English phrase, not every turn."""
    words=re.findall(r"[a-z']+",text.lower())
    if not adaptive or not words:return base
    if words[-1] in {'and','or','but','because','to','the','a','an','with','for','of','my','your',
                     'is','are','was','please','can','could','would','um','uh','so','actually'}:
        return max(base,1.0)
    return base


class NoiseFloor:
    """Reject very faint false starts; never amplify or gate speech already underway."""
    def __init__(self):self.quiet=deque(maxlen=160)

    def observe(self, rms):self.quiet.append(max(0,float(rms)))

    def accepts(self, rms, strong=False):
        if not strong:return True
        floor=sorted(self.quiet)[len(self.quiet)//4] if self.quiet else 0
        return rms>=max(.0015,min(.015,floor*2))
