"""Mod Settings Extended Patcher - core: merges MSE's menu changes onto Real-Time Graphics and HDR Menus Preview's
panel_ingamemenu.redswf, read from the player's own install, or rebuilds MSE's standard file from the game's."""
import glob
import json
import os
import re
import hashlib
import subprocess
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abcrt        # noqa: E402
import avm2verify   # noqa: E402
import cr2w         # noqa: E402
import fml_patch    # noqa: E402
import uw_map_patch as M  # noqa: E402
import w3bundle     # noqa: E402
import w3meta       # noqa: E402

VERSION = '1.4.2'
DEPOT = fml_patch.DEPOT
MSE_DIR = 'mod00000_ModSettingsExtended'
MSE_SCRIPT = os.path.join('content', 'scripts', 'local', 'FullModsList.ws')
# names only Real-Time Graphics' menu file has: its T hint (versions with the hotkey) / its text style store (all,
# version 6 "Original" too: no hotkey, folder modLiveGraphicsPreviewOriginal)
RTG_MARKS = (b'TOGGLE TRANSPARENCY', b'_previewOriginalTextStyles')
RTG_NAME = 'Real-Time Graphics and HDR Menus Preview'


class PatchFailed(Exception):
    pass


# ---- 1.2.1: the log. One file per run, next to the patcher (else %TEMP%): what the window decides from plus the
# details a bug report needs (game folder, every mod with the menu file and which one wins, versions found, errors).
LOG_NAME = 'ModSettingsExtendedPatcher-log.txt'
LOG_PATH = None


def _here():
    return os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))


def log_start():
    global LOG_PATH
    for d in (_here(), tempfile.gettempdir()):
        p = os.path.join(d, LOG_NAME)
        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write('Mod Settings Extended Patcher %s log, %s\n' % (VERSION, time.strftime('%Y-%m-%d %H:%M:%S')))
            LOG_PATH = p
            return p
        except OSError:
            pass
    return None


def log(msg=''):
    if not LOG_PATH:
        return
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write('[%s] %s\n' % (time.strftime('%H:%M:%S'), msg))
    except OSError:
        pass


def log_exc():
    log(traceback.format_exc().rstrip())


def documents_dir():
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return buf.value
    except Exception:
        pass
    return os.path.join(os.path.expanduser('~'), 'Documents')


def mods_settings():
    """{mod folder (lower case): priority} from Documents\The Witcher 3\mods.settings; None when there is no file"""
    out = {}
    p = os.path.join(documents_dir(), 'The Witcher 3', 'mods.settings')
    try:
        cur = None
        with open(p, encoding='utf-8', errors='replace') as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith('[') and ln.endswith(']'):
                    cur = ln[1:-1].lower()
                elif cur and ln.lower().startswith('priority='):
                    out[cur] = ln.split('=', 1)[1].strip()
    except OSError:
        return None
    return out


def _short_hash(data):
    return hashlib.sha256(data).hexdigest()[:12] if data else '-'


def log_report(game, how):
    """everything the window decides from, for this game folder"""
    try:
        log('Game folder: %s (%s)' % (game, how))
        if not game:
            return
        log('Game folder valid: %s; Mods folder exists: %s' % (is_game_dir(game), os.path.isdir(mods_dir(game))))
        log('Mod Settings Extended installed: %s (Mods\\%s)' % (mse_installed(game), MSE_DIR))
        bp = os.path.join(mse_content(game), 'blob0.bundle')
        d = entry_data(bp) if os.path.isfile(bp) else None
        log('MSE menu file: %s, state %s, sha %s' % (bp, current_state(game), _short_hash(d)))
        prio = mods_settings()
        log('mods.settings: %s' % ('not found' if prio is None else (prio or 'no priorities')))
        menu = [(MSE_DIR, bp, False)] + other_menu_mods(game)

        def key(m):
            v = (prio or {}).get(m[0].lower())
            if v is not None and v.lstrip('-').isdigit():
                return (0, int(v), m[0].lower())
            return (1, 0, m[0].lower())
        log('Mods that ship the menu file (panel_ingamemenu.redswf), in the order the game most likely picks (first wins; estimated from mods.settings Priority, lowest first, then folder name):')
        for i, (mod, b, rtg) in enumerate(sorted(menu, key=key)):
            if mod == MSE_DIR:
                kind = 'Mod Settings Extended'
            elif rtg:
                kind = 'Real-Time Graphics, ' + ('T toggle' if has_t_toggle(b) else 'no T toggle')
            else:
                kind = 'other'
            log('  %d. Mods\\%s  [%s]  %s, sha %s' % (i + 1, mod, kind, os.path.basename(b), _short_hash(entry_data(b))))
        if not any(r for _, _, r in menu):
            log('Real-Time Graphics was not recognized in any mod. If it is installed, its menu file may be a version '
                'this patcher does not know.')
        try:
            names = sorted(os.listdir(mods_dir(game)), key=str.lower)
            log('Mods folder (%d): %s' % (len(names), ', '.join(names)))
        except OSError as ex:
            log('Mods folder not readable: %s' % ex)
    except Exception:
        log_exc()


