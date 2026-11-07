"""Mod Settings Extended Patcher - window"""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mse_core as core  # noqa: E402

BG, PANEL, FG, DIM, GOLD, OK, ERR = '#16130f', '#221d17', '#e8dfcf', '#9c9284', '#deb25c', '#8fc27a', '#e07a6a'
FONT = ('Segoe UI', 10)


class App:
    def __init__(self, root):
        self.root = root
        core.log_start()
        self.game = core.find_game_dir()
        core.log_report(self.game, 'found automatically' if self.game else 'not found')
        self.rtg = None
        root.title('Mod Settings Extended Patcher %s' % core.VERSION)
        root.configure(bg=BG)
        root.resizable(False, False)
        tk.Label(root, text='Mod Settings Extended Patcher', bg=BG, fg=GOLD, font=('Segoe UI Semibold', 15)) \
            .pack(anchor='w', padx=18, pady=(16, 0))
        tk.Label(root, text='Makes Mod Settings Extended work together with %s.' % core.RTG_NAME, bg=BG, fg=DIM,
                 font=FONT).pack(anchor='w', padx=18, pady=(2, 12))

        row = tk.Frame(root, bg=BG)
        row.pack(fill='x', padx=18)
        tk.Label(row, text='Game folder', bg=BG, fg=DIM, font=FONT).pack(side='left')
        self.path = tk.Label(row, text='', bg=PANEL, fg=FG, font=FONT, anchor='w', width=58, padx=8, pady=4)
        self.path.pack(side='left', padx=8)
        self._button(row, 'Browse...', self.browse).pack(side='left')

        self.box = tk.Frame(root, bg=PANEL, padx=14, pady=10)
        self.box.pack(fill='x', padx=18, pady=12)
        self.lines = []
        for _ in range(4):
            lab = tk.Label(self.box, text='', bg=PANEL, fg=FG, font=FONT, anchor='w', justify='left', wraplength=640)
            lab.pack(fill='x', anchor='w', pady=1)
            self.lines.append(lab)

        btns = tk.Frame(root, bg=BG)
        btns.pack(fill='x', padx=18)
        self.b_combine = self._button(btns, 'Combine with Real-Time Graphics', self.combine, primary=True)
        self.b_combine.pack(side='left')
        self.b_restore = self._button(btns, 'Restore standard MSE', self.restore)
        self.b_restore.pack(side='left', padx=10)
        self.b_log = self._button(btns, 'Open log', self.open_log)
        self.b_log.pack(side='right')

        self.msg = tk.Label(root, text='', bg=BG, fg=FG, font=FONT, anchor='w', justify='left', wraplength=680)
        self.msg.pack(fill='x', padx=18, pady=(12, 4))
        tk.Label(root, text='Run this again after updating either mod. The game must be closed.', bg=BG, fg=DIM,
                 font=('Segoe UI', 9)).pack(anchor='w', padx=18, pady=(0, 14))
        self.refresh()

    def _button(self, parent, text, cmd, primary=False):
        return tk.Button(parent, text=text, command=cmd, font=FONT, relief='flat', cursor='hand2', padx=14, pady=5,
                         bg=GOLD if primary else PANEL, fg='#1a1510' if primary else FG,
                         activebackground='#f0c878' if primary else '#2e271f',
                         activeforeground='#1a1510' if primary else FG, disabledforeground='#6b6357')

    def line(self, i, text, color=FG):
        self.lines[i].configure(text=text, fg=color)

    def say(self, text, color=FG):
        self.msg.configure(text=text, fg=color)

    def browse(self):
        d = filedialog.askdirectory(title='Select The Witcher 3 folder', initialdir=self.game or '/')
        if d:
            if core.is_game_dir(d):
                self.game = os.path.normpath(d)
                self.say('')
                core.log_report(self.game, 'chosen with Browse')
            else:
                core.log('Browse: not a game folder: %s' % d)
                self.say('That folder is not The Witcher 3 (no content\\content0 or bin folder in it).', ERR)
            self.refresh()

    def refresh(self):
        self.rtg = None
        for i in range(4):
            self.line(i, '')
        can_combine = can_restore = False
        if not self.game:
            self.path.configure(text='Not found - use Browse...')
            self.line(0, 'The Witcher 3 was not found (Steam, GOG and Epic were checked).', ERR)
        else:
            self.path.configure(text=self.game)
            if not core.mse_installed(self.game):
                self.line(0, 'Mod Settings Extended: not installed (Mods\\%s)' % core.MSE_DIR, ERR)
            else:
                state = core.current_state(self.game)
                self.line(0, 'Mod Settings Extended: installed', OK)
                self.line(1, 'Menu file in use: ' + {'combined': 'combined with Real-Time Graphics',
                                                     'standard': 'standard (Mod Settings Extended only)',
                                                     'missing': 'missing (reinstall Mod Settings Extended)'}[state],
                          OK if state == 'combined' else (ERR if state == 'missing' else FG))
                others = core.other_menu_mods(self.game)
                rtg = [o for o in others if o[2]]
                if rtg:
                    self.rtg = rtg[0]
                    self.line(2, '%s: found (Mods\\%s)' % (core.RTG_NAME, rtg[0][0]), OK)
                    can_combine = True
                else:
                    self.line(2, '%s: not installed' % core.RTG_NAME, DIM)
                rest = [o[0] for o in others if not o[2]]
                if rest:
                    self.line(3, "Not supported, Mod Settings Extended's menu is used instead: " + ', '.join(rest),
                              DIM)
                can_restore = state != 'standard'
        self.b_combine.configure(state='normal' if can_combine else 'disabled')
        self.b_restore.configure(state='normal' if can_restore else 'disabled')

    def _run(self, job_name, job, done):
        core.log('%s pressed' % job_name)
        if core.game_running():
            core.log('Refused: The Witcher 3 is running.')
            self.say('Close The Witcher 3 first, then try again.', ERR)
            return
        self.b_combine.configure(state='disabled')
        self.b_restore.configure(state='disabled')
        self.say('Working...', DIM)

        def work():
            try:
                job()
                res = (done, OK)
            except core.PatchFailed as ex:
                core.log_exc()
                res = (str(ex) + ' Nothing was changed.', ERR)
            except PermissionError:
                core.log_exc()
                res = ('Windows refused the write. Close the game, or run the patcher as administrator.', ERR)
            except Exception as ex:
                core.log_exc()
                res = ('Unexpected error: %s: %s' % (type(ex).__name__, ex), ERR)
            core.log('Result: ' + res[0])
            core.log_report(self.game, 'after ' + job_name)
            self.root.after(0, lambda: (self.refresh(), self.say(*res)))
        threading.Thread(target=work, daemon=True).start()

    def combine(self):
        bp = self.rtg[1]
        self._run('Combine', lambda: core.combine(self.game, bp),
                  'Done. Both mods now share one menu file: T toggles transparency in the menus '
                  '(in the Mods list, T types into the search).' if core.has_t_toggle(bp) else
                  'Done. Both mods now share one menu file.')

    def open_log(self):
        if core.LOG_PATH and os.path.isfile(core.LOG_PATH):
            os.startfile(core.LOG_PATH)
        else:
            self.say("No log could be written (the patcher's folder and %TEMP% both refused it).", ERR)

    def restore(self):
        self._run('Restore', lambda: core.restore(self.game), 'Done. Mod Settings Extended uses its standard menu file again.')


def main():
    root = tk.Tk()
    app = App(root)

    def report(exc, val, tb):
        # a windowed exe has no console: an error in a button handler would otherwise do nothing visible
        import traceback
        core.log(''.join(traceback.format_exception(exc, val, tb)).rstrip())
        try:
            app.refresh()
        except Exception:
            pass
        app.say('Unexpected error: %s: %s (details in the log)' % (exc.__name__, val), ERR)
    root.report_callback_exception = report
    root.mainloop()


if __name__ == '__main__':
    main()
