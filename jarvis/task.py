# SPDX-License-Identifier: GPL-3.0-or-later
"""Public action progress. A completed reply is never evidence of a successful action."""
import re
import threading


def control_step(command):
    op = command.get('op', '')
    labels = {
        'windows': ('Find the window', 'observation'),
        'screenshot': ('Check the screen', 'observation'),
        'inspect_app': ('Inspect app controls', 'observation'),
        'config_read': ('Read settings', 'observation'),
        'undo_list': ('Check restore points', 'observation'),
        'config_write': ('Update settings', 'action'),
        'undo_restore': ('Restore settings', 'action'),
        'focus': ('Focus the window', 'action'),
        'move': ('Move to the target', 'observation'),
        'click': ('Click the target', 'action'),
        'drag': ('Drag the target', 'action'),
        'scroll': ('Scroll the page', 'action'),
        'type': ('Enter text', 'action'),
        'key': ('Use a shortcut', 'action'),
        'accessible_action': ('Update the text field' if command.get('actionName') == 'set_text' else 'Use the app control', 'action'),
    }
    if op == 'browser':
        verb = (command.get('args') or [''])[0]
        if verb in ('snapshot', 'screenshot', 'get', 'find'):
            return 'Check the page', 'observation'
        return {'open': 'Open the page', 'fill': 'Fill the field', 'click': 'Click the page control'}.get(verb, 'Use the browser'), 'action'
    return labels.get(op, ('Use the computer', 'action'))


def control_evidence(command, result):
    """Only explicit broker readbacks can establish verification; screenshots cannot."""
    op = command.get('op')
    if op == 'config_write' and (result.get('verified') is True or result.get('unchanged') is True):
        return 'File contents checked after the update'
    if op == 'undo_restore' and result.get('verified') is True:
        return 'Restored file contents checked'
    if op == 'accessible_action' and command.get('actionName') == 'set_text' and result.get('verified') is True:
        return 'Text field read back and matched'
    if op == 'focus' and result.get('focused') == command.get('window') and command.get('window'):
        return 'Active window checked'
    return ''


class TaskProgress:
    def __init__(self):
        self.lock = threading.RLock()
        self.begin('')

    def begin(self, turn):
        with self.lock:
            self.turn = turn
            self.state = 'running' if turn else 'idle'
            self.steps = {}
            self.wrappers = {}
            self.overflow = False

    def record(self, identity, label, kind='action', state='running', evidence='', source='control'):
        with self.lock:
            if self.state != 'running':
                return
            key = source + ':' + str(identity)
            if key not in self.steps and len(self.steps) >= 200:
                self.overflow = True
                return
            self.steps[key] = dict(id=key, label=str(label)[:100], kind=kind, state=state,
                                   evidence=str(evidence)[:200], source=source)

    def tools(self, tools):
        with self.lock:
            if self.state != 'running':
                return
            for index, tool in enumerate(tools):
                name = str(tool.get('name', 'tool'))
                identity = tool.get('id') or str(index) + ':' + name
                state = tool.get('status', 'running')
                is_control = ('jarvis' in name.lower() and 'computer' in name.lower()) or name.lower() == 'computer'
                if is_control:
                    if len(self.wrappers) < 200 or identity in self.wrappers:
                        self.wrappers[identity] = state
                    else:
                        self.overflow = True
                    continue
                verb = re.split(r'[_:.]+', name.lower())[-1]
                observation = verb in ('read', 'cat', 'list', 'ls', 'grep', 'rg', 'find', 'search', 'glob')
                label = {'read': 'Read the file', 'edit': 'Edit the file', 'write': 'Write the file',
                         'bash': 'Run the command', 'shell': 'Run the command', 'exec': 'Run the command',
                         'search': 'Search for information', 'grep': 'Find matching text', 'list': 'List available items'}.get(verb, 'Use ' + name.replace('_', ' ')[:70])
                self.record(identity, label, 'observation' if observation else 'action',
                            'failed' if state == 'error' else 'observed' if state == 'complete' and observation else 'performed' if state == 'complete' else 'running', source='agent')

    def finish(self, status):
        with self.lock:
            if self.state != 'running':
                return self.snapshot()
            # Adapter tool IDs differ from MCP request IDs. Count acknowledged
            # calls as coverage, but never use their text output as proof.
            covered = sum(s['source'] == 'control' for s in self.steps.values())
            missing = max(0, len(self.wrappers) - covered)
            for index in range(missing):
                self.record('unobserved-' + str(index), 'Computer action', state='performed', source='adapter')
            failed = any(s['state'] == 'failed' for s in self.steps.values()) or 'error' in self.wrappers.values()
            actions = [s for s in self.steps.values() if s['kind'] == 'action']
            pending = any(s['state'] == 'running' for s in self.steps.values()) or 'running' in self.wrappers.values()
            if status == 'stopped':
                self.state = 'stopped'
            elif status == 'error':
                self.state = 'error'
            elif failed or pending or self.overflow:
                self.state = 'review'
            elif actions and all(s['state'] == 'verified' for s in actions):
                self.state = 'verified'
            elif actions:
                self.state = 'review'
            else:
                self.state = 'answered'
            for step in self.steps.values():
                if step['state'] == 'running':
                    step['state'] = 'stopped' if self.state == 'stopped' else 'unconfirmed'
            return self.snapshot()

    def snapshot(self):
        with self.lock:
            steps = list(self.steps.values())
            active = next((s for s in reversed(steps) if s['state'] == 'running'), None)
            label = {'idle': '', 'running': active['label'] if active else 'Working through your request',
                     'verified': 'Actions verified', 'review': 'Review the result', 'answered': 'Reply ready',
                     'stopped': 'Stopped', 'error': 'Couldn’t finish'}[self.state]
            detail = {'verified': 'Action results matched their checks.',
                      'review': 'Some results still need checking. Open the conversation for details.',
                      'answered': '', 'stopped': 'Completed actions are kept.', 'error': 'Open the conversation for details.'}.get(self.state, '')
            return dict(turn=self.turn, state=self.state, label=label, detail=detail,
                        steps=[dict(s) for s in steps[-12:]], total=len(steps),
                        checked=sum(s['state'] == 'verified' for s in steps), truncated=self.overflow or len(steps) > 12)