def is_game_dir(d):
    return bool(d) and os.path.isdir(os.path.join(d, 'content', 'content0')) and os.path.isdir(os.path.join(d, 'bin'))


def epic_install_dirs():
    """The Witcher 3 folders the Epic Games launcher knows: its install manifests (one JSON .item file per installed
    game) and LauncherInstalled.dat. Only a folder with the game's own exe counts. Only reads files."""
    pd = os.environ.get('PROGRAMDATA') or r'C:\ProgramData'
    locs = []
    for m in sorted(glob.glob(os.path.join(pd, 'Epic', 'EpicGamesLauncher', 'Data', 'Manifests', '*.item'))):
        try:
            with open(m, encoding='utf-8', errors='replace') as f:
                j = json.load(f)
            locs.append(j.get('InstallLocation') or '')
        except (OSError, ValueError, AttributeError):
            pass
    try:
        with open(os.path.join(pd, 'Epic', 'UnrealEngineLauncher', 'LauncherInstalled.dat'), encoding='utf-8',
                  errors='replace') as f:
            locs += [i.get('InstallLocation') or '' for i in json.load(f).get('InstallationList', [])]
    except (OSError, ValueError, AttributeError):
        pass
    out = []
    for d in locs:
        if d and any(os.path.isfile(os.path.join(d, 'bin', x, 'witcher3.exe')) for x in ('x64_dx12', 'x64')) \
                and os.path.normcase(os.path.normpath(d)) not in [os.path.normcase(os.path.normpath(o)) for o in out]:
            out.append(d)
    return out


def running_on_wine():
    """True under Wine or Proton (Linux, Steam Deck): Wine's ntdll exports wine_get_version, Windows' doesn't."""
    try:
        import ctypes
        return hasattr(ctypes.WinDLL('ntdll'), 'wine_get_version')
    except Exception:
        return False


def _unix_to_wine(path, root):
    """A Linux path from Steam's libraryfolders.vdf ("/home/deck/Games") as Wine shows it: Wine's Z: drive is the
    Linux root folder by default."""
    return os.path.join(root, *[x for x in path.split('/') if x])


def wine_steam_dirs(root='Z:\\'):
    """The Witcher 3 folders in the Linux Steam libraries, seen through Wine's Z: drive: native Steam
    (~/.local/share/Steam, ~/.steam/steam), Flatpak Steam, and every library listed in their libraryfolders.vdf
    (other drives, a Steam Deck's SD card). Only reads files."""
    steams = []
    homes = sorted(glob.glob(os.path.join(root, 'home', '*'))) + [os.path.join(root, 'root')]
    for h in homes:
        for rel in (('.local', 'share', 'Steam'), ('.steam', 'steam'), ('.steam', 'root'),
                    ('.var', 'app', 'com.valvesoftware.Steam', '.local', 'share', 'Steam'),
                    ('.var', 'app', 'com.valvesoftware.Steam', 'data', 'Steam')):
            s = os.path.join(h, *rel)
            if os.path.isdir(os.path.join(s, 'steamapps')):
                steams.append(s)
    libs = []
    for s in steams:
        libs.append(s)
        vdf = os.path.join(s, 'steamapps', 'libraryfolders.vdf')
        try:
            with open(vdf, encoding='utf-8', errors='replace') as f:
                paths = [re.sub(r'\\(.)', r'\1', m) for m in re.findall(r'"path"\s+"((?:[^"\\]|\\.)*)"', f.read())]
            libs += [_unix_to_wine(m, root) for m in paths if m.startswith('/')]
        except OSError:
            pass
    out, seen = [], set()
    for l in libs:
        g = os.path.join(l, 'steamapps', 'common', 'The Witcher 3')
        k = os.path.normcase(os.path.realpath(g))
        if k not in seen:
            seen.add(k)
            out.append(g)
    return out


