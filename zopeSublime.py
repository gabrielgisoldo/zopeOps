import sublime
import sublime_plugin
import subprocess as sub
import re
from time import sleep


class ZopeSublime(sublime_plugin.EventListener):
    """Plugin for sublime text 3."""

    def on_post_save_async(self, view):
        """Run after save on another thread."""
        self.settings = sublime.load_settings('zopeSublime.sublime-settings')

        self.type_ops = self.settings.get('type_ops', 'restart')
        self.diff_days = self.settings.get('diff_days', "1")
        self.show_log = self.settings.get('show_log', False)
        self.simple_alert = self.settings.get('simple_alert', False)
        self.wait_time = self.settings.get('wait_time', 3)
        self.extensions = self.settings.get('extensions', [])
        self.syntaxes = self.settings.get('syntaxes', [])
        self.operations = self.settings.get('ops', [])
        self.log_output = None

        if not self.operations or not self.check_operations():
            raise Exception("Not configured!")

        syntax = view.settings().get('syntax').split('/')[-1]
        file = view.file_name().split('/')[-1]
        path = '/'.join(view.file_name().split('/')[:-1]) + '/'

        if self.extensions and file.split('.')[-1] not in self.extensions:
            return

        if self.syntaxes and syntax.split('.')[0] not in self.syntaxes:
            return

        for item in self.operations:
            if item['zope_folder'] and item['zope_folder'][-1] != '/':
                item['zope_folder'] += '/'

            file_in_path = False
            for directory in item['Directories']:
                if path.find(directory) >= 0:
                    file_in_path = True
                    break

            if not file_in_path:
                continue

            self.exec_zope_ops(ops=item)

            self.check_log(ops=item)

        # sublime.active_window().show_input_panel(
        #     "Zope Ops:", self.type_ops, self.select_ops, None, None)

        # sublime.message_dialog(file)
        # sublime.message_dialog(syntax)

    def check_operations(self):
        """Check if the configuration is ok."""
        for item in self.operations:
            if not item["zope_folder"] and not item["zopectl"]:
                return False
        return True

    def exec_zope_ops(self, ops):
        """Execute zope ops."""
        if ops['zopectl']:
            sub.call([ops['zopectl'], self.type_ops, self.diff_days])
        else:
            sub.call([ops['zope_folder'] + 'bin/zopectl', self.type_ops])

    def check_log(self, ops):
        """Check zope's event log."""
        if self.show_log and ops['zope_folder']:
            sleep(self.wait_time)

            proc = sub.Popen(
                ['/bin/tail', '-n 50', ops['zope_folder'] + 'log/event.log'],
                stdout=sub.PIPE, stderr=sub.PIPE, universal_newlines=True)

            self.log_output = proc.communicate()[0]

            self.log_output = re.sub(r"-+(?=\n)+\n", '', self.log_output)

            window = sublime.active_window()
            output = window.get_output_panel('log_output_panel')

            output.set_read_only(False)
            output.run_command('help_message',
                               {'docstring': self.log_output})

            output.set_read_only(True)
            window.run_command('show_panel',
                               {'panel': 'output.log_output_panel'})

        elif self.simple_alert and ops['zope_folder']:
            sleep(self.wait_time)

            proc = sub.Popen(
                ['/bin/tail', '-n 50', ops['zope_folder'] + 'log/event.log'],
                stdout=sub.PIPE, stderr=sub.PIPE)

            self.log_output = str(proc.communicate()[0], 'iso-8859-1')

            if re.findall(r'\d+:\d+:\d+ ERROR', self.log_output):
                sublime.error_message("Found ERROR on operation.")

            else:
                last_line = self.log_output.split('\n')[-2]
                print(last_line)

                if last_line.find('INFO Zope Ready to handle requests') >= 0:
                    sublime.message_dialog("Ops was Successful")
        else:
            sublime.message_dialog("Done")
