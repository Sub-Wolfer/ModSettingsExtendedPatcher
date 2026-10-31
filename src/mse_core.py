"""Mod Settings Extended Patcher - core: merges MSE's menu changes onto Real-Time Graphics and HDR Menus Preview's
panel_ingamemenu.redswf, read from the player's own install, or rebuilds MSE's standard file from the game's."""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abcrt        # noqa: E402
import avm2verify   # noqa: E402
import cr2w         # noqa: E402
import fml_patch    # noqa: E402
import uw_map_patch as M  # noqa: E402
import w3bundle     # noqa: E402
import w3meta       # noqa: E402

VERSION = '1.0.1'
DEPOT = fml_patch.DEPOT
MSE_DIR = 'mod00000_ModSettingsExtended'
MSE_SCRIPT = os.path.join('content', 'scripts', 'local', 'FullModsList.ws')
# names only Real-Time Graphics' menu file has: its T hint (versions with the hotkey) / its text style store (all,
# version 6 "Original" too: no hotkey, folder modLiveGraphicsPreviewOriginal)
RTG_MARKS = (b'TOGGLE TRANSPARENCY', b'_previewOriginalTextStyles')
RTG_NAME = 'Real-Time Graphics and HDR Menus Preview'


class PatchFailed(Exception):
    pass


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
    for c in cands:
        if is_game_dir(c):
            return os.path.normpath(c)


def game_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq witcher3.exe', '/NH'], capture_output=True, text=True,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout
        return 'witcher3.exe' in out.lower()
    except OSError:
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