def _json_install_paths(j):
    """Every "install_path" / "installPath" value anywhere in a launcher's JSON."""
    out = []
    if isinstance(j, dict):
        for k, v in j.items():
            if k in ('install_path', 'installPath') and isinstance(v, str):
                out.append(v)
            else:
                out += _json_install_paths(v)
    elif isinstance(j, list):
        for v in j:
            out += _json_install_paths(v)
    return out


def _has_witcher3_exe(d):
    return any(os.path.isfile(os.path.join(d, 'bin', x, 'witcher3.exe')) for x in ('x64_dx12', 'x64'))


def wine_launcher_dirs(root='Z:\\'):
    """The Witcher 3 folders from GOG and Epic on Linux, seen through Wine's Z: drive: Heroic's install lists (GOG and
    Epic, native and Flatpak), the folders Heroic and Lutris install to by default (~/Games), and GOG / Epic installs
    inside Wine prefixes (Lutris, Bottles, ~/.wine). Only folders with the game's own exe count. Only reads files."""
    homes = [h for h in glob.glob(os.path.join(root, 'home', '*')) if os.path.isdir(h)] + [os.path.join(root, 'root')]
    cands = []
    for h in sorted(homes):
        for cfg in (os.path.join(h, '.config', 'heroic'),
                    os.path.join(h, '.var', 'app', 'com.heroicgameslauncher.hgl', 'config', 'heroic')):
            for js in (('gog_store', 'installed.json'), ('legendaryConfig', 'legendary', 'installed.json'),
                       ('..', 'legendary', 'installed.json')):          # standalone / older Legendary
                try:
                    with open(os.path.normpath(os.path.join(cfg, *js)), encoding='utf-8', errors='replace') as f:
                        cands += [_unix_to_wine(p, root) for p in _json_install_paths(json.load(f)) if p.startswith('/')]
                except (OSError, ValueError, RecursionError):
                    pass
        # Lutris: one .yml per game; game: exe (absolute, or inside prefix) -> the folder 3 levels above bin\x64*\
        for ld in (os.path.join(h, '.local', 'share', 'lutris', 'games'), os.path.join(h, '.config', 'lutris', 'games'),
                   os.path.join(h, '.var', 'app', 'net.lutris.Lutris', 'data', 'lutris', 'games')):
            for y in glob.glob(os.path.join(glob.escape(ld), '*.yml')):
                try:
                    with open(y, encoding='utf-8', errors='replace') as f:
                        txt = f.read()
                except OSError:
                    continue
                val = lambda key: [m.strip().strip('\'"') for m in re.findall(r'^\s*%s:\s*(.+?)\s*$' % key, txt, re.M)]
                pre = (val('prefix') or [''])[0]
                for exe in val('exe'):
                    full = exe if exe.startswith('/') else (pre.rstrip('/') + '/' + exe if pre.startswith('/') else '')
                    parts = [x for x in full.split('/') if x]
                    if len(parts) >= 4 and parts[-1].lower() == 'witcher3.exe' and parts[-3].lower() == 'bin':
                        cands.append(_unix_to_wine('/' + '/'.join(parts[:-3]), root))
        e = glob.escape(h)
        prefixes = [os.path.join(e, 'Games', '*'), os.path.join(e, '.wine'),
                    os.path.join(e, '.local', 'share', 'bottles', 'bottles', '*'),
                    os.path.join(e, '.var', 'app', 'com.usebottles.bottles', 'data', 'bottles', 'bottles', '*')]
        pats = [os.path.join(e, 'Games', '*'), os.path.join(e, 'Games', 'Heroic', '*')]
        for pf in prefixes:
            dc = os.path.join(pf, 'drive_c')
            pats += [os.path.join(dc, 'GOG Games', '*'),
                     os.path.join(dc, 'Program Files*', 'GOG Galaxy', 'Games', '*'),
                     os.path.join(dc, 'Program Files*', 'Epic Games', '*')]
        for p in pats:
            cands += sorted(glob.glob(p))
    out, seen = [], set()
    for d in cands:
        k = os.path.normcase(os.path.normpath(d))
        if k not in seen and _has_witcher3_exe(d):
            seen.add(k)
            out.append(d)
    return out


