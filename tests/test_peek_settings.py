import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backend import Bridge
from peek.control import Control
from peek.settings import DEFAULTS,validate,scope_instruction


class SettingsTests(unittest.TestCase):
    def test_fresh_peek_defaults_to_voxtype_manual_toggle(self):
        self.assertEqual(DEFAULTS['asrModel'],'voxtype')
        self.assertFalse(DEFAULTS['handsFree'])
        self.assertFalse(DEFAULTS['wakeEnabled'])

    def test_validation_is_atomic_and_rejects_bad_ranges_types_paths(self):
        for values in ({'asrThreads':0},{'volume':float('nan')},{'handsFree':'false'},
                       {'scope':'hidden'},{'asrThreads':2.5},{'ttsModel':'cloud'},
                       {'asrModel':'parakeet-unified','modelPath':'/missing/peek-model'},
                       {'speechRate':1.3}):
            original=dict(DEFAULTS)
            with self.assertRaises(ValueError):validate(original,values)
            self.assertEqual(original,DEFAULTS)

    def test_engine_voice_matching_and_persistence_without_arming_microphone(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Bridge(folder,lambda _:None)
            try:
                b.dispatch({'action':'peek_settings','settings':{'asrThreads':6,'endSilence':.85,'handsFree':False,'volume':.8}})
                self.assertIsNone(b.peek.voice)
                self.assertFalse(b.peek.enabled)
            finally:b.close()
            b=Bridge(folder,lambda _:None)
            try:
                self.assertEqual(b.peek.prefs['asrThreads'],6)
                self.assertEqual(b.peek.prefs['endSilence'],.85)
                self.assertFalse(b.peek.prefs['handsFree'])
                self.assertEqual(b.peek.prefs['volume'],.8)
            finally:b.close()
        prefs=validate(DEFAULTS,{'ttsModel':'kokoro'},check_files=False)
        self.assertEqual(prefs['voice'],'af_heart')
        self.assertEqual(validate(prefs,{'ttsModel':'pocket'},check_files=False)['voice'],'alba')

    def test_voxtype_mode_requires_manual_activation(self):
        prefs=validate(DEFAULTS,{'asrModel':'voxtype','handsFree':False,'wakeEnabled':False},check_files=False)
        self.assertEqual(prefs['asrModel'],'voxtype')
        self.assertEqual(validate(DEFAULTS,{'asrModel':'voxtype'},check_files=False)['asrModel'],'voxtype')
        for values in ({'asrModel':'voxtype','handsFree':True},
                       {'asrModel':'voxtype','wakeEnabled':True,'handsFree':False}):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError,'manual push-to-talk'):
                validate(DEFAULTS,values,check_files=False)

    def test_busy_model_or_mode_change_does_not_cancel_task_or_save(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Bridge(folder,lambda _:None)
            try:
                b.busy=True;b.peek.state['enabled']=True
                before=dict(b.peek.prefs)
                for values in ({'asrThreads':6},{'scope':'browser'}):
                    with self.assertRaises(ValueError):b.peek.dispatch({'action':'peek_settings','settings':values})
                    self.assertEqual(b.peek.prefs,before)
                    self.assertFalse(b.cancelled.is_set())
            finally:b.busy=False;b.close()

    def test_each_native_prompt_uses_current_scope_without_changing_visible_text(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Bridge(folder,lambda _:None)
            try:
                b.peek.state['enabled']=True
                chat={'native':{},'messages':[]};user={'text':'Open Google'}
                desktop,_=b.native_prompt(chat,user)
                b.peek.prefs['scope']='browser'
                browser,_=b.native_prompt(chat,user)
                self.assertIn('DESKTOP',desktop);self.assertIn('BROWSER',browser)
                self.assertIn('visible default Omarchy browser',desktop)
                self.assertIn('isolated headless',browser)
                self.assertEqual(user['text'],'Open Google')
            finally:b.close()


class BrowserRoutingTests(unittest.TestCase):
    def setUp(self):
        with patch.object(Control,'watch_input',lambda _:None):self.c=Control(lambda _:None)
        self.c.handle({'op':'_configure','enabled':True,'scope':'desktop'})
    def tearDown(self):self.c.close()

    def test_desktop_open_uses_omarchy_default_launcher_and_never_agent_browser(self):
        with patch('peek.control.run',return_value=b'zen.desktop\n') as run,patch('peek.control.hypr',return_value={'class':'zen'}):
            result=self.c.browser({'args':['open','https://www.google.com']},self.c.epoch)
        self.assertEqual(result['defaultBrowser'],'zen.desktop')
        self.assertEqual(result['scope'],'desktop')
        self.assertEqual([call.args[0] for call in run.call_args_list],
                         [['xdg-settings','get','default-web-browser'],['omarchy','launch','browser','https://www.google.com']])

    def test_desktop_rejects_dom_and_non_web_urls(self):
        for args in (['snapshot','-i'],['open','file:///etc/passwd'],['open','--headless'],['open','javascript:alert(1)']):
            with patch('peek.control.run') as run:
                with self.assertRaises(ValueError):self.c.browser({'args':args},self.c.epoch)
                run.assert_not_called()

    def test_browser_rejects_desktop_input_and_launch_overrides(self):
        self.c.handle({'op':'_configure','enabled':True,'scope':'browser'})
        with self.assertRaises(ValueError):self.c.handle({'op':'type','text':'no'})
        for args in (['open','https://example.com','--headed'],['open','https://example.com','--cdp=9222']):
            with self.assertRaises(ValueError):self.c.browser({'args':args},self.c.epoch)

    def test_switching_to_desktop_closes_only_the_owned_browser_session(self):
        self.c.scope='browser';self.c.browser_started=True
        with patch('peek.control.run') as run:
            self.c.handle({'op':'_configure','enabled':False,'scope':'desktop'})
            self.assertEqual(run.call_args.args[0][-3:],['--session',self.c.browser_session,'close'])
        self.assertFalse(self.c.browser_started)


if __name__=='__main__':unittest.main()