def find_game_dir():
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    d = here
    for _ in range(5):                                   # the patcher placed somewhere inside the game folder
        if is_game_dir(d):
            return d
        d = os.path.dirname(d)
    cands = []
    try:
        import winreg
        for hive, key, val in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
                               (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    steam = winreg.QueryValueEx(k, val)[0]
                libs = [steam]
                vdf = os.path.join(steam, 'steamapps', 'libraryfolders.vdf')
                if os.path.isfile(vdf):
                    libs += [m.replace('\\\\', '\\') for m in re.findall(r'"path"\s+"([^"]+)"', open(vdf, encoding='utf-8', errors='replace').read())]
                cands += [os.path.join(l, 'steamapps', 'common', 'The Witcher 3') for l in libs]
            except OSError:
                pass
        for key in (r'SOFTWARE\WOW6432Node\GOG.com\Games\1495134320', r'SOFTWARE\WOW6432Node\GOG.com\Games\1207664663'):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                    cands.append(winreg.QueryValueEx(k, 'path')[0])
            except OSError:
                pass
    except ImportError:
        pass
    cands += epic_install_dirs()                         # Epic Games Store
    if running_on_wine():                                # Linux / Steam Deck: Steam's own folders, through Z:
        try:
            cands += wine_steam_dirs()
        except Exception:
            log_exc()
        try:
            cands += wine_launcher_dirs()                # GOG / Epic: Heroic, Lutris, Bottles
        except Exception:
            log_exc()
    for c in cands:
        if is_game_dir(c):
            return os.path.normpath(c)


def game_running():
    try:
        # bytes, not text: tasklist writes in the console code page (German "ausgef\x81hrt" can't be decoded as cp1252)
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq witcher3.exe', '/NH'], capture_output=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout or b''
        if b'witcher3.exe' in out.lower():
            return True
    except Exception:
        log_exc()
    # Proton runs the game in its own Wine instance, which tasklist here can't see: look at Linux's own process list
    return running_on_wine() and linux_process_running('witcher3.exe')


def linux_process_running(name, root='Z:\\'):
    """True if a Linux process's command line names the exe (read through Wine's Z: drive). Only reads files."""
    want = name.lower().encode()
    try:
        pids = [p for p in os.listdir(os.path.join(root, 'proc')) if p.isdigit()]
    except OSError:
        return False
    for p in pids:
        try:
            with open(os.path.join(root, 'proc', p, 'cmdline'), 'rb') as f:
                if want in f.read().lower():
                    return True
        except OSError:
            pass
    return False


def mods_dir(game):
    return os.path.join(game, 'Mods')


def mse_content(game):
    return os.path.join(mods_dir(game), MSE_DIR, 'content')


def mse_installed(game):
    return os.path.isfile(os.path.join(mods_dir(game), MSE_DIR, MSE_SCRIPT))


def entry_data(bundle_path):
    """panel_ingamemenu.redswf from a bundle, or None"""
    try:
        b = w3bundle.read_bundle(bundle_path, load_payload=False)
    except Exception:
        return None
    for e in b.entries:
        if e.name.lower() == DEPOT.lower():
            with open(bundle_path, 'rb') as f:
                f.seek(e.offset)
                e.payload = f.read(e.zsize)
            return e.data()
    return None


def swf_of(redswf):
    w = cr2w.CR2W(redswf)
    pe, lo, bo, bl, tail = w.swf_layout()
    return M.inflate_swf(w.chunk_data(0)[bo:bo + bl])


def is_rtg(redswf):
    try:
        swf = swf_of(redswf)
        return any(k in swf for k in RTG_MARKS)
    except Exception:
        return False


def has_t_toggle(bundle_path):
    """Real-Time Graphics with its T transparency toggle (version 6 "Original" has none)"""
    d = entry_data(bundle_path)
    try:
        return d is not None and RTG_MARKS[0] in swf_of(d)
    except Exception:
        return False


def other_menu_mods(game):
    """[(folder, bundle path, is Real-Time Graphics)] for every other mod that ships panel_ingamemenu.redswf"""
    out = []
    md = mods_dir(game)
    if not os.path.isdir(md):
        return out
    for mod in sorted(os.listdir(md), key=str.lower):
        if mod.lower() == MSE_DIR.lower():
            continue
        for bp in sorted(glob.glob(os.path.join(md, mod, 'content', '*.bundle'))):
            d = entry_data(bp)
            if d is not None:
                out.append((mod, bp, is_rtg(d)))
                break
    return out


def current_state(game):
    """'combined' / 'standard' / 'missing' for MSE's own menu file"""
    bp = os.path.join(mse_content(game), 'blob0.bundle')
    d = entry_data(bp) if os.path.isfile(bp) else None
    if d is None:
        return 'missing'
    return 'combined' if is_rtg(d) else 'standard'


def _errors(swf):
    abc = abcrt.ABC(abcrt.swf_abcs(swf)[0][1])
    own = abc.owners()
    errs = set()
    for b in abc.bodies:
        for e in avm2verify.verify_body(abc, b)['errors']:
            errs.add((str(own.get(b['method'], b['method'])), re.sub(r'\[\d+,\d+\)', '', e)))
    return errs, avm2verify.verify_abc_refs(abc)


def build(source):
    """patched redswf; the code check may only report problems the source file already had"""
    try:
        data, swf = fml_patch.patch_redswf(source)
    except fml_patch.PatchError as ex:
        raise PatchFailed('This version of the menu file is not supported (%s).' % ex)
    new, refs = _errors(swf)
    old, _ = _errors(swf_of(source))
    if refs or new - old:
        bad = sorted(new - old)[:3]
        raise PatchFailed('The code check failed: %s' % (bad or refs[:3]))
    return data


def write_mse(game, data):
    content = mse_content(game)
    bp = os.path.join(content, 'blob0.bundle')
    mp = os.path.join(content, 'metadata.store')
    fd, tb = tempfile.mkstemp(suffix='.msetmp', dir=content)
    os.close(fd)
    tm = tb + '.store'
    try:
        with open(tb, 'wb') as f:
            f.write(w3bundle.build_bundle_bytes([w3bundle.make_entry(DEPOT, data, w3bundle.COMP_ZLIB)],
                                                alignment=16, pad_end=False, pad_file_to=0, gap_fill=None))
        if entry_data(tb) != data:
            raise PatchFailed('Read-back check failed.')
        # metadata.store names the bundle by file name: generated for the final name
        with open(tm, 'wb') as f:
            f.write(w3meta.write_store(w3meta.generate([('blob0.bundle', tb)])))
        os.replace(tb, bp)
        os.replace(tm, mp)
    finally:
        for p in (tb, tm):
            if os.path.exists(p):
                os.remove(p)
    if entry_data(bp) != data:
        raise PatchFailed('Read-back check failed after writing.')


def combine(game, rtg_bundle):
    src = entry_data(rtg_bundle)
    if src is None or not is_rtg(src):
        raise PatchFailed('%s\'s menu file was not found.' % RTG_NAME)
    write_mse(game, build(src))


def restore(game):
    src = entry_data(os.path.join(game, 'content', 'content0', 'bundles', 'r4gui.bundle'))
    if src is None:
        raise PatchFailed('The game\'s own menu file was not found (content\content0\bundles\r4gui.bundle).')
    write_mse(game, build(src))
