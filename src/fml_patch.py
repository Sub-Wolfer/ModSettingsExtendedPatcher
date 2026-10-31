"""Full Mods List - panel_ingamemenu.redswf patch: every menu list longer than 10 entries is shown in full, in columns.

The game menu (pause menu and main menu both use gameplay\\gui_new\\swf\\mainmenu\\panel_ingamemenu.redswf) draws its
left list with SimpleListModule (menuListModule at stage 333, 370): a W3ScrollingList over 10 renderers placed on the
timeline (mcListItem1..10, MenuListItemCommon, 42 units apart, x 0, frame about -170..170). Longer lists (Options >
Mods with many mods) scroll inside those 10 rows, and IngameMenu.activateMenuListItem picks the renderer by
index - renderers[0].index, which is what Mod Settings Menu Fix works around by splitting the list into submenus.

Changes (all inside catch-all guarded methods; lists of 10 or fewer entries keep the vanilla layout):
  * SimpleListModule.fmlPrep(dp) - from setListData, right before mcList.dataProvider is set: blank labels get the
    entry id; when the list has more entries than renderers, new MenuListItemCommon renderers mcListItem11..N are
    created (cap 99), added to the module, given the mouse handlers, and the list rescans its renderers
    (itemRendererInstanceName = "mcListItem"). It also listens to W3ScrollingList.REPOSITION on the stage, because
    ScrollingList.drawLayout puts every renderer back at x 0 / y i*40.
  * SimpleListModule.fmlLayout() - from the start of repositionRenderers. More than 10 entries: columns COLW units
    apart, each filled with as many rows as fit above the bottom margin of the screen (getScreenRect) before the
    next one starts, never more columns than fit before the right margin (then the columns share the rows and
    scroll). While an option page is open (lockSelection, the page is drawn at
    x 707 right of the list) only the column with the open entry is shown, at the first column's place.
  * SimpleListModule.fmlNav(e) - from IngameMenu.handleInputNavigate, right before the list gets the input: in column
    mode left/right jump one column (same row; clamped to the last entry, no wrap).
  * the lockSelection setter re-lays the list out; the hideSelection setter also reaches renderers 11..N.
  * Options > Mods sorted A to Z: a gold letter header row before each group (fmlHdrs in fmlView, drawn by
    fmlHdrDraw from updateText), never selectable (fmlHdrSkip from W3ScrollingList.selectedIndex set, Up / Down in
    fmlNav); RT / Space turns them on or off, stored with the sort (code + 3 = off).
  * Options > Mods sorted By category: grouped by the category the script sets on each row (fmlKind), A to Z
    inside a group, with a gold category header row before each group (on / off as in A to Z; stored code 6 = on,
    7 = off); X / Insert moves the selected mod to the next category (fmlCatNext), told to the script ("cat").
    Y / Home twice within RESET_MS (fmlCatReset; the first press arms it and relabels the prompt) puts every mod of
    the list shown (from the top level also those in Menu Organizer categories, fmlRstRow) back in the category the
    script guessed for it (fmlGuess), told to the script ("catreset" with those ids).
Added to SimpleListModule: fmlPer:int, fmlCnt:int, fmlHooked:Boolean; methods fmlPrep, fmlLayout, fmlNav, fmlRepos,
fmlHide.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
import abcrt            # noqa: E402
import cr2w             # noqa: E402
import uw_map_patch as M  # noqa: E402

M.BRANCHES = M.BRANCHES + tuple(b for b in ('ifeq', 'ifne', 'ifstricteq', 'ifstrictne', 'iflt', 'ifle', 'ifgt',
                                             'ifge', 'ifnlt', 'ifnle', 'ifngt', 'ifnge') if b not in M.BRANCHES)
PatchError = M.PatchError

DEPOT = 'gameplay\\gui_new\\swf\\mainmenu\\panel_ingamemenu.redswf'
COLW = 370          # column spacing (renderer frame is about 340 wide)
EDGE_R = 190        # last column's centre stays this far from the right screen edge
EDGE_B = 100        # rows stay above this distance from the bottom screen edge (about the space above row 1)
STRIP_W = 369       # width of the dark strip behind the list (shape -184.5..184.5)
VANILLA_ROWS = 10
MAX_ROWS = 600      # renderers created at most (rows past this would scroll the vanilla way)
STRIP_EXTRA = 70    # column mode: the strip reaches this much further right (room for the scroll bar)
BAR_X = 160         # scroll bar: this far right of the last shown column's centre, inside the dark strip (edge ~178)
WHEEL_ROWS = 3      # rows per mouse-wheel notch
STICK_SPEED = 15    # right stick: rows per second at full tilt (speed grows with tilt squared)
STICK_DEAD = 0.15   # right stick: tilt below this does nothing
TOP_SHIFT = 250     # column mode: the list moves up this far into the space of the hidden game logo
SORT_ACTION = 7771  # input feedback id of the "Sort" prompt
HDR_ACTION = SORT_ACTION + 1   # input feedback id of the "Headers" prompt (A to Z only)
HDR_NAME = 'Headers'           # its label when the script sent no translation (fmlNames[NUM_SORTS + 1])
GAP_TRIES = 64      # fmlGaps: rows per column tried / end padding rows at most this often
HDR_TYPE = 36       # IngameMenu.IGMActionType_SubtleSeparator: vanilla moveDown skips it, the selectedIndex setter refuses it
HDR_GROW = 4        # header letter: this many pixels larger than the mod names
HDR_GOLD = 0xDEB25C  # header letter and line color
HDR_LINE_A = 0.6    # header line: the gold at this alpha, 1 px high
FRAME_PAD = 24      # Mods list: the selection frame reaches this far past each end of the name
FRAME_TRIM = 10     # Mods list: the selection frame this much shorter than vanilla (clear of a header row above)
PAD_RT, KEY_SPACE = 151, 32   # KeyCode.PAD_RIGHT_TRIGGER / KeyCode.SPACE: headers on/off
TOP_FADE = 3        # column mode: a row scrolled partly out at the top fades this many times faster than it
                    # leaves (gone before it reaches the title's second line)
SEARCH_SHOWN = 10   # characters of the search shown in the title (the last ones, after "...")
SORT_NAMES = 'A to Z|Newest first|Recently opened|By category'   # sorts 0..3; the script sends them in the game's language
NUM_SORTS = 4
OLD_SORTS = 3       # stored codes 0..5 = sorts 0..2, + OLD_SORTS while the headers are off (unchanged meaning)
CAT_SORT = 3        # fmlSort of By category
CAT_CODE = 6        # its stored code: 6 headers on, 7 headers off
CAT_ACTION = SORT_ACTION + 2   # input feedback id of the "Change category" prompt (By category only)
RST_ACTION = CAT_ACTION + 1    # input feedback id of the "Reset categories" prompt (By category only, after it)
CAT_NAMES = 'Animation|Camera|Controls|Immersion|Menu|Utilities|UI|Visuals|Misc'   # fmlKind 0..8 when the script
NUM_CATS = 9                                                                      # sent no translation
PAD_X, KEY_INSERT = 138, 45   # KeyCode.PAD_X_SQUARE / KeyCode.INSERT: the selected mod -> the next category
# KeyCode.PAD_Y_TRIANGLE / KeyCode.HOME: reset the categories. Free while the Mods list has the focus on PC: Y only
# reaches IngameMenu.handleInputNavigate's "Xbox One main menu: choose profile" case (and modal dialogs, the save slot
# pages, W3SubMenuListItemRenderer); Home is read only by sliders, steppers, popups, TextArea and the CLIK
# ScrollingList, whose handleInput W3ScrollingList replaces without calling it. (LB / RB: the main menu's account
# button, LT: the tooltip zoom, so not those.)
PAD_Y, KEY_HOME = 139, 36
RST_IDX = NUM_SORTS + 3 + NUM_CATS   # fmlNames index of the "Reset categories" label (newer scripts only)
RST_NAME = 'Reset categories'        # its label when the script sent no translation
RST_ARMED = 'Press again to reset'   # armed, English (a translated label without its armed one gets "?" instead)
RST_AIDX = RST_IDX + 1               # fmlNames index of the armed label (newer scripts only)
# favorites (Mods list, every sort): LB / Page Up favorite on/off
PAD_LB, KEY_PGUP = 148, 33   # KeyCode.PAD_LEFT_SHOULDER / KeyCode.PAGE_UP
FAV_ACTION = RST_ACTION + 1  # input feedback id of the "Favorite" prompt
FAV_IDX = RST_AIDX + 1       # fmlNames indexes of "Favorite" and the "Favorites" header
FAVS_IDX = FAV_IDX + 1       # (newer scripts only; English otherwise)
RESET_MS = 3000     # a second Y / Home within this many ms after the first resets the categories
RTG_HINT_Y = 20     # Real-Time Graphics merge: its "[ T ] TOGGLE TRANSPARENCY" hint moves from the bottom right (y 1005) to the top right
MENU_FPS = 240      # SWF frame rate: the menu redraws every game frame up to this (follows the monitor with VSync)
TIMELINE_FPS = 30   # the game's own frame rate for this menu: timeline animations keep this speed (fmlGov)


def op_name(ins):
    return abcrt.OPS[ins[1]][0]


def insert_at(ins, k, new, tag):
    """insert new instructions before ins[k]; jumps that targeted ins[k] now land on the new code"""
    old = ins[k][0]
    body = M.assemble(new, tag)
    body[0][0] = old
    ins[k] = [tag + 'orig', ins[k][1], ins[k][2]]
    return ins[:k] + body + ins[k:]


def patch_abc(abc):
    c = M.Ctx(abc)
    ci = c.cls('SimpleListModule')
    tr = abc.instances[ci]['traits']
    if any(abc.mn(t.name).startswith('fml') for t in tr):
        raise PatchError('this menu file is already patched by Full Mods List')
    pub = lambda n, ops=('getproperty', 'setproperty', 'initproperty'): c.used_mn(n, ops, 'pkg:::' + n)
    like = c.trait_mn(tr, 'setListData', (1,))
    nm = lambda s: c.new_name(like, s)
    mcList = c.trait_mn(tr, 'mcList', (0,))
    locked = c.trait_mn(tr, '_lockedSelectionIndex', (0,))
    X, Y = pub('x'), pub('y')
    vis, nameP = pub('visible'), pub('name')
    tf, th = pub('textField'), pub('textHeight')
    lab, idP = pub('label'), pub('id')
    length = pub('length')
    dprov = pub('dataProvider')
    numR = c.used_mn('numRenderers', ('getproperty',))
    gra = c.used_mn('getRendererAt', ('callproperty',))
    selIdx = pub('selectedIndex')
    hideSel = pub('hideSelection')
    regMouse = c.used_mn('registerMouseEventsForItem', ('callpropvoid',))
    irin = c.used_mn('itemRendererInstanceName', ('setproperty',))
    addChild = c.used_mn('addChild', ('callpropvoid',))
    gdbn = c.used_mn('getDefinitionByName', ('callproperty',))
    cu, gsr = c.used_mn('CommonUtils', ('getlex',)), c.used_mn('getScreenRect', ('callproperty',))
    pointC = c.used_mn('Point', ('constructprop', 'findpropstrict'))
    g2l = c.used_mn('globalToLocal', ('callproperty',))
    Wd, Hd = pub('width'), pub('height')
    stageP = c.used_mn('stage', ('getlex', 'getproperty'))
    ael = c.used_mn('addEventListener', ('callpropvoid',))
    w3sl = c.used_mn('W3ScrollingList', ('getlex',))
    repos = c.used_mn('REPOSITION', ('getproperty',))
    details, navEq = pub('details'), pub('navEquivalent')
    valueP, handled = pub('value'), pub('handled')
    t_int, t_bool = c.type_mn('int'), c.type_mn('Boolean')

    def string(s):
        b = s.encode()
        if b in abc.strings[1:]:
            return abc.strings.index(b, 1)
        abc.strings.append(b)
        return len(abc.strings) - 1
    s_item, s_cls = string('mcListItem'), string('MenuListItemCommon')
    s_left, s_right, s_up = string('left'), string('right'), string('keyUp')

    fmlPer, fmlCnt, fmlHooked = nm('fmlPer'), nm('fmlCnt'), nm('fmlHooked')
    M.add_slot(c, ci, fmlPer, t_int, 0, 0)
    M.add_slot(c, ci, fmlCnt, t_int, 0, 0)
    M.add_slot(c, ci, fmlHooked, t_bool, 0, 0)
    m_prep, m_layout, m_nav = nm('fmlPrep'), nm('fmlLayout'), nm('fmlNav')
    m_repos, m_hide = nm('fmlRepos'), nm('fmlHide')
    m_strip, fmlBg, fmlBgX = nm('fmlStrip'), nm('fmlBg'), nm('fmlBgX')
    M.add_slot(c, ci, fmlBg, 0, 0, 0)
    M.add_slot(c, ci, fmlBgX, c.type_mn('Number'), 0, 0)
    numCh, gca = c.used_mn('numChildren', ('getproperty',)), c.used_mn('getChildAt', ('callproperty',))
    scX = pub('scaleX')
    s9 = c.new_name(X, 'scale9Grid')
    rectC = c.used_mn('Rectangle', ('constructprop',))
    def pubn(n, ops=('getproperty', 'setproperty', 'callproperty', 'callpropvoid')):
        try:
            return c.used_mn(n, ops, 'pkg:::' + n)
        except PatchError:
            return c.new_name(X, n)
    t_num = c.type_mn('Number')
    # long lists (columns) and the Mods list: names on one line, at the left edge of the column (right in Arabic),
    # shrunk to fit instead of wrapping onto the row below; other lists get the vanilla centred, wrapping text back
    numLinesP = pubn('numLines')
    m_fmt, m_shrink, m_apply = nm('fmlFmt'), nm('fmlShrink'), nm('fmlApplyTo')
    m_fit = nm('fmlFitFrame')
    fmlAlignNow = nm('fmlAlignNow')
    M.add_slot(c, ci, fmlAlignNow, 0, 0, 0)
    getTF, setTF = pubn('getTextFormat'), pubn('setTextFormat')
    s_apply = string('fmlApplyTo')
    wwP, dtfP, alignP, tasM = pubn('wordWrap'), pubn('defaultTextFormat'), pubn('align'), pubn('setTextAutoSize')
    s_center, s_shrink, s_none = string('center'), string('shrink'), string('none')
    s_tfx = string('scaleform.gfx.TextFieldEx')
    try:
        arabic = (c.used_mn('CoreComponent', ('getlex',)), c.used_mn('isArabicAligmentMode', ('getproperty',)))
    except PatchError:
        arabic = None
    fmlScroll,fmlVis, fmlRowH, fmlShown = nm('fmlScroll'), nm('fmlVis'), nm('fmlRowH'), nm('fmlShown')
    fmlFollow, fmlBarS, fmlDrag, fmlStickT = nm('fmlFollow'), nm('fmlBarS'), nm('fmlDrag'), nm('fmlStickT')
    for f, t in ((fmlScroll, t_num), (fmlVis, t_int), (fmlRowH, t_num), (fmlShown, t_int), (fmlFollow, t_bool),
                 (fmlBarS, 0), (fmlDrag, t_bool), (fmlStickT, t_num)):
        M.add_slot(c, ci, f, t, 0, 0)
    fmlY0, fmlY0Set, m_top = nm('fmlY0'), nm('fmlY0Set'), nm('fmlTop')
    fmlStickY, m_frame = nm('fmlStickY'), nm('fmlFrame')
    fmlMods = nm('fmlMods')
    fmlTopOn, fmlAll = nm('fmlTopOn'), nm('fmlAll')
    M.add_slot(c, ci, fmlTopOn, t_bool, 0, 0)
    m_ui, m_key = nm('fmlUi'), nm('fmlKey')
    m_hits = nm('fmlHits')
    M.add_slot(c, ci, fmlMods, t_bool, 0, 0)
    # letter header rows (Options > Mods, A to Z): fmlHdrOff = the player turned them off (stored with the sort)
    fmlSort, fmlHdrOff = nm('fmlSort'), nm('fmlHdrOff')
    M.add_slot(c, ci, fmlHdrOff, t_bool, 0, 0)
    # no header in a column's last row (fmlGaps puts a blank spacer row there instead): fmlMaxR / fmlScrC = the Mods
    # list's rows that fit in a column / columns that fit on screen (fmlLayout), fmlGapR / fmlGapC = the values
    # fmlGaps placed the spacers for, fmlRegap = they differ (first open, resolution change): fmlUi shows the list again
    fmlMaxR, fmlScrC, fmlGapR, fmlGapC = nm('fmlMaxR'), nm('fmlScrC'), nm('fmlGapR'), nm('fmlGapC')
    fmlRegap = nm('fmlRegap')
    for f in (fmlMaxR, fmlScrC, fmlGapR, fmlGapC):
        M.add_slot(c, ci, f, t_int, 0, 0)
    M.add_slot(c, ci, fmlRegap, t_bool, 0, 0)
    m_gaps, m_regap = nm('fmlGaps'), nm('fmlRegapNow')
    m_ishdr, m_hskip, m_hdrs = nm('fmlIsHdr'), nm('fmlHdrSkip'), nm('fmlHdrs')
    m_hdraw, m_htog = nm('fmlHdrDraw'), nm('fmlHdrToggle')
    fmlHdrP = pubn('fmlHdr')
    s_fmlhdr = string('fmlHdr')
    pcP = pubn('previousContainers')
    s_pc, s_mods, s_Mods = string('previousContainers'), string('mods'), string('Mods')
    s_pe, peP = string('previousEntries'), pubn('previousEntries')
    M.add_slot(c, ci, fmlStickY, t_num, 0, 0)
    s_frame = string('enterFrame')
    m_gov, fmlGovOn, fmlGovT, fmlGovA = nm('fmlGov'), nm('fmlGovOn'), nm('fmlGovT'), nm('fmlGovA')
    M.add_slot(c, ci, fmlGovOn, t_bool, 0, 0)
    M.add_slot(c, ci, fmlY0, t_num, 0, 0)
    M.add_slot(c, ci, fmlY0Set, t_bool, 0, 0)
    logo = c.trait_mn(tr, 'mcGameLogo', (0,))
    alphaP, parentP, verP = pubn('alpha'), pubn('parent'), pubn('txtVersion')
    s_ver = string('txtVersion')
    m_bar, m_bdown, m_bmove, m_bup = nm('fmlBar'), nm('fmlBarDown'), nm('fmlBarMove'), nm('fmlBarUp')
    m_wheel, m_follow = nm('fmlWheel'), nm('fmlFollowSel')
    spriteC = c.used_mn('Sprite', ('constructprop',))
    gfx = pubn('graphics')
    g_clear, g_bf, g_dr, g_ef = pubn('clear'), pubn('beginFill'), pubn('drawRect'), pubn('endFill')
    mouseY, delta = pubn('mouseY'), pubn('delta')
    codeP, yval = pubn('code'), pubn('yvalue')
    getTimer = c.used_mn('getTimer', ('callproperty',))
    s_mdown, s_mmove, s_mup, s_wheel = string('mouseDown'), string('mouseMove'), string('mouseUp'), string('mouseWheel')
    i_white = c.integer(0xFFFFFF)
    d_hit, d_track, d_thumb = c.double(0.01), c.double(0.2), c.double(0.75)
    d_dead2, d_speed = c.double(STICK_DEAD * STICK_DEAD), c.double(STICK_SPEED / 1000.0)
    repR = c.trait_mn(tr, 'repositionRenderers', (1,))
    lbody = c.body('SimpleListModule::setListData')
    void = abc.methods[abc.instances[ci]['traits'][[abc.mn(t.name) for t in tr].index('repositionRenderers')].method]['ret']

    L = lambda *a: (None,) + a
    lst = [L('getlocal0'), L('getproperty', mcList)]
    # sorts with header rows (A to Z, By category): on to ok, else to miss; stack unchanged. first = the caller's
    # label on the first instruction
    hdr_gate = lambda miss, ok, first=None: [
        (first, 'getlocal0') if first else L('getlocal0'), L('getproperty', fmlSort), L('convert_i'),
        L('pushbyte', 0), L('ifeq', ok),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT), L('ifne', miss),
        (ok, 'nop')]

    # fmlPrep(dp): 1 dp, 2 cnt, 3 cls, 4 i / shown container's index, 5 r, 6 n, 7 item, 8 containers,
    #              9 menu / its previousEntries / shown container / its id
    prep = [
        L('getlocal0'), L('getproperty', fmlGovOn), L('iftrue', 'G0'),
        L('getlocal0'), L('getproperty', stageP), L('iffalse', 'G0'),
        L('getlocal0'), L('pushstring', s_frame), L('getlocal0'), L('getproperty', m_gov),
        L('pushfalse'), L('pushbyte', 0), L('pushtrue'), L('callpropvoid', ael, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlGovOn),
        ('G0', 'label'),
        # the list being shown is Options > Mods, or one of Menu Organizer's categories in it (the script marks those
        # with fmlCat): the menu pushed its container before calling setListData
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlMods),
        L('getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal', 9),
        L('getlocal', 9), L('iffalse', 'MZ'),
        L('pushstring', s_pc), L('getlocal', 9), L('in'), L('iffalse', 'MZ'),
        L('getlocal', 9), L('getproperty', pcP), L('coerce_a'), L('setlocal', 8),
        L('getlocal', 8), L('iffalse', 'MZ'),
        L('getlocal', 8), L('getproperty', length), L('convert_i'), L('decrement_i'), L('setlocal', 4),
        # going Back the menu pops previousEntries, calls setListData and only then pops previousContainers: then
        # previousEntries is the shorter one and the list shown belongs to the container before the last
        L('pushstring', s_pe), L('getlocal', 9), L('in'), L('iffalse', 'MC'),
        L('getlocal', 9), L('getproperty', peP), L('coerce_a'), L('setlocal', 9),
        L('getlocal', 9), L('iffalse', 'MC'),
        L('getlocal', 9), L('getproperty', length), L('getlocal', 4), L('ifgt', 'MC'),
        L('declocal_i', 4),
        ('MC', 'getlocal', 4), L('pushbyte', 0), L('iflt', 'MZ'),
        L('getlocal', 8), L('getlocal', 4), L('getproperty', abc_late(c)), L('coerce_a'), L('setlocal', 9),
        L('getlocal', 9), L('iffalse', 'MZ'),
        L('getlocal', 9), L('getproperty', c.new_name(X, 'fmlCat')), L('iftrue', 'MY'),
        L('getlocal', 9), L('getproperty', idP), L('coerce_a'), L('setlocal', 9),
        L('getlocal', 9), L('pushstring', s_mods), L('ifeq', 'MY'),
        L('getlocal', 9), L('pushstring', s_Mods), L('ifne', 'MZ'),
        ('MY', 'getlocal0'), L('pushtrue'), L('initproperty', fmlMods),
        ('MZ', 'label'),
        # new list: back to the top, then show the selected row
        L('getlocal0'), L('pushbyte', 0), L('initproperty', fmlScroll),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlFollow),
        L('getlocal0'), L('pushbyte', 0), L('initproperty', fmlStickY),
        # blank labels -> id; 9 counts the entries that are not letter rows
        L('pushbyte', 0), L('setlocal', 4),
        L('pushbyte', 0), L('setlocal', 9),
        ('PL', 'label'),
        L('getlocal', 4), L('getlocal1'), L('getproperty', length), L('ifnlt', 'PD'),
        L('getlocal1'), L('getlocal', 4), L('getproperty', abc_late(c)), L('coerce_a'), L('setlocal', 7),
        L('getlocal', 7), L('iffalse', 'PN'),
        L('pushstring', s_fmlhdr), L('getlocal', 7), L('in'), L('iftrue', 'PC'),
        L('inclocal_i', 9),
        ('PC', 'nop'),
        L('getlocal', 7), L('getproperty', lab), L('iftrue', 'PN'),
        L('getlocal', 7), L('getproperty', idP), L('iffalse', 'PN'),
        L('getlocal', 7), L('getlocal', 7), L('getproperty', idP), L('setproperty', lab),
        ('PN', 'inclocal_i', 4),
        L('jump', 'PL'),
        # more renderers
        ('PD', 'getlocal1'), L('getproperty', length), L('convert_i'), L('setlocal', 6),
        # Mods list: room for the letter rows of A to Z too (fmlView, after this, adds up to one per entry, a spacer
        # row per column and a few at the end (fmlGaps; gapsim: at most 2.2 * entries + 2), plus Back when the list comes from fmlRefresh: fmlAll has no Back), whatever the
        # sort, so switching to A to Z or turning the headers on never adds renderers later: 3 * entries + 2,
        # counting only entries that are not letter or spacer rows (on Back the list already has them; a renderer
        # added then showed its "TextField" placeholder)
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'PH'),
        L('getlocal', 9), L('pushbyte', 3), L('multiply'), L('pushbyte', 2), L('add'), L('convert_i'),
        L('setlocal', 6),
        ('PH', 'getlocal0'), L('getproperty', mcList), L('getproperty', numR), L('convert_i'), L('setlocal2'),
        L('getlocal2'), L('pushbyte', 1), L('iflt', 'END'),
        L('getlocal', 6), L('getlocal2'), L('ifngt', 'FEW'),
        L('getlocal', 6), L('pushshort', MAX_ROWS), L('ifngt', 'CAP'),
        L('pushshort', MAX_ROWS), L('setlocal', 6),
        ('CAP', 'findpropstrict', gdbn), L('pushstring', s_cls), L('callproperty', gdbn, 1), L('coerce_a'),
        L('setlocal3'),
        L('getlocal2'), L('increment_i'), L('setlocal', 4),
        ('CL', 'label'),
        L('getlocal', 4), L('getlocal', 6), L('ifgt', 'SCAN'),
        L('getlocal3'), L('construct', 0), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('pushstring', s_item), L('getlocal', 4), L('add'), L('setproperty', nameP),
        L('getlocal0'), L('getlocal', 5), L('callpropvoid', addChild, 1),
        L('getlocal0'), L('getlocal', 5), L('callpropvoid', regMouse, 1),
        L('getlocal', 5), L('getlocal0'), L('getproperty', hideSel), L('setproperty', hideSel),
        L('inclocal_i', 4),
        L('jump', 'CL'),
        # no renderers to add: the Mods list still needs the listeners (sort prompt, title, messages to the script)
        ('FEW', 'getlocal0'), L('getproperty', fmlMods), L('iffalse', 'END'),
        L('jump', 'HOOK'),
        ('SCAN', 'getlocal0'), L('getproperty', mcList), L('pushstring', s_item), L('setproperty', irin),
        ('HOOK', 'getlocal0'), L('getproperty', fmlHooked), L('iftrue', 'END'),
        L('getlocal0'), L('getproperty', stageP), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', stageP),
        L('getlex', w3sl), L('getproperty', repos), L('getlocal0'), L('getproperty', m_repos),
        L('pushfalse'), L('pushbyte', 0), L('pushtrue'), L('callpropvoid', ael, 5),
        L('getlocal0'), L('pushstring', s_wheel), L('getlocal0'), L('getproperty', m_wheel),
        L('pushfalse'), L('pushbyte', 0), L('pushtrue'), L('callpropvoid', ael, 5),
        L('getlocal0'), L('pushstring', s_frame), L('getlocal0'), L('getproperty', m_frame),
        L('pushfalse'), L('pushbyte', 0), L('pushtrue'), L('callpropvoid', ael, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlHooked),
        # every renderer's text field for this list (before the dataProvider set re-renders the labels)
        ('END', 'getlocal0'), L('getlocal1'), L('callpropvoid', m_fmt, 1),
        L('returnvoid'),
    ]

    # fmlFmt(dp): on = fmlMods (the Options > Mods list only; Settings and other lists stay centred) -> fmlAlignNow "left" ("right" in Arabic); off after it was on ->
    # "center" (vanilla look back); never on -> stays null and the rows are left alone. Every row gets it now, and again
    # each time it redraws its text (hook in W3MenuListItemRenderer.updateText): a label set as plain text keeps the
    # field's old paragraph format, so the field's default format alone only reached rows with markup (Back).
    #   2 on, 4 i, 5 n, 6 row
    fmt = [
        L('getlocal0'), L('getproperty', fmlMods), L('convert_b'), L('setlocal2'),
        L('getlocal2'), L('iftrue', 'ON'),
        L('getlocal0'), L('getproperty', fmlAlignNow), L('iffalse', 'END'),
        L('getlocal0'), L('pushstring', s_center), L('initproperty', fmlAlignNow),
        L('jump', 'A9'),
        ('ON', 'getlocal0'), L('pushstring', s_left), L('initproperty', fmlAlignNow),
        *([L('getlex', arabic[0]), L('getproperty', arabic[1]), L('iffalse', 'A9'),
           L('getlocal0'), L('pushstring', s_right), L('initproperty', fmlAlignNow)] if arabic else []),
        ('A9', 'getlocal0'), L('getproperty', mcList), L('getproperty', numR), L('convert_i'), L('setlocal', 5),
        L('pushbyte', 0), L('setlocal', 4),
        ('R0', 'label'),
        L('getlocal', 4), L('getlocal', 5), L('ifnlt', 'END'),
        L('getlocal0'), L('getproperty', mcList), L('getlocal', 4), L('callproperty', gra, 1), L('coerce_a'),
        L('setlocal', 6),
        L('getlocal', 6), L('iffalse', 'RN'),
        L('getlocal0'), L('getlocal', 6), L('callpropvoid', m_apply, 1),
        ('RN', 'inclocal_i', 4), L('jump', 'R0'),
        ('END', 'returnvoid'),
    ]

    # fmlApplyTo(row): the row's text field as fmlAlignNow says: "center" = vanilla (wraps, no shrink), otherwise one
    # line at that edge, shrunk to fit; then the selection frame refits to it (fmlFitFrame, also when nothing was
    # applied).   2 text field, 3 format
    apply_ = [
        L('getlocal0'), L('getproperty', fmlAlignNow), L('iffalse', 'END'),
        L('getlocal1'), L('getproperty', tf), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        L('getlocal2'), L('getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_center), L('equals'),
        L('setproperty', wwP),
        L('getlocal2'), L('callproperty', getTF, 0), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('getlocal0'), L('getproperty', fmlAlignNow), L('setproperty', alignP),
        L('getlocal2'), L('getlocal3'), L('callpropvoid', setTF, 1),
        L('getlocal2'), L('getproperty', dtfP), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('getlocal0'), L('getproperty', fmlAlignNow), L('setproperty', alignP),
        L('getlocal2'), L('getlocal3'), L('setproperty', dtfP),
        L('getlocal0'), L('getlocal2'),
        L('getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_center), L('equals'), L('not'),
        L('callpropvoid', m_shrink, 2),
        ('END', 'getlocal0'), L('getlocal1'), L('callpropvoid', m_fit, 1),
        L('returnvoid'),
    ]

    # fmlShrink(tf, on): Scaleform's TextFieldEx.setTextAutoSize(tf, on ? "shrink" : "none"), in its own guarded
    # method (no TextFieldEx: the line is clipped at the field's edge instead)
    shrink = [
        L('findpropstrict', gdbn), L('pushstring', s_tfx), L('callproperty', gdbn, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('getlocal3'), L('getlocal1'), L('pushstring', s_none),
        L('getlocal2'), L('iffalse', 'S1'),
        L('pop'), L('pushstring', s_shrink),
        ('S1', 'callpropvoid', tasM, 2),
        ('END', 'returnvoid'),
    ]

    # fmlLayout():Boolean  1 n, 2 i, 3 r, 4 rect, 5 pt, 6 rowH, 7 maxRows, 8 maxCols, 9 ncols, 10 per, 11 col,
    #                      12 y, 13 lockCol, 14 lastCol, 15 k, 16 max scroll, 17 sel's row, 18 sel
    layout = [
        *lst, L('getproperty', numR), L('convert_i'), L('setlocal', 15),
        L('pushbyte', 0), L('setlocal1'),
        *lst, L('getproperty', dprov), L('iffalse', 'HAVE'),
        *lst, L('getproperty', dprov), L('getproperty', length), L('convert_i'), L('setlocal1'),
        ('HAVE', 'getlocal1'), L('getlocal', 15), L('ifngt', 'NOK'),
        L('getlocal', 15), L('setlocal1'),
        ('NOK', 'getlocal1'), L('pushbyte', VANILLA_ROWS), L('ifgt', 'COLS'),
        # vanilla length. The page stays moved up while the Mods list itself is long (a search can leave 10 rows or
        # fewer): want = fmlMods && fmlAll.length + 1 (its Back row) > VANILLA_ROWS
        L('getlocal0'), L('getproperty', fmlMods), L('convert_b'),
        L('dup'), L('iffalse', 'W9'), L('pop'),
        L('getlocal0'), L('getproperty', fmlAll), L('convert_b'),
        L('dup'), L('iffalse', 'W9'), L('pop'),
        L('getlocal0'), L('getproperty', fmlAll), L('getproperty', length), L('pushbyte', VANILLA_ROWS),
        L('ifnlt', 'WT'),
        L('pushfalse'), L('jump', 'W9'),
        ('WT', 'pushtrue'),
        ('W9', 'setlocal', 4),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlTopOn), L('ifeq', 'WS'),
        L('getlocal0'), L('getlocal', 4), L('callpropvoid', m_top, 1),
        # undo our x offsets once, then let the vanilla code place the rows
        ('WS', 'getlocal0'), L('getproperty', fmlCnt), L('pushbyte', 0), L('ifngt', 'NO'),
        L('pushbyte', 0), L('setlocal2'),
        ('RL', 'label'),
        L('getlocal2'), L('getlocal', 15), L('ifnlt', 'RD'),
        *lst, L('getlocal2'), L('callproperty', gra, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'RN'),
        L('getlocal3'), L('pushbyte', 0), L('setproperty', X),
        L('getlocal3'), L('pushbyte', 1), L('setproperty', alphaP),
        ('RN', 'inclocal_i', 2),
        L('jump', 'RL'),
        ('RD', 'getlocal0'), L('pushbyte', 0), L('initproperty', fmlCnt),
        L('getlocal0'), L('pushbyte', 1), L('callpropvoid', m_strip, 1),
        L('getlocal0'), L('callpropvoid', m_bar, 0),
        ('NO', 'pushfalse'), L('returnvalue'),
        # columns
        # Mods list only: logo and version text hidden, list moved up into their space (before the screen rect
        # is measured); any other long list keeps them
        ('COLS', 'getlocal0'), L('getlocal0'), L('getproperty', fmlMods), L('callpropvoid', m_top, 1),
        # row height from renderer 0's text, one line of it (NaN or under 42: 42); renderer 1 when row 0 is a
        # letter header (its bigger letter would space every row further apart)
        L('getlocal0'), L('getproperty', mcList),
        L('getlocal0'), L('pushbyte', 0), L('callproperty', m_ishdr, 1), L('convert_i'),
        L('callproperty', gra, 1),
        L('getproperty', tf), L('coerce_a'), L('setlocal', 6),
        L('getlocal', 6), L('getproperty', numLinesP), L('convert_i'), L('setlocal', 7),
        L('getlocal', 7), L('pushbyte', 1), L('ifge', 'NL1'),
        L('pushbyte', 1), L('setlocal', 7),
        ('NL1', 'getlocal', 6), L('getproperty', th), L('getlocal', 7), L('divide'),
        L('pushbyte', 17), L('add'), L('convert_d'), L('setlocal', 6),
        L('getlocal', 6), L('pushbyte', 42), L('ifge', 'RH'),
        L('pushbyte', 42), L('convert_d'), L('setlocal', 6),
        ('RH', 'getlex', cu), L('callproperty', gsr, 0), L('coerce_a'), L('setlocal', 4),
        L('getlocal0'), L('findpropstrict', pointC),
        L('getlocal', 4), L('getproperty', X), L('getlocal', 4), L('getproperty', Wd), L('add'),
        L('pushshort', EDGE_R), L('subtract'),
        L('getlocal', 4), L('getproperty', Y), L('getlocal', 4), L('getproperty', Hd), L('add'),
        L('pushshort', EDGE_B), L('subtract'),
        L('constructprop', pointC, 2), L('callproperty', g2l, 1), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('getproperty', Y), L('getlocal', 6), L('divide'), L('convert_i'), L('setlocal', 7),
        L('getlocal', 7), L('pushbyte', VANILLA_ROWS), L('ifnlt', 'MR'),
        L('pushbyte', VANILLA_ROWS), L('setlocal', 7),
        ('MR', 'getlocal', 5), L('getproperty', X), L('pushshort', COLW), L('divide'), L('convert_i'),
        L('increment_i'), L('setlocal', 8),
        L('getlocal', 8), L('pushbyte', 1), L('ifnlt', 'MC'),
        L('pushbyte', 1), L('setlocal', 8),
        ('MC', 'getlocal1'), L('getlocal', 7), L('add'), L('decrement'), L('getlocal', 7), L('divide'),
        L('convert_i'), L('setlocal', 9),
        L('getlocal', 9), L('getlocal', 8), L('ifngt', 'NC'),
        L('getlocal', 8), L('setlocal', 9),
        # rows per column: fill each column down to the bottom margin (maxRows; n when one column holds them all),
        # more than maxRows only when the screen width caps the columns (then they scroll)
        ('NC', 'getlocal', 7), L('setlocal', 10),
        L('getlocal', 10), L('getlocal1'), L('ifngt', 'P1'),
        L('getlocal1'), L('setlocal', 10),
        ('P1', 'getlocal1'), L('getlocal', 9), L('add'), L('decrement'), L('getlocal', 9), L('divide'),
        L('convert_i'), L('setlocal', 11),
        L('getlocal', 11), L('getlocal', 10), L('ifngt', 'P2'),
        L('getlocal', 11), L('setlocal', 10),
        ('P2', 'getlocal0'), L('getlocal', 10), L('initproperty', fmlPer),
        L('getlocal0'), L('getlocal1'), L('initproperty', fmlCnt),
        # Mods list: maxRows and the screen's columns for fmlGaps; with headers shown and the spacers placed for other
        # values (first open, resolution change), fmlUi shows the list again (once: the new values count as placed)
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'GP'),
        L('getlocal0'), L('getlocal', 7), L('initproperty', fmlMaxR),
        L('getlocal0'), L('getlocal', 8), L('initproperty', fmlScrC),
        *hdr_gate('GP', 'GG'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('iftrue', 'GP'),
        L('getlocal', 7), L('getlocal0'), L('getproperty', fmlGapR), L('ifne', 'GR'),
        L('getlocal', 8), L('getlocal0'), L('getproperty', fmlGapC), L('ifeq', 'GP'),
        ('GR', 'getlocal0'), L('getlocal', 7), L('initproperty', fmlGapR),
        L('getlocal0'), L('getlocal', 8), L('initproperty', fmlGapC),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlRegap),
        ('GP', 'pushbyte', 255), L('setlocal', 13),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('iflt', 'NL'),
        L('getlocal0'), L('getproperty', locked), L('getlocal', 10), L('divide'), L('convert_i'), L('setlocal', 13),
        # the dark strip behind the list spans every shown column
        ('NL', 'getlocal0'), L('getlocal', 9), L('getlocal', 13), L('pushbyte', 0), L('iflt', 'SW'),
        L('pop'), L('pushbyte', 1),
        ('SW', 'callpropvoid', m_strip, 1),
        L('getlocal0'), L('getlocal', 9), L('getlocal', 13), L('pushbyte', 0), L('iflt', 'SH'),
        L('pop'), L('pushbyte', 1),
        ('SH', 'initproperty', fmlShown),
        # rows in view: vis = min(per, maxRows); the rest scrolls
        L('getlocal', 10), L('setlocal', 14),
        L('getlocal', 14), L('getlocal', 7), L('ifngt', 'V1'),
        L('getlocal', 7), L('setlocal', 14),
        ('V1', 'getlocal0'), L('getlocal', 14), L('initproperty', fmlVis),
        L('getlocal0'), L('getlocal', 6), L('initproperty', fmlRowH),
        L('getlocal', 10), L('getlocal', 14), L('subtract'), L('convert_i'), L('setlocal', 16),
        # keyboard / pad moved the selection: bring its row into view
        L('getlocal0'), L('getproperty', fmlFollow), L('iffalse', 'CL'),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlFollow),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal', 17),
        L('getlocal', 17), L('pushbyte', 0), L('iflt', 'CL'),
        L('getlocal', 17), L('setlocal', 18),
        L('getlocal', 17), L('getlocal', 10), L('modulo'), L('convert_i'), L('setlocal', 17),
        # scrolling up to a group's first entry: its letter header (the row above, same column) comes into view too;
        # not for the right stick (fmlFrame moved the highlight to the top row: pulling the header in jerks the view)
        L('getlocal0'), L('getproperty', fmlStickY), L('pushbyte', 0), L('ifne', 'FH'),
        L('getlocal', 17), L('pushbyte', 0), L('ifngt', 'FH'),
        L('getlocal0'), L('getlocal', 18), L('decrement_i'), L('callproperty', m_ishdr, 1), L('iffalse', 'FH'),
        L('getlocal', 17), L('decrement_i'), L('getlocal0'), L('getproperty', fmlScroll), L('ifge', 'FH'),
        L('getlocal0'), L('getlocal', 17), L('decrement_i'), L('initproperty', fmlScroll),
        L('jump', 'CL'),
        ('FH', 'getlocal', 17), L('getlocal0'), L('getproperty', fmlScroll), L('ifge', 'F1'),
        L('getlocal0'), L('getlocal', 17), L('initproperty', fmlScroll),
        L('jump', 'CL'),
        ('F1', 'getlocal', 17), L('getlocal0'), L('getproperty', fmlScroll), L('getlocal', 14), L('add'),
        L('iflt', 'CL'),
        L('getlocal0'), L('getlocal', 17), L('getlocal', 14), L('subtract'), L('increment'), L('convert_i'),
        L('initproperty', fmlScroll),
        ('CL', 'getlocal0'), L('getproperty', fmlScroll), L('getlocal', 16), L('ifngt', 'C1'),
        L('getlocal0'), L('getlocal', 16), L('initproperty', fmlScroll),
        ('C1', 'getlocal0'), L('getproperty', fmlScroll), L('pushbyte', 0), L('ifge', 'C2'),
        L('getlocal0'), L('pushbyte', 0), L('initproperty', fmlScroll),
        ('C2', 'pushbyte', 0), L('setlocal2'),
        ('LL', 'label'),
        L('getlocal2'), L('getlocal1'), L('ifnlt', 'LD'),
        L('getlocal2'), L('getlocal', 10), L('divide'), L('convert_i'), L('setlocal', 11),
        L('getlocal2'), L('getlocal', 10), L('modulo'), L('getlocal0'), L('getproperty', fmlScroll), L('subtract'),
        L('convert_d'), L('setlocal', 12),
        *lst, L('getlocal2'), L('callproperty', gra, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'LN'),
        # shown = row (partly) in view && (no option page open || this is the open entry's column)
        L('getlocal3'),
        L('getlocal', 12), L('pushbyte', 255), L('greaterthan'),
        L('dup'), L('iffalse', 'V9'), L('pop'),
        L('getlocal', 12), L('getlocal', 14), L('lessthan'),
        ('V9', 'dup'), L('iffalse', 'V8'), L('pop'),
        L('getlocal', 13), L('pushbyte', 0), L('lessthan'),
        L('dup'), L('iftrue', 'V8'), L('pop'),
        L('getlocal', 11), L('getlocal', 13), L('equals'),
        ('V8', 'setproperty', vis),
        # rows partly scrolled out at the top or bottom fade with the part that is out
        L('getlocal3'),
        L('getlocal', 12), L('pushbyte', 0), L('ifge', 'A1'),
        L('pushbyte', 1), L('getlocal', 12), L('pushbyte', TOP_FADE), L('multiply'), L('add'), L('convert_d'),
        L('dup'), L('pushbyte', 0), L('ifgt', 'AS'),
        # faded out: hidden, so it can't be clicked either
        L('pop'), L('getlocal3'), L('pushfalse'), L('setproperty', vis), L('pushbyte', 0), L('convert_d'),
        L('jump', 'AS'),
        ('A1', 'getlocal', 12), L('getlocal', 14), L('decrement'), L('ifngt', 'A2'),
        L('getlocal', 14), L('getlocal', 12), L('subtract'), L('convert_d'), L('jump', 'AS'),
        ('A2', 'pushbyte', 1), L('convert_d'),
        ('AS', 'setproperty', alphaP),
        L('getlocal', 13), L('pushbyte', 0), L('iflt', 'XF'),
        # an option page is open: the open entry's column sits at the first column's place
        L('getlocal3'), L('pushbyte', 0), L('setproperty', X),
        L('jump', 'PY'),
        ('XF', 'getlocal3'), L('getlocal', 11), L('pushshort', COLW), L('multiply'), L('setproperty', X),
        ('PY', 'getlocal3'), L('getlocal', 12), L('getlocal', 6), L('multiply'), L('setproperty', Y),
        ('LN', 'inclocal_i', 2),
        L('jump', 'LL'),
        ('LD', 'getlocal0'), L('callpropvoid', m_bar, 0),
        L('pushtrue'), L('returnvalue'),
    ]

    # fmlNav(e):Boolean  1 e, 2 details, 3 dir, 4 i, 5 per
    upA, pcUpA, downA, pcDownA = pubn('UpAction'), pubn('PCUpAction'), pubn('DownAction'), pubn('PCDownAction')
    s_hold = string('keyHold')
    nav = [
        # A to Z / By category with headers (any layout): Up / Down step over the header rows here. Vanilla moveDown skips them,
        # but moveUp's separator test is always true, so Up would land on a header. Same keys as the list's
        # handleInput (UpAction / PCUpAction / DownAction / PCDownAction); a single press past either end wraps
        # (the menu list's "wrap" mode), a held key stops there; keyUp is left to vanilla (it only tells the
        # script).   2 details, 3 dir, 4 code, 5 n, 6 value, 7 i, 8 wrapped
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'HX'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'HX'),
        *hdr_gate('HX', 'NG'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('iftrue', 'HX'),
        L('getlocal1'), L('getproperty', handled), L('iftrue', 'HX'),
        L('getlocal1'), L('getproperty', details), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'HX'),
        L('getlocal2'), L('getproperty', codeP), L('convert_i'), L('setlocal', 4),
        L('pushbyte', 255), L('setlocal3'),
        L('getlocal', 4), *lst, L('getproperty', upA), L('ifeq', 'HG'),
        L('getlocal', 4), *lst, L('getproperty', pcUpA), L('ifeq', 'HG'),
        L('pushbyte', 1), L('setlocal3'),
        L('getlocal', 4), *lst, L('getproperty', downA), L('ifeq', 'HG'),
        L('getlocal', 4), *lst, L('getproperty', pcDownA), L('ifne', 'HX'),
        ('HG', 'getlocal2'), L('getproperty', valueP), L('convert_s'), L('coerce_a'), L('setlocal', 6),
        L('getlocal', 6), L('pushstring', s_up), L('ifeq', 'HX'),
        L('getlocal1'), L('pushtrue'), L('setproperty', handled),
        L('pushbyte', 0), L('setlocal', 5),
        *lst, L('getproperty', dprov), L('iffalse', 'YES'),
        *lst, L('getproperty', dprov), L('getproperty', length), L('convert_i'), L('setlocal', 5),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal', 7),
        L('pushfalse'), L('setlocal', 8),
        # nothing selected: Down starts above the first row, Up below the last
        L('getlocal', 7), L('pushbyte', 0), L('ifge', 'HL'),
        L('getlocal', 5), L('setlocal', 7),
        L('getlocal3'), L('pushbyte', 0), L('iflt', 'HL'),
        L('pushbyte', 255), L('setlocal', 7),
        ('HL', 'label'),
        L('getlocal', 7), L('getlocal3'), L('add'), L('convert_i'), L('setlocal', 7),
        L('getlocal', 7), L('pushbyte', 0), L('iflt', 'HW'),
        L('getlocal', 7), L('getlocal', 5), L('iflt', 'HC'),
        ('HW', 'getlocal', 6), L('pushstring', s_hold), L('ifeq', 'YES'),
        L('getlocal', 8), L('iftrue', 'YES'),
        L('pushtrue'), L('setlocal', 8),
        L('getlocal', 5), L('setlocal', 7),
        L('getlocal3'), L('pushbyte', 0), L('iflt', 'HL'),
        L('pushbyte', 255), L('setlocal', 7),
        L('jump', 'HL'),
        ('HC', 'getlocal0'), L('getlocal', 7), L('callproperty', m_ishdr, 1), L('iftrue', 'HL'),
        # the setter plays the highlight sound and sends INDEX_CHANGE (fmlFollowSel brings the row into view)
        *lst, L('getlocal', 7), L('setproperty', selIdx),
        L('jump', 'YES'),
        ('HX', 'getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'NO'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'NO'),
        L('getlocal1'), L('getproperty', details), L('coerce_a'), L('setlocal2'),
        L('pushbyte', 0), L('setlocal3'),
        # right stick: the axis event (code 1001, y > 0 is up) or the stick's up/down keys (201 / 202) set
        # fmlStickY (-1..1, up > 0); fmlFrame scrolls by it every frame.   4 code, 5 y*|y|
        L('getlocal2'), L('getproperty', codeP), L('convert_i'), L('setlocal', 4),
        L('getlocal', 4), L('pushshort', 1001), L('ifne', 'DG'),
        L('getlocal1'), L('pushtrue'), L('setproperty', handled),
        L('getlocal2'), L('getproperty', valueP), L('coerce_a'), L('setlocal', 6),
        L('getlocal', 6), L('iffalse', 'YES'),
        L('getlocal', 6), L('getproperty', yval), L('convert_d'), L('setlocal', 7),
        L('getlocal', 7), L('getlocal', 7), L('multiply'), L('convert_d'), L('setlocal', 5),
        L('getlocal', 5), L('pushdouble', d_dead2), L('ifnlt', 'SG'),
        L('pushbyte', 0), L('convert_d'), L('setlocal', 5),
        L('jump', 'SY'),
        ('SG', 'getlocal', 7), L('pushbyte', 0), L('ifge', 'SY'),
        L('getlocal', 5), L('negate'), L('convert_d'), L('setlocal', 5),
        ('SY', 'getlocal0'), L('getlocal', 5), L('initproperty', fmlStickY),
        L('jump', 'YES'),
        ('DG', 'getlocal', 4), L('pushshort', 201), L('ifeq', 'DU'),
        L('getlocal', 4), L('pushshort', 202), L('ifne', 'NS'),
        L('pushbyte', 255), L('convert_d'), L('setlocal', 5),
        L('jump', 'DK'),
        ('DU', 'pushbyte', 1), L('convert_d'), L('setlocal', 5),
        ('DK', 'getlocal1'), L('pushtrue'), L('setproperty', handled),
        L('getlocal2'), L('getproperty', valueP), L('pushstring', s_up), L('ifne', 'DS'),
        L('pushbyte', 0), L('convert_d'), L('setlocal', 5),
        ('DS', 'getlocal0'), L('getlocal', 5), L('initproperty', fmlStickY),
        L('jump', 'YES'),
        ('NS', 'getlocal2'), L('getproperty', navEq), L('pushstring', s_right), L('ifne', 'NR'),
        L('pushbyte', 1), L('setlocal3'),
        ('NR', 'getlocal2'), L('getproperty', navEq), L('pushstring', s_left), L('ifne', 'NL'),
        L('pushbyte', 255), L('setlocal3'),
        ('NL', 'getlocal3'), L('pushbyte', 0), L('ifeq', 'NO'),
        L('getlocal1'), L('pushtrue'), L('setproperty', handled),
        L('getlocal2'), L('getproperty', valueP), L('pushstring', s_up), L('ifeq', 'YES'),
        L('getlocal0'), L('getproperty', fmlPer), L('setlocal', 5),
        *lst, L('getproperty', selIdx), L('getlocal3'), L('getlocal', 5), L('multiply'), L('add'), L('convert_i'),
        L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', 0), L('iflt', 'YES'),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlCnt), L('iflt', 'SET'),
        # past the end going right: the last entry, if it is in a later column
        L('getlocal3'), L('pushbyte', 0), L('ifngt', 'YES'),
        L('getlocal0'), L('getproperty', fmlCnt), L('decrement'), L('getlocal', 5), L('divide'), L('convert_i'),
        *lst, L('getproperty', selIdx), L('getlocal', 5), L('divide'), L('convert_i'), L('ifngt', 'YES'),
        L('getlocal0'), L('getproperty', fmlCnt), L('decrement'), L('convert_i'), L('setlocal', 4),
        # a letter header in a column's last row: its entries start the next column, so the hook 10 skip (+1)
        # would jump a column too far; take the entry above it, same column
        ('SET', 'getlocal0'), L('getlocal', 4), L('callproperty', m_ishdr, 1), L('iffalse', 'SS'),
        L('getlocal', 4), L('increment_i'), L('getlocal', 5), L('modulo'), L('convert_i'), L('pushbyte', 0),
        L('ifne', 'SS'),
        L('getlocal', 4), L('pushbyte', 1), L('ifngt', 'SS'),
        L('declocal_i', 4),
        ('SS', 'getlocal0'), L('getproperty', mcList), L('getlocal', 4), L('setproperty', selIdx),
        ('YES', 'pushtrue'), L('returnvalue'),
        ('NO', 'pushfalse'), L('returnvalue'),
    ]

    # fmlRepos(e): the list's drawLayout put every renderer back in one column
    rep = [
        L('getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'END'),
        L('getlocal0'), L('callpropvoid', repR, 0),
        ('END', 'returnvoid'),
    ]

    # fmlHide(): hideSelection for renderers 11..N   1 i, 2 k, 3 r
    hide = [
        *lst, L('getproperty', numR), L('convert_i'), L('setlocal2'),
        L('pushbyte', VANILLA_ROWS), L('setlocal1'),
        ('HL', 'label'),
        L('getlocal1'), L('getlocal2'), L('ifnlt', 'END'),
        *lst, L('getlocal1'), L('callproperty', gra, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'HN'),
        L('getlocal3'), L('getlocal0'), L('getproperty', hideSel), L('setproperty', hideSel),
        ('HN', 'inclocal_i', 1),
        L('jump', 'HL'),
        ('END', 'returnvoid'),
    ]

    # fmlStrip(cols): the module's unnamed dark strip (shape 369 x 1920 centred on the rows) covers cols columns;
    # a 9-slice grid keeps its ragged side edges at their own width.   1 cols, 2 i, 3 child, 4 n
    strip = [
        L('getlocal0'), L('getproperty', fmlBg), L('iftrue', 'GOT'),
        L('getlocal0'), L('getproperty', numCh), L('convert_i'), L('setlocal', 4),
        L('pushbyte', 0), L('setlocal2'),
        ('FL', 'label'),
        L('getlocal2'), L('getlocal', 4), L('ifnlt', 'END'),
        L('getlocal0'), L('getlocal2'), L('callproperty', gca, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('getproperty', Hd), L('pushshort', 1500), L('ifngt', 'FN'),
        L('getlocal3'), L('getproperty', Wd), L('pushshort', 300), L('ifngt', 'FN'),
        L('getlocal3'), L('getproperty', Wd), L('pushshort', 450), L('ifnlt', 'FN'),
        L('getlocal3'), L('getproperty', scX), L('pushbyte', 1), L('ifne', 'FN'),
        L('getlocal0'), L('getlocal3'), L('initproperty', fmlBg),
        L('getlocal0'), L('getlocal3'), L('getproperty', X), L('initproperty', fmlBgX),
        L('jump', 'GOT'),
        ('FN', 'inclocal_i', 2),
        L('jump', 'FL'),
        ('GOT', 'getlocal0'), L('getproperty', fmlBg), L('iffalse', 'END'),
        # 2 = extra width on the right: column mode (fmlCnt is 0 in the vanilla layout) with no settings page open
        L('pushbyte', 0), L('setlocal2'),
        L('getlocal0'), L('getproperty', fmlCnt), L('pushbyte', 0), L('ifngt', 'NX'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'NX'),
        L('pushshort', STRIP_EXTRA), L('setlocal2'),
        ('NX', 'getlocal1'), L('pushbyte', 1), L('ifgt', 'S9'),
        L('getlocal2'), L('pushbyte', 0), L('ifngt', 'ONE'),
        ('S9', 'getlocal0'), L('getproperty', fmlBg),
        L('findpropstrict', rectC), L('pushbyte', 0), L('pushshort', 150), L('subtract'),
        L('pushbyte', 0), L('pushshort', 900), L('subtract'),
        L('pushshort', 300), L('pushshort', 1800),
        L('constructprop', rectC, 4), L('setproperty', s9),
        ('ONE', 'getlocal0'), L('getproperty', fmlBg),
        L('getlocal1'), L('decrement'), L('pushshort', COLW), L('multiply'), L('pushshort', STRIP_W), L('add'),
        L('getlocal2'), L('add'), L('pushshort', STRIP_W), L('divide'), L('setproperty', scX),
        L('getlocal0'), L('getproperty', fmlBg),
        L('getlocal0'), L('getproperty', fmlBgX),
        L('getlocal1'), L('decrement'), L('pushshort', COLW), L('multiply'), L('getlocal2'), L('add'),
        L('pushbyte', 2), L('divide'), L('add'), L('setproperty', X),
        ('END', 'returnvoid'),
    ]

    # fmlBar(): scroll bar right of the last shown column; only while rows are scrolled out of view.
    #           1 bar, 2 graphics, 3 trackH, 4 thumbH, 5 thumbY
    def listen(target, s_type, method):
        return [*target, L('pushstring', s_type), L('getlocal0'), L('getproperty', method),
                L('pushfalse'), L('pushbyte', 0), L('pushtrue'), L('callpropvoid', ael, 5)]
    stage = [L('getlocal0'), L('getproperty', stageP)]
    rect = lambda *v: [L('getlocal2'), *v, L('callpropvoid', g_dr, 4)]
    fill = lambda d: [L('getlocal2'), L('pushint', i_white), L('pushdouble', d), L('callpropvoid', g_bf, 2)]
    bar = [
        L('getlocal0'), L('getproperty', fmlBarS), L('coerce_a'), L('setlocal1'),
        L('getlocal1'), L('iftrue', 'HAVE'),
        L('findpropstrict', spriteC), L('constructprop', spriteC, 0), L('coerce_a'), L('setlocal1'),
        L('getlocal0'), L('getlocal1'), L('initproperty', fmlBarS),
        L('getlocal0'), L('getlocal1'), L('callpropvoid', addChild, 1),
        *listen([L('getlocal1')], s_mdown, m_bdown),
        L('getlocal0'), L('getproperty', stageP), L('iffalse', 'HAVE'),
        *listen(stage, s_mmove, m_bmove),
        *listen(stage, s_mup, m_bup),
        ('HAVE', 'getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'OFF'),
        L('getlocal0'), L('getproperty', fmlPer), L('getlocal0'), L('getproperty', fmlVis), L('ifgt', 'ON'),
        ('OFF', 'getlocal1'), L('pushfalse'), L('setproperty', vis),
        L('returnvoid'),
        ('ON', 'getlocal1'), L('pushtrue'), L('setproperty', vis),
        L('getlocal1'), L('getlocal0'), L('getproperty', fmlShown), L('decrement'), L('pushshort', COLW),
        L('multiply'), L('pushshort', BAR_X), L('add'), L('setproperty', X),
        L('getlocal1'), L('pushbyte', 0), L('pushbyte', 6), L('subtract'), L('setproperty', Y),
        L('getlocal0'), L('getproperty', fmlVis), L('getlocal0'), L('getproperty', fmlRowH), L('multiply'),
        L('convert_d'), L('setlocal3'),
        L('getlocal3'), L('getlocal0'), L('getproperty', fmlVis), L('multiply'), L('getlocal0'),
        L('getproperty', fmlPer), L('divide'), L('convert_d'), L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', 24), L('ifnlt', 'TH'),
        L('pushbyte', 24), L('convert_d'), L('setlocal', 4),
        ('TH', 'getlocal3'), L('getlocal', 4), L('subtract'), L('getlocal0'), L('getproperty', fmlScroll),
        L('multiply'), L('getlocal0'), L('getproperty', fmlPer), L('getlocal0'), L('getproperty', fmlVis),
        L('subtract'), L('divide'), L('convert_d'), L('setlocal', 5),
        L('getlocal1'), L('getproperty', gfx), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('callpropvoid', g_clear, 0),
        *fill(d_hit), *rect(L('pushbyte', 0), L('pushbyte', 10), L('subtract'), L('pushbyte', 0),
                            L('pushbyte', 26), L('getlocal3')),
        *fill(d_track), *rect(L('pushbyte', 0), L('pushbyte', 0), L('pushbyte', 6), L('getlocal3')),
        *fill(d_thumb), *rect(L('pushbyte', 0), L('getlocal', 5), L('pushbyte', 6), L('getlocal', 4)),
        L('getlocal2'), L('callpropvoid', g_ef, 0),
        L('returnvoid'),
    ]
    # fmlBarDown(e) / fmlBarMove(e) / fmlBarUp(e): click or drag on the bar: the thumb's centre follows the mouse
    bdown = [
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlDrag),
        L('getlocal0'), L('getlocal1'), L('callpropvoid', m_bmove, 1),
        L('returnvoid'),
    ]
    # 1 e, 2 trackH
    bmove = [
        L('getlocal0'), L('getproperty', fmlDrag), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', fmlBarS), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', fmlVis), L('getlocal0'), L('getproperty', fmlRowH), L('multiply'),
        L('convert_d'), L('setlocal2'),
        L('getlocal2'), L('pushbyte', 1), L('iflt', 'END'),
        L('getlocal0'),
        L('getlocal0'), L('getproperty', fmlBarS), L('getproperty', mouseY), L('getlocal2'), L('divide'),
        L('getlocal0'), L('getproperty', fmlPer), L('multiply'),
        L('getlocal0'), L('getproperty', fmlVis), L('pushbyte', 2), L('divide'), L('subtract'),
        L('initproperty', fmlScroll),
        L('getlocal0'), L('callpropvoid', repR, 0),
        ('END', 'returnvoid'),
    ]
    bup = [L('getlocal0'), L('pushfalse'), L('initproperty', fmlDrag), L('returnvoid')]
    # fmlWheel(e): WHEEL_ROWS rows per notch
    wheel = [
        L('getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'END'),
        L('getlocal1'), L('getproperty', delta), L('pushbyte', 0), L('ifngt', 'DN'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlScroll), L('pushbyte', WHEEL_ROWS), L('subtract'),
        L('initproperty', fmlScroll),
        L('jump', 'GO'),
        ('DN', 'getlocal1'), L('getproperty', delta), L('pushbyte', 0), L('ifnlt', 'END'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlScroll), L('pushbyte', WHEEL_ROWS), L('add'),
        L('initproperty', fmlScroll),
        ('GO', 'getlocal0'), L('callpropvoid', repR, 0),
        ('END', 'returnvoid'),
    ]
    # fmlFollowSel(): the selection changed: the next layout brings it into view
    follow = [
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlFollow),
        L('getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'END'),
        L('getlocal0'), L('callpropvoid', repR, 0),
        ('END', 'returnvoid'),
    ]

    # fmlTop(on): column mode hides the game logo and the menu's version text and moves the list up into their
    #             space; off puts both back.   1 on, 2 parent
    top = [
        L('getlocal0'), L('getlocal1'), L('convert_b'), L('initproperty', fmlTopOn),
        L('getlocal0'), L('getproperty', fmlY0Set), L('iftrue', 'HAVE'),
        L('getlocal0'), L('getlocal0'), L('getproperty', Y), L('initproperty', fmlY0),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlY0Set),
        ('HAVE', 'getlocal1'), L('iffalse', 'OFF'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlY0), L('pushshort', TOP_SHIFT), L('subtract'),
        L('setproperty', Y),
        L('jump', 'LOGO'),
        ('OFF', 'getlocal0'), L('getlocal0'), L('getproperty', fmlY0), L('setproperty', Y),
        ('LOGO', 'getlocal0'), L('getproperty', logo), L('iffalse', 'VER'),
        L('getlocal0'), L('getproperty', logo), L('getlocal1'), L('not'), L('setproperty', vis),
        ('VER', 'getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        L('pushstring', s_ver), L('getlocal2'), L('in'), L('iffalse', 'END'),
        L('getlocal2'), L('getproperty', verP), L('iffalse', 'END'),
        L('getlocal2'), L('getproperty', verP), L('getlocal1'), L('not'), L('setproperty', vis),
        ('END', 'returnvoid'),
    ]

    # fmlFrame(e): while the right stick is held, scroll STICK_SPEED rows/s * fmlStickY; a highlight that leaves
    #              the screen moves to the top row in view of its column.   1 e, 2 now, 3 ms / top row, 4 sel, 5 row
    frame = [
        L('getlocal0'), L('callpropvoid', m_ui, 0),
        L('getlocal0'), L('getproperty', fmlStickY), L('pushbyte', 0), L('ifeq', 'IDLE'),
        L('getlocal0'), L('getproperty', fmlCnt), L('pushbyte', VANILLA_ROWS), L('ifngt', 'STOP'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'STOP'),
        L('findpropstrict', getTimer), L('callproperty', getTimer, 0), L('convert_d'), L('setlocal2'),
        L('getlocal2'), L('getlocal0'), L('getproperty', fmlStickT), L('subtract'), L('convert_d'), L('setlocal3'),
        L('getlocal0'), L('getlocal2'), L('initproperty', fmlStickT),
        L('getlocal3'), L('pushbyte', 100), L('ifgt', 'D1'),
        L('getlocal3'), L('pushbyte', 0), L('ifgt', 'D2'),
        ('D1', 'pushbyte', 16), L('convert_d'), L('setlocal3'),
        ('D2', 'getlocal0'), L('getlocal0'), L('getproperty', fmlScroll),
        L('getlocal0'), L('getproperty', fmlStickY), L('getlocal3'), L('multiply'), L('pushdouble', d_speed),
        L('multiply'), L('subtract'), L('initproperty', fmlScroll),
        L('getlocal0'), L('callpropvoid', repR, 0),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', 0), L('iflt', 'END'),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlPer), L('modulo'), L('convert_d'), L('setlocal', 5),
        L('getlocal', 5), L('getlocal0'), L('getproperty', fmlScroll), L('iflt', 'MOVE'),
        L('getlocal', 5), L('getlocal0'), L('getproperty', fmlScroll), L('getlocal0'), L('getproperty', fmlVis),
        L('add'), L('pushbyte', 1), L('subtract'), L('ifngt', 'END'),
        # top row fully in view = ceil(scroll)
        ('MOVE', 'getlocal0'), L('getproperty', fmlScroll), L('convert_i'), L('setlocal3'),
        L('getlocal3'), L('getlocal0'), L('getproperty', fmlScroll), L('ifnlt', 'C0'),
        L('inclocal_i', 3),
        ('C0', 'getlocal', 4), L('getlocal', 5), L('subtract'), L('getlocal3'), L('add'), L('convert_i'),
        L('setlocal', 4),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlCnt), L('iflt', 'SET'),
        L('getlocal0'), L('getproperty', fmlCnt), L('decrement'), L('convert_i'), L('setlocal', 4),
        ('SET', 'getlocal0'), L('getproperty', mcList), L('getlocal', 4), L('setproperty', selIdx),
        ('END', 'returnvoid'),
        ('STOP', 'getlocal0'), L('pushbyte', 0), L('initproperty', fmlStickY),
        ('IDLE', 'getlocal0'), L('pushbyte', 0), L('initproperty', fmlStickT),
        L('returnvoid'),
    ]

    # ---- sort and search (Options > Mods only) ---------------------------------------------------------------------
    # fmlView(dp) returns the list to show: fmlAll (the Mods entries without Back, kept from the last fresh list)
    # filtered by fmlSearch and sorted by fmlSort, then Back. A fresh list also clears the search and tells the
    # script its ids ("seen"). The script answers through IngameMenu.fmlSetData -> fmlParse with the stored sort and
    # the first-seen / last-opened stamps of every id.
    late = abc_late(c)
    typeP = pubn('type')
    pushM, spliceM, concatM, splitM = pubn('push'), pubn('splice'), pubn('concat'), pubn('split')
    lowerM, upperM, idxM, charAtM, substrM = (pubn('toLowerCase'), pubn('toUpperCase'), pubn('indexOf'),
                                              pubn('charAt'), pubn('substr'))
    textP, ifmP = pubn('text'), pubn('mcInputFeedbackModule')
    appendB, removeB = pubn('appendButton'), pubn('removeButton')
    navC, r3P = c.used_mn('NavigationCode', ('getlex',)), pubn('GAMEPAD_R3')
    ttl = c.trait_mn(tr, 'txtMenuListTitle', (0,))
    dins = abcrt.decode(lbody['code'])
    igmLex = next(x[2][0] for x in dins if op_name(x) == 'getlex' and abc.mn(x[2][0]) == 'IngameMenu')
    backP = next(x[2][0] for x in dins if op_name(x) == 'getproperty' and abc.mn(x[2][0]) == 'IGMActionType_Back')
    arrC = next(x[2][0] for x in dins if op_name(x) == 'coerce' and abc.mn(x[2][0]) == 'Array')
    dpC = c.used_mn('DataProvider', ('constructprop',), 'pkg:scaleform.clik.data::DataProvider')
    ains = abcrt.decode(c.body('IngameMenu::activateMenuListItem')['code'])
    pick = lambda op, n: next(x[2][0] for x in ains if op_name(x) == op and abc.mn(x[2][0]) == n)
    geFind, geLex, geCall = pick('findpropstrict', 'GameEvent'), pick('getlex', 'GameEvent'), pick('getproperty', 'CALL')
    geNew, dispM = pick('constructprop', 'GameEvent'), pick('callpropvoid', 'dispatchEvent')
    s_empty, s_semi, s_bar, s_colon = string(''), string(';'), string('|'), string(':')
    s_onfml, s_seen, s_open, s_sort = string('OnFmlEvent'), string('seen'), string('open'), string('sort')
    s_snd, s_deny = string('OnPlaySoundEvent'), string('gui_global_slider_move_failed')
    s_chars, s_dash = string('abcdefghijklmnopqrstuvwxyz0123456789'), string('  -  ')
    s_sortp, s_names, s_ifm = string('Sort'), string(SORT_NAMES), string('mcInputFeedbackModule')
    s_hdrname, s_r2 = string(HDR_NAME), string('gamepad_R2')     # NavigationCode.GAMEPAD_R2 (the RT icon)
    fmlSearch, fmlRefr = nm('fmlSearch'), nm('fmlRefr')
    fmlSeen, fmlOpen, fmlPrompt, fmlTBase, fmlTSet = (nm('fmlSeen'), nm('fmlOpen'), nm('fmlPrompt'), nm('fmlTBase'),
                                                      nm('fmlTSet'))
    fmlPSeen, fmlPOpen, fmlPSort = nm('fmlPendSeen'), nm('fmlPendOpen'), nm('fmlPendSort')
    fmlNames = nm('fmlNames')       # [A to Z, Newest first, Recently opened, By category, Sort(, Headers(, Category,
    #                                 the NUM_CATS category names))] from the script, or null
    M.add_slot(c, ci, fmlNames, 0, 0, 0)
    # the sort names: fmlNames, else the English SORT_NAMES (leaves the Array on the stack)
    names = lambda lab: [L('getlocal0'), L('getproperty', fmlNames), L('dup'), L('iftrue', lab), L('pop'),
                         L('pushstring', s_names), L('pushstring', s_bar), L('callproperty', splitM, 1),
                         (lab, 'nop')]
    fmlLastDP = nm('fmlLastDP')
    M.add_slot(c, ci, fmlLastDP, 0, 0, 0)
    fmlOpenTop = nm('fmlOpenTop')
    M.add_slot(c, ci, fmlOpenTop, t_num, 0, 0)
    # fmlBackId: the id of the Mods entry last opened (hook 7), until the list is shown again. fmlSelOut: the index
    # fmlView wants selected instead of the one the menu restores (-1 = keep the menu's)
    fmlBackId, fmlSelOut, fmlNoRs = nm('fmlBackId'), nm('fmlSelOut'), nm('fmlNoRs')
    M.add_slot(c, ci, fmlBackId, 0, 0, 0)
    M.add_slot(c, ci, fmlNoRs, t_bool, 0, 0)
    M.add_slot(c, ci, fmlSelOut, t_int, 0, 0)
    # fmlKeepId: the id to select in the next fmlView (headers toggled). fmlHPrompt: the "Headers" prompt is shown
    fmlKeepId, fmlHPrompt = nm('fmlKeepId'), nm('fmlHPrompt')
    M.add_slot(c, ci, fmlKeepId, 0, 0, 0)
    M.add_slot(c, ci, fmlHPrompt, t_bool, 0, 0)
    # fmlKind: the category the script set on a Mods row (0..NUM_CATS-1; -1 = a Menu Organizer category).
    # fmlPendCat: "id:kind" to tell the script (X / Insert). fmlCPrompt: the "Category" prompt is shown
    fmlKindP, s_fmlkind = pubn('fmlKind'), string('fmlKind')
    s_cat, s_catnames, s_catp, s_x = (string('cat'), string(CAT_NAMES), string('Change category'),
                                      string('gamepad_X'))
    fmlPCat, fmlCPrompt = nm('fmlPendCat'), nm('fmlCPrompt')
    M.add_slot(c, ci, fmlPCat, 0, 0, 0)
    M.add_slot(c, ci, fmlCPrompt, t_bool, 0, 0)
    m_kind, m_cname, m_cnext = nm('fmlKindOf'), nm('fmlCatName'), nm('fmlCatNext')
    # Reset categories (Y / Home, By category only): fmlGuess = the script's guess on a Mods row (newer scripts).
    # fmlRArmT: getTimer() of the first press (0 = not armed). fmlRPrompt: the prompt is shown, fmlRShown: with the
    # armed label. fmlPendRst: tell the script "catreset" next frame
    fmlGuessP, s_fmlguess = pubn('fmlGuess'), string('fmlGuess')
    s_crst, s_y, s_q = string('catreset'), string('gamepad_Y'), string('?')
    s_rstp, s_rsta = string(RST_NAME), string(RST_ARMED)
    fmlRArmT, fmlRPrompt, fmlRShown, fmlPRst = nm('fmlRArmT'), nm('fmlRPrompt'), nm('fmlRShown'), nm('fmlPendRst')
    M.add_slot(c, ci, fmlRArmT, t_num, 0, 0)
    M.add_slot(c, ci, fmlRPrompt, t_bool, 0, 0)
    M.add_slot(c, ci, fmlRShown, t_bool, 0, 0)
    M.add_slot(c, ci, fmlPRst, 0, 0, 0)
    m_crst, m_rrow = nm('fmlCatReset'), nm('fmlRstRow')
    # favorites: the script sets fmlFav on each Mods row; fmlPendFav = "id:0|1" to tell the script;
    # fmlFvPrompt = the Favorite prompt is shown
    fmlFavP, fmlCatP = pubn('fmlFav'), c.new_name(X, 'fmlCat')
    fmlPFav, fmlFvPr = nm('fmlPendFav'), nm('fmlFvPrompt')
    for f, t in ((fmlPFav, 0), (fmlFvPr, t_bool)):
        M.add_slot(c, ci, f, t, 0, 0)
    m_flag, m_fpr = nm('fmlFlag'), nm('fmlFlagPrompts')
    s_fav = string('fav')
    s_favp, s_favs = string('Favorite'), string('Favorites')
    s_l1 = string('gamepad_L1')
    s_fgold, s_amp, s_eamp = string('<font color="#%06X">' % HDR_GOLD), string('&'), string('&amp;')
    s_lt, s_elt, s_gt, s_egt = string('<'), string('&lt;'), string('>'), string('&gt;')
    joinM = pubn('join')
    s_fmlfav = string('fmlFav')
    # a label from fmlNames (newer scripts), else the English one (leaves a String)
    nlabel = lambda idx, eng, lab: [L('pushstring', eng),
                                    L('getlocal0'), L('getproperty', fmlNames), L('iffalse', lab),
                                    L('getlocal0'), L('getproperty', fmlNames), L('getproperty', length),
                                    L('pushbyte', idx + 1), L('iflt', lab),
                                    L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', idx),
                                    L('getproperty', late), L('convert_s'),
                                    (lab, 'nop')]
    subElP, s_subel = pubn('subElements'), string('subElements')
    for f, t in ((fmlSort, t_int), (fmlSearch, 0), (fmlAll, 0), (fmlRefr, t_bool), (fmlSeen, 0), (fmlOpen, 0),
                 (fmlPrompt, t_bool), (fmlTBase, 0), (fmlTSet, 0), (fmlPSeen, 0), (fmlPOpen, 0), (fmlPSort, 0)):
        M.add_slot(c, ci, f, t, 0, 0)
    m_view, m_less, m_refresh, m_tell = nm('fmlView'), nm('fmlLess'), nm('fmlRefresh'), nm('fmlTell')
    m_parse = nm('fmlParse')
    lastMO = next(x[2][0] for x in abcrt.decode(lbody['code'])
                  if op_name(x) == 'getproperty' and abc.mn(x[2][0]) == '_lastMouseOveredItem')
    titleP, listT = pubn('titleText'), c.used_mn('listTitle', ('getproperty',))
    s_p1, s_p2 = string("<p align='center'>"), string("</p><p align='center'><font size='20'>")
    s_p3, s_dots = string('</font></p>'), string('...')
    fmlTHtml = nm('fmlTHtml')
    M.add_slot(c, ci, fmlTHtml, 0, 0, 0)
    # fmlPrep: every new list forgets the title it had; the shown container's listTitle (what the menu shows as the
    # title) is the base
    prep[0:0] = [L('getlocal0'), L('pushnull'), L('initproperty', fmlTBase),
                 L('getlocal0'), L('pushnull'), L('initproperty', fmlTHtml)]
    k = [i for i in range(len(prep) - 1) if prep[i] == L('getlocal', 9) and prep[i + 1] == L('getproperty', idP)]
    if len(k) != 1:
        raise PatchError('fmlPrep: container id read not found')
    prep[k[0]:k[0]] = [L('getlocal0'), L('getlocal', 9), L('getproperty', listT), L('coerce_a'),
                       L('initproperty', fmlTBase)]
    isBack = lambda loc, miss_or_hit, op: [L('getlocal', loc), L('getproperty', typeP), L('getlex', igmLex),
                                           L('getproperty', backP), L(op, miss_or_hit)]

    # fmlView(dp):Array   1 dp, 2 out, 3 i, 4 item, 5 back, 6 ids, 7 j, 8 search, 9 id to select
    view = [
        L('getlocal0'), L('pushbyte', 255), L('initproperty', fmlSelOut),
        L('pushnull'), L('setlocal', 9),
        L('getlocal0'), L('getproperty', fmlMods), L('iftrue', 'GO'),
        L('getlocal1'), L('returnvalue'),
        ('GO', 'pushnull'), L('setlocal', 5),
        L('pushbyte', 0), L('setlocal3'),
        ('B0', 'label'), L('getlocal3'), L('getlocal1'), L('getproperty', length), L('ifnlt', 'B9'),
        L('getlocal1'), L('getlocal3'), L('getproperty', late), L('coerce_a'), L('setlocal', 4),
        L('getlocal', 4), L('iffalse', 'B1'),
        *isBack(4, 'B1', 'ifne'),
        L('getlocal', 4), L('setlocal', 5),
        ('B1', 'inclocal_i', 3), L('jump', 'B0'),
        ('B9', 'getlocal0'), L('getproperty', fmlRefr), L('iftrue', 'RF'),
        L('getlocal1'), L('getlocal0'), L('getproperty', fmlLastDP), L('ifstricteq', 'BK'),
        # a fresh list: keep its entries, clear the search, tell the script the ids
        L('getlocal0'), L('pushnull'), L('initproperty', fmlBackId),
        L('getlocal0'), L('newarray', 0), L('initproperty', fmlAll),
        L('getlocal0'), L('pushstring', s_empty), L('initproperty', fmlSearch),
        L('pushstring', s_empty), L('setlocal', 6),
        L('pushbyte', 0), L('setlocal3'),
        ('A0', 'label'), L('getlocal3'), L('getlocal1'), L('getproperty', length), L('ifnlt', 'A9'),
        L('getlocal1'), L('getlocal3'), L('getproperty', late), L('coerce_a'), L('setlocal', 4),
        L('getlocal', 4), L('iffalse', 'A1'),
        *isBack(4, 'A1', 'ifeq'),
        # never a letter header (a list of ours that came back without being fmlLastDP)
        L('getlocal', 4), L('getproperty', fmlHdrP), L('iftrue', 'A1'),
        L('getlocal0'), L('getproperty', fmlAll), L('getlocal', 4), L('callpropvoid', pushM, 1),
        L('getlocal', 6), L('getlocal', 4), L('getproperty', idP), L('convert_s'), L('add'), L('pushstring', s_semi),
        L('add'), L('coerce_a'), L('setlocal', 6),
        ('A1', 'inclocal_i', 3), L('jump', 'A0'),
        ('A9', 'getlocal0'), L('getlocal', 6), L('initproperty', fmlPSeen),
        ('RF', 'label'), L('getlocal0'), L('pushfalse'), L('initproperty', fmlRefr),
        # headers toggled: the entry that was selected stays selected (fmlKeepId, set by fmlHdrToggle)
        L('getlocal', 9), L('iftrue', 'KQ'),
        L('getlocal0'), L('getproperty', fmlKeepId), L('coerce_a'), L('setlocal', 9),
        ('KQ', 'getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('coerce_a'), L('setlocal', 8),
        L('newarray', 0), L('setlocal2'),
        L('pushbyte', 0), L('setlocal3'),
        ('F0', 'label'), L('getlocal3'), L('getlocal0'), L('getproperty', fmlAll), L('getproperty', length), L('ifnlt', 'F9'),
        L('getlocal0'), L('getproperty', fmlAll), L('getlocal3'), L('getproperty', late), L('coerce_a'),
        L('setlocal', 4),
        L('getlocal', 8), L('pushstring', s_empty), L('ifeq', 'KEEP'),
        L('getlocal', 4), L('getproperty', lab), L('convert_s'), L('callproperty', lowerM, 0), L('getlocal', 8),
        L('callproperty', idxM, 1), L('pushbyte', 0), L('iflt', 'F1'),
        # insertion sort: before the first entry this one sorts ahead of
        ('KEEP', 'pushbyte', 0), L('setlocal', 7),
        ('S0', 'label'), L('getlocal', 7), L('getlocal2'), L('getproperty', length), L('ifnlt', 'S9'),
        L('getlocal0'), L('getlocal', 4), L('getlocal2'), L('getlocal', 7), L('getproperty', late),
        L('callproperty', m_less, 2), L('iftrue', 'S9'),
        L('inclocal_i', 7), L('jump', 'S0'),
        ('S9', 'getlocal2'), L('getlocal', 7), L('pushbyte', 0), L('getlocal', 4), L('callpropvoid', spliceM, 3),
        ('F1', 'inclocal_i', 3), L('jump', 'F0'),
        # A to Z / By category with headers: a header row before each group (after the filter, so a search keeps
        # only the letters / categories that still have entries; Back is added after this and gets none)
        ('F9', 'getlocal0'), L('getlocal2'), L('callproperty', m_hdrs, 1), L('coerce_a'), L('dup'),
        L('iffalse', 'HZ'),
        L('setlocal2'), L('jump', 'HY'),
        ('HZ', 'pop'),
        # no header in a column's last row, no mod on a later column's top: spacer rows (fmlGaps; Back, added below,
        # counts as a row)
        ('HY', 'getlocal0'), L('getlocal2'), L('getlocal', 5), L('convert_b'), L('convert_i'),
        L('callpropvoid', m_gaps, 2),
        # back from an entry's page (or headers toggled): select that entry where it is now, in the final rows
        L('getlocal', 9), L('iffalse', 'F95'),
        L('pushbyte', 0), L('setlocal3'),
        ('G0', 'label'), L('getlocal3'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'F95'),
        L('getlocal2'), L('getlocal3'), L('getproperty', late), L('getproperty', fmlHdrP), L('iftrue', 'G1'),
        L('getlocal2'), L('getlocal3'), L('getproperty', late), L('getproperty', idP), L('convert_s'),
        L('getlocal', 9), L('ifne', 'G1'),
        L('getlocal0'), L('getlocal3'), L('initproperty', fmlSelOut), L('jump', 'F95'),
        ('G1', 'inclocal_i', 3), L('jump', 'G0'),
        ('F95', 'getlocal', 5), L('iffalse', 'RET'),
        L('getlocal2'), L('getlocal', 5), L('callpropvoid', pushM, 1),
        # the id to select is Back's (Back was selected when fmlRegapNow showed the list again): Back, the last row
        L('getlocal', 9), L('iffalse', 'RET'),
        L('getlocal0'), L('getproperty', fmlSelOut), L('pushbyte', 0), L('ifge', 'RET'),
        L('getlocal', 5), L('getproperty', idP), L('convert_s'), L('getlocal', 9), L('ifne', 'RET'),
        L('getlocal0'), L('getlocal2'), L('getproperty', length), L('decrement_i'), L('initproperty', fmlSelOut),
        # the list's dataProvider setter takes an IDataProvider: a plain Array there is a TypeError
        ('RET', 'findpropstrict', dpC), L('getlocal2'), L('constructprop', dpC, 1), L('coerce_a'), L('setlocal2'),
        L('getlocal0'), L('getlocal2'), L('initproperty', fmlLastDP),
        L('getlocal2'), L('returnvalue'),
        # the same list again (Back from an entry's page): under Recently opened, sorted again with the entry just
        # opened on top, and no hovered row taking the selection
        ('BK', 'getlocal0'), L('getproperty', fmlBackId), L('iffalse', 'SAME'),
        L('getlocal0'), L('getproperty', fmlNoRs), L('iftrue', 'BK0'),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', 2), L('ifne', 'BK0'),
        L('getlocal0'), L('getproperty', fmlBackId), L('convert_s'), L('coerce_a'), L('setlocal', 9),
        L('getlocal0'), L('pushbyte', 255), L('setproperty', lastMO),
        ('BK0', 'getlocal0'), L('pushnull'), L('initproperty', fmlBackId),
        L('getlocal', 9), L('iftrue', 'RF'),
        ('SAME', 'getlocal1'), L('returnvalue'),
    ]

    # fmlLess(a, b):Boolean - a sorts ahead of b.   3 x, 4 y, 5 sort, 6 stamp map
    less = [
        L('getlocal1'), L('getproperty', fmlFavP), L('convert_b'), L('getlocal2'), L('getproperty', fmlFavP),
        L('convert_b'), L('ifeq', 'FQ'),
        L('getlocal1'), L('getproperty', fmlFavP), L('convert_b'), L('returnvalue'),
        ('FQ', 'getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('setlocal', 5),
        L('getlocal', 5), L('pushbyte', 1), L('iflt', 'NAME'),
        # 3 = by category: category order (fmlKindOf), A to Z inside a category
        L('getlocal', 5), L('pushbyte', CAT_SORT), L('ifne', 'STAMP'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_kind, 1), L('convert_i'), L('setlocal3'),
        L('getlocal0'), L('getlocal2'), L('callproperty', m_kind, 1), L('convert_i'), L('setlocal', 4),
        L('getlocal3'), L('getlocal', 4), L('ifeq', 'NAME'),
        L('getlocal3'), L('getlocal', 4), L('lessthan'), L('returnvalue'),
        # 1 = newest first (first seen), 2 = recently opened
        ('STAMP', 'getlocal0'), L('getproperty', fmlSeen), L('getlocal', 5), L('pushbyte', 1), L('ifeq', 'MAP'),
        L('pop'), L('getlocal0'), L('getproperty', fmlOpen),
        ('MAP', 'coerce_a'), L('setlocal', 6),
        L('getlocal', 6), L('iffalse', 'NAME'),
        L('getlocal', 6), L('getlocal1'), L('getproperty', idP), L('convert_s'), L('getproperty', late),
        L('convert_d'), L('setlocal3'),
        L('getlocal3'), L('getlocal3'), L('ifeq', 'X1'),
        L('pushbyte', 0), L('convert_d'), L('setlocal3'),
        ('X1', 'getlocal', 6), L('getlocal2'), L('getproperty', idP), L('convert_s'), L('getproperty', late),
        L('convert_d'), L('setlocal', 4),
        L('getlocal', 4), L('getlocal', 4), L('ifeq', 'X2'),
        L('pushbyte', 0), L('convert_d'), L('setlocal', 4),
        ('X2', 'getlocal3'), L('getlocal', 4), L('ifeq', 'NAME'),
        L('getlocal3'), L('getlocal', 4), L('greaterthan'), L('returnvalue'),
        ('NAME', 'getlocal1'), L('getproperty', lab), L('convert_s'), L('callproperty', lowerM, 0), L('coerce_a'),
        L('setlocal3'),
        L('getlocal2'), L('getproperty', lab), L('convert_s'), L('callproperty', lowerM, 0), L('coerce_a'),
        L('setlocal', 4),
        L('getlocal3'), L('getlocal', 4), L('lessthan'), L('returnvalue'),
    ]

    # fmlRefresh(): show fmlAll again with the current search and sort (Mods list with the focus only)
    refresh = [
        L('getlocal0'), L('pushnull'), L('initproperty', fmlBackId),
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', fmlAll), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'END'),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlRefr),
        L('getlocal0'), L('pushbyte', 255), L('setproperty', lastMO),
        L('getlocal0'), L('findpropstrict', dpC), L('getlocal0'), L('getproperty', fmlAll), L('constructprop', dpC, 1),
        L('pushbyte', 0), L('callpropvoid', like, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlRefr),
        ('END', 'returnvoid'),
    ]

    # fmlTell(kind, value): GameEvent CALL "OnFmlEvent" [kind, value] from the menu   3 menu
    tell = [
        L('getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('getlocal3'),
        L('findpropstrict', geFind), L('getlex', geLex), L('getproperty', geCall), L('pushstring', s_onfml),
        L('getlocal1'), L('getlocal2'), L('newarray', 2), L('constructprop', geNew, 3),
        L('callpropvoid', dispM, 1),
        ('END', 'returnvoid'),
    ]

    # fmlParse(s): "1|next|sort|id:seen:opened;..."   2 parts, 3 items, 4 i, 5 fields, 6 seen, 7 opened,
    #              8 fmlHdrOff before
    # stored sort code: 0..2 = sort with headers on (the default), + OLD_SORTS when they are off; By category is
    # CAT_CODE (6) with headers on, CAT_CODE + 1 (7) off
    parse = [
        L('getlocal1'), L('convert_s'), L('pushstring', s_bar), L('callproperty', splitM, 1), L('coerce_a'),
        L('setlocal2'),
        L('getlocal2'), L('getproperty', length), L('pushbyte', 4), L('iflt', 'END'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('convert_b'), L('setlocal', 8),
        L('getlocal2'), L('pushbyte', 2), L('getproperty', late), L('convert_i'), L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', CAT_CODE), L('iflt', 'OLD'),
        L('getlocal0'), L('pushbyte', CAT_SORT), L('initproperty', fmlSort),
        L('getlocal0'), L('getlocal', 4), L('pushbyte', CAT_CODE + 1), L('greaterequals'), L('initproperty', fmlHdrOff),
        L('jump', 'DEC'),
        ('OLD', 'getlocal0'), L('getlocal', 4), L('pushbyte', OLD_SORTS), L('modulo'), L('convert_i'),
        L('initproperty', fmlSort),
        L('getlocal0'), L('getlocal', 4), L('pushbyte', OLD_SORTS), L('greaterequals'), L('initproperty', fmlHdrOff),
        ('DEC', 'getlocal0'), L('getlocal2'), L('pushbyte', 1), L('getproperty', late), L('convert_d'),
        L('initproperty', fmlOpenTop),
        L('newobject', 0), L('setlocal', 6), L('newobject', 0), L('setlocal', 7),
        L('getlocal2'), L('pushbyte', 3), L('getproperty', late), L('convert_s'), L('pushstring', s_semi),
        L('callproperty', splitM, 1), L('coerce_a'), L('setlocal3'),
        L('pushbyte', 0), L('setlocal', 4),
        ('L0', 'label'), L('getlocal', 4), L('getlocal3'), L('getproperty', length), L('ifnlt', 'L9'),
        L('getlocal3'), L('getlocal', 4), L('getproperty', late), L('convert_s'), L('pushstring', s_colon),
        L('callproperty', splitM, 1), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('getproperty', length), L('pushbyte', 3), L('iflt', 'L1'),
        L('getlocal', 6), L('getlocal', 5), L('pushbyte', 0), L('getproperty', late), L('convert_s'),
        L('getlocal', 5), L('pushbyte', 1), L('getproperty', late), L('convert_d'), L('setproperty', late),
        L('getlocal', 7), L('getlocal', 5), L('pushbyte', 0), L('getproperty', late), L('convert_s'),
        L('getlocal', 5), L('pushbyte', 2), L('getproperty', late), L('convert_d'), L('setproperty', late),
        ('L1', 'inclocal_i', 4), L('jump', 'L0'),
        ('L9', 'getlocal0'), L('getlocal', 6), L('initproperty', fmlSeen),
        L('getlocal0'), L('getlocal', 7), L('initproperty', fmlOpen),
        # part 5 (sent, not stored): the sort names, the Sort prompt and (newer scripts) the Headers prompt, the
        # Category prompt and the category names in the game's language, ";"-separated
        L('getlocal2'), L('getproperty', length), L('pushbyte', 6), L('iflt', 'NN'),
        L('getlocal2'), L('pushbyte', 5), L('getproperty', late), L('convert_s'), L('pushstring', s_semi),
        L('callproperty', splitM, 1), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('getproperty', length), L('pushbyte', NUM_SORTS + 1), L('iflt', 'NN'),
        # first names: a Sort prompt already shown is put up again with the translated label
        L('getlocal0'), L('getproperty', fmlNames), L('iftrue', 'NS'),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlPrompt),
        ('NS', 'getlocal0'), L('getlocal3'), L('initproperty', fmlNames),
        # the list was shown before the store arrived (A to Z, headers on): show it again if that differs
        ('NN', 'getlocal0'), L('getproperty', fmlSort), L('pushbyte', 1), L('ifge', 'RFR'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('getlocal', 8), L('ifeq', 'END'),
        ('RFR', 'getlocal0'), L('callpropvoid', m_refresh, 0),
        ('END', 'returnvoid'),
    ]

    # fmlKey(e) - Mods list with the focus: R3 / Tab cycles the sort; RT / Space turns the headers on or off
    # (A to Z and By category only; the game's dialogs take Space before this runs); X / Insert moves the selected
    # mod to the next category (By category only); Y / Home resets the categories (By category only, twice);
    # letters and digits type a search (E only once
    # one is typed: before that E opens the entry), Backspace deletes the last one, Delete clears it, Enter opens the
    # entry while a search is typed. 0 = not ours, 1 = handled, 2 = open the entry.   2 details, 3 code, 5 value
    up = lambda miss: [L('getlocal1'), L('pushtrue'), L('setproperty', handled),
                       L('getlocal', 5), L('pushstring', s_up), L('ifne', miss)]
    # the sort code sent to the script (leaves a String): fmlSort, + OLD_SORTS while the headers are off; By category
    # CAT_CODE, + 1 while they are off
    sort_code = lambda lab: [L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT),
                             L('ifne', lab + 'o'),
                             L('pushbyte', CAT_CODE),
                             L('getlocal0'), L('getproperty', fmlHdrOff), L('iffalse', lab),
                             L('increment_i'), L('jump', lab),
                             (lab + 'o', 'getlocal0'), L('getproperty', fmlSort), L('convert_i'),
                             L('getlocal0'), L('getproperty', fmlHdrOff), L('iffalse', lab),
                             L('pushbyte', OLD_SORTS), L('add_i'),
                             (lab, 'convert_s')]
    key = [
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'NO'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'NO'),
        L('getlocal1'), L('getproperty', details), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'NO'),
        L('getlocal2'), L('getproperty', codeP), L('convert_i'), L('setlocal3'),
        L('getlocal2'), L('getproperty', valueP), L('coerce_a'), L('setlocal', 5),
        # RT / Space: headers on or off, A to Z and By category only (other sorts: not ours, as before)
        L('getlocal3'), L('pushshort', PAD_RT), L('ifeq', 'HDR'),
        L('getlocal3'), L('pushbyte', KEY_SPACE), L('ifne', 'CK'),
        *hdr_gate('NO', 'HG', 'HDR'),
        *up('YES'),
        L('getlocal0'), L('callpropvoid', m_htog, 0),
        L('jump', 'YES'),
        # X / Insert: the selected mod to the next category, By category only (other sorts: not ours)
        ('CK', 'getlocal3'), L('pushshort', PAD_X), L('ifeq', 'CAT'),
        L('getlocal3'), L('pushbyte', KEY_INSERT), L('ifne', 'RK'),
        ('CAT', 'getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT), L('ifne', 'NO'),
        *up('YES'),
        L('getlocal0'), L('callpropvoid', m_cnext, 0),
        L('jump', 'YES'),
        # Y / Home: reset the categories (arm, then reset), By category only (other sorts: not ours)
        ('RK', 'getlocal3'), L('pushshort', PAD_Y), L('ifeq', 'RST'),
        L('getlocal3'), L('pushbyte', KEY_HOME), L('ifne', 'FV'),
        ('RST', 'getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT), L('ifne', 'NO'),
        *up('YES'),
        L('getlocal0'), L('callpropvoid', m_crst, 0),
        L('jump', 'YES'),
        # LB / Page Up favorite (every sort)
        ('FV', 'getlocal3'), L('pushshort', PAD_LB), L('ifeq', 'FAV'),
        L('getlocal3'), L('pushbyte', KEY_PGUP), L('ifne', 'S0'),
        ('FAV', 'label'), *up('YES'),
        L('getlocal0'), L('callpropvoid', m_flag, 0),
        L('jump', 'YES'),
        ('S0', 'getlocal3'), L('pushshort', 147), L('ifeq', 'SORT'),
        L('getlocal3'), L('pushbyte', 9), L('ifne', 'TXT'),
        ('SORT', 'label'), *up('YES'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlSort), L('increment_i'), L('pushbyte', NUM_SORTS), L('modulo'),
        L('convert_i'), L('initproperty', fmlSort),
        L('getlocal0'), *sort_code('SC'), L('initproperty', fmlPSort),
        L('jump', 'RF'),
        ('TXT', 'getlocal3'), L('pushbyte', 13), L('ifne', 'LTR'),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('pushstring', s_empty), L('ifeq', 'NO'),
        *up('YES'),
        L('pushbyte', 2), L('returnvalue'),
        ('LTR', 'getlocal3'), L('pushbyte', 65), L('iflt', 'DIG'),
        L('getlocal3'), L('pushbyte', 90), L('ifgt', 'NUM'),
        L('getlocal3'), L('pushbyte', 69), L('ifne', 'LET'),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('pushstring', s_empty), L('ifeq', 'NO'),
        ('LET', 'getlocal3'), L('pushbyte', 65), L('subtract'), L('convert_i'), L('setlocal3'),
        L('jump', 'ADD'),
        ('DIG', 'getlocal3'), L('pushbyte', 48), L('iflt', 'BS'),
        L('getlocal3'), L('pushbyte', 57), L('ifgt', 'BS'),
        L('getlocal3'), L('pushbyte', 22), L('subtract'), L('convert_i'), L('setlocal3'),
        L('jump', 'ADD'),
        ('NUM', 'getlocal3'), L('pushbyte', 96), L('iflt', 'BS'),
        L('getlocal3'), L('pushbyte', 105), L('ifgt', 'BS'),
        L('getlocal3'), L('pushbyte', 70), L('subtract'), L('convert_i'), L('setlocal3'),
        ('ADD', 'label'), *up('YES'),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'),
        L('pushstring', s_chars), L('getlocal3'), L('callproperty', charAtM, 1), L('add'), L('coerce_a'),
        L('setlocal', 4),
        L('getlocal0'), L('getlocal', 4), L('callproperty', m_hits, 1), L('iffalse', 'REJ'),
        L('getlocal0'), L('getlocal', 4), L('initproperty', fmlSearch),
        L('jump', 'RF'),
        # no mod would be left: E opens the highlighted entry, anything else is refused with a sound (still handled,
        # so a top-row 3 never reaches the main menu's account button)
        ('REJ', 'getlocal3'), L('pushbyte', 4), L('ifne', 'DENY'),
        L('pushbyte', 2), L('returnvalue'),
        ('DENY', 'getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'YES'),
        L('getlocal2'), L('findpropstrict', geFind), L('getlex', geLex), L('getproperty', geCall),
        L('pushstring', s_snd), L('pushstring', s_deny), L('newarray', 1), L('constructprop', geNew, 3),
        L('callpropvoid', dispM, 1),
        L('jump', 'YES'),
        ('BS', 'getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('pushstring', s_empty), L('ifeq', 'NO'),
        L('getlocal3'), L('pushbyte', 46), L('ifeq', 'DEL'),
        L('getlocal3'), L('pushbyte', 8), L('ifne', 'NO'),
        *up('YES'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('pushbyte', 0),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('getproperty', length), L('decrement'),
        L('callproperty', substrM, 2), L('initproperty', fmlSearch),
        L('jump', 'RF'),
        ('DEL', 'label'), *up('YES'),
        L('getlocal0'), L('pushstring', s_empty), L('initproperty', fmlSearch),
        ('RF', 'getlocal0'), L('callpropvoid', m_refresh, 0),
        ('YES', 'pushtrue'), L('returnvalue'),
        ('NO', 'pushfalse'), L('returnvalue'),
    ]

    # fmlUi(): every frame - the "Sort" prompt while the Mods list has the focus (and "Headers" while it is A to Z or
    #          By category, "Change category" and "Reset categories" while it is By category),
    #          and the search text after the list title.   1 menu / input feedback, 2 title field, 3 wanted title, 4 current title
    send = lambda slot, kind, lab: [
        L('getlocal0'), L('getproperty', slot), L('iffalse', lab),
        L('getlocal0'), L('pushstring', kind), L('getlocal0'), L('getproperty', slot), L('convert_s'),
        L('getlocal0'), L('pushnull'), L('initproperty', slot),
        L('callpropvoid', m_tell, 2),
        (lab, 'nop')]
    ui = [
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlNoRs),
        # fmlLayout found the spacers placed for other columns: the list again (Mods list with the focus only; else
        # it stays pending)
        L('getlocal0'), L('getproperty', fmlRegap), L('iffalse', 'RG'),
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'RG'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'RG'),
        L('getlocal0'), L('callpropvoid', m_regap, 0),
        ('RG', 'nop'),
        # an entry was opened: stamp it in fmlOpen now (4 = the map)
        L('getlocal0'), L('getproperty', fmlPOpen), L('iffalse', 'Q0'),
        L('getlocal0'), L('getproperty', fmlOpen), L('coerce_a'), L('setlocal', 4),
        L('getlocal', 4), L('iftrue', 'Q0M'),
        L('newobject', 0), L('coerce_a'), L('setlocal', 4),
        L('getlocal0'), L('getlocal', 4), L('initproperty', fmlOpen),
        ('Q0M', 'getlocal0'), L('getlocal0'), L('getproperty', fmlOpenTop), L('increment'),
        L('initproperty', fmlOpenTop),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlPOpen), L('convert_s'),
        L('getlocal0'), L('getproperty', fmlOpenTop), L('setproperty', late),
        ('Q0', 'nop'),
        *send(fmlPSeen, s_seen, 'Q1'), *send(fmlPOpen, s_open, 'Q2'), *send(fmlPSort, s_sort, 'Q3'),
        *send(fmlPCat, s_cat, 'Q4'), *send(fmlPRst, s_crst, 'Q5'),
        *send(fmlPFav, s_fav, 'Q6'),
        L('getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal1'),
        L('getlocal1'), L('iffalse', 'TITLE'),
        L('pushstring', s_ifm), L('getlocal1'), L('in'), L('iffalse', 'TITLE'),
        L('getlocal1'), L('getproperty', ifmP), L('coerce_a'), L('setlocal1'),
        L('getlocal1'), L('iffalse', 'TITLE'),
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'POFF'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'POFF'),
        L('getlocal0'), L('getproperty', fmlPrompt), L('iftrue', 'HP'),
        L('getlocal1'), L('pushshort', SORT_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal1'), L('pushshort', SORT_ACTION), L('getlex', navC), L('getproperty', r3P), L('pushbyte', 9),
        L('pushstring', s_sortp),
        L('getlocal0'), L('getproperty', fmlNames), L('iffalse', 'SP'),
        L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', NUM_SORTS), L('getproperty', late),
        L('convert_s'),
        ('SP', 'pushtrue'), L('callpropvoid', appendB, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlPrompt),
        # the Headers, Change category and Reset categories prompts go back up after it, so they stay right of Sort
        # (in that order)
        L('getlocal1'), L('pushshort', HDR_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlHPrompt),
        L('getlocal1'), L('pushshort', CAT_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlCPrompt),
        L('getlocal1'), L('pushshort', RST_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlRPrompt),
        # "RT / Space Headers" next to it while the sort is A to Z or By category
        *hdr_gate('HOFF', 'HG2', 'HP'),
        L('getlocal0'), L('getproperty', fmlHPrompt), L('iftrue', 'CP'),
        L('getlocal1'), L('pushshort', HDR_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal1'), L('pushshort', HDR_ACTION), L('pushstring', s_r2), L('pushbyte', KEY_SPACE),
        L('pushstring', s_hdrname),
        L('getlocal0'), L('getproperty', fmlNames), L('iffalse', 'HN'),
        L('getlocal0'), L('getproperty', fmlNames), L('getproperty', length), L('pushbyte', NUM_SORTS + 2),
        L('iflt', 'HN'),
        L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', NUM_SORTS + 1), L('getproperty', late),
        L('convert_s'),
        ('HN', 'pushtrue'), L('callpropvoid', appendB, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlHPrompt),
        L('jump', 'CP'),
        ('POFF', 'getlocal0'), L('getproperty', fmlPrompt), L('iffalse', 'HOFF'),
        L('getlocal1'), L('pushshort', SORT_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlPrompt),
        ('HOFF', 'getlocal0'), L('getproperty', fmlHPrompt), L('iffalse', 'CP'),
        L('getlocal1'), L('pushshort', HDR_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlHPrompt),
        # "X / Insert Change category" right of them while the sort is By category (local 1 is the input feedback
        # module on every way here)
        ('CP', 'getlocal0'), L('getproperty', fmlMods), L('iffalse', 'COFF'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'COFF'),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT), L('ifne', 'COFF'),
        L('getlocal0'), L('getproperty', fmlCPrompt), L('iftrue', 'RP'),
        L('getlocal1'), L('pushshort', CAT_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal1'), L('pushshort', CAT_ACTION), L('pushstring', s_x), L('pushbyte', KEY_INSERT),
        L('pushstring', s_catp),
        L('getlocal0'), L('getproperty', fmlNames), L('iffalse', 'CN'),
        L('getlocal0'), L('getproperty', fmlNames), L('getproperty', length), L('pushbyte', NUM_SORTS + 3),
        L('iflt', 'CN'),
        L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', NUM_SORTS + 2), L('getproperty', late),
        L('convert_s'),
        ('CN', 'pushtrue'), L('callpropvoid', appendB, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlCPrompt),
        # "Y / Home Reset categories" after it; armed (fmlCatReset): the script's armed label ("Press again to reset";
        # a script without one: that in English, a translated label + "?")
        # until RESET_MS have passed. Put up again whenever the armed state differs from the label shown
        ('RP', 'getlocal0'), L('getproperty', fmlRArmT), L('pushbyte', 0), L('ifngt', 'RA'),
        L('findpropstrict', getTimer), L('callproperty', getTimer, 0), L('getlocal0'), L('getproperty', fmlRArmT),
        L('subtract'), L('pushshort', RESET_MS), L('ifngt', 'RA'),
        L('getlocal0'), L('pushbyte', 0), L('initproperty', fmlRArmT),
        ('RA', 'getlocal0'), L('getproperty', fmlRPrompt), L('iffalse', 'RS'),
        L('getlocal0'), L('getproperty', fmlRShown),
        L('getlocal0'), L('getproperty', fmlRArmT), L('pushbyte', 0), L('greaterthan'), L('ifeq', 'TITLE'),
        ('RS', 'getlocal1'), L('pushshort', RST_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal1'), L('pushshort', RST_ACTION), L('pushstring', s_y), L('pushbyte', KEY_HOME),
        L('pushstring', s_rstp),
        L('getlocal0'), L('getproperty', fmlNames), L('iffalse', 'RN'),
        L('getlocal0'), L('getproperty', fmlNames), L('getproperty', length), L('pushbyte', RST_IDX + 1),
        L('iflt', 'RN'),
        L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', RST_IDX), L('getproperty', late),
        L('convert_s'),
        ('RN', 'getlocal0'), L('getproperty', fmlRArmT), L('pushbyte', 0), L('ifngt', 'RL'),
        L('getlocal0'), L('getproperty', fmlNames), L('iffalse', 'RE'),
        L('getlocal0'), L('getproperty', fmlNames), L('getproperty', length), L('pushbyte', RST_AIDX + 1),
        L('iflt', 'RE'),
        L('pop'), L('getlocal0'), L('getproperty', fmlNames), L('pushbyte', RST_AIDX), L('getproperty', late),
        L('convert_s'), L('jump', 'RL'),
        ('RE', 'dup'), L('pushstring', s_rstp), L('ifne', 'RQ'),
        L('pop'), L('pushstring', s_rsta), L('jump', 'RL'),
        ('RQ', 'pushstring', s_q), L('add'),
        ('RL', 'pushtrue'), L('callpropvoid', appendB, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlRPrompt),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlRArmT), L('pushbyte', 0), L('greaterthan'),
        L('initproperty', fmlRShown),
        L('jump', 'TITLE'),
        # not By category, a page open or not the Mods list: both prompts down, a first Y / Home forgotten
        ('COFF', 'getlocal0'), L('getproperty', fmlCPrompt), L('iffalse', 'ROFF'),
        L('getlocal1'), L('pushshort', CAT_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlCPrompt),
        ('ROFF', 'getlocal0'), L('pushbyte', 0), L('initproperty', fmlRArmT),
        L('getlocal0'), L('getproperty', fmlRPrompt), L('iffalse', 'TITLE'),
        L('getlocal1'), L('pushshort', RST_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlRPrompt),
        ('TITLE', 'getlocal0'), L('callpropvoid', m_fpr, 0),
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', fmlTBase), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', ttl), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        # line 2: sort name [+ "  -  " + the search, its last SEARCH_SHOWN characters]
        *names('NM0'),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('getproperty', late), L('convert_s'),
        L('coerce_a'), L('setlocal3'),
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('pushstring', s_empty), L('ifeq', 'HT'),
        L('getlocal', 5), L('getproperty', length), L('pushbyte', SEARCH_SHOWN), L('ifngt', 'SH'),
        L('pushstring', s_dots), L('getlocal', 5), L('getlocal', 5), L('getproperty', length),
        L('pushbyte', SEARCH_SHOWN), L('subtract'), L('callproperty', substrM, 1), L('add'), L('coerce_a'),
        L('setlocal', 5),
        ('SH', 'getlocal3'), L('pushstring', s_dash), L('add'), L('getlocal', 5), L('add'), L('coerce_a'),
        L('setlocal3'),
        # <p align='center'>BASE</p><p align='center'><font size='20'>LINE 2</font></p>
        ('HT', 'pushstring', s_p1), L('getlocal0'), L('getproperty', fmlTBase), L('convert_s'), L('add'),
        L('pushstring', s_p2), L('add'), L('getlocal3'), L('add'), L('pushstring', s_p3), L('add'),
        L('coerce_a'), L('setlocal3'),
        # same title as last time and nobody wrote the field since: nothing to do
        L('getlocal3'), L('getlocal0'), L('getproperty', fmlTHtml), L('ifne', 'SET'),
        L('getlocal2'), L('getproperty', textP), L('getlocal0'), L('getproperty', fmlTSet), L('ifeq', 'END'),
        ('SET', 'getlocal0'), L('getlocal3'), L('initproperty', fmlTHtml),
        L('getlocal0'),
        L('pushstring', s_p1), L('getlocal0'), L('getproperty', fmlTBase), L('convert_s'), L('add'),
        L('pushstring', s_p2), L('add'),
        *names('NM1'),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('getproperty', late), L('add'),
        L('pushstring', s_p3), L('add'),
        L('setproperty', titleP),
        L('getlocal2'), L('getproperty', numLinesP), L('convert_i'), L('setlocal', 6),
        L('getlocal0'), L('getlocal3'), L('setproperty', titleP),
        # line 2 wrapped (wide fonts: Korean, Arabic, Chinese): one search character less until it fits.
        # 4 characters shown, 5 search
        L('getlocal0'), L('getproperty', fmlSearch), L('convert_s'), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('getproperty', length), L('convert_i'), L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', SEARCH_SHOWN), L('ifngt', 'FIT'),
        L('pushbyte', SEARCH_SHOWN), L('setlocal', 4),
        ('FIT', 'label'),
        L('getlocal2'), L('getproperty', numLinesP), L('getlocal', 6), L('ifngt', 'DONE'),
        L('getlocal', 4), L('pushbyte', 1), L('ifngt', 'DONE'),
        L('declocal_i', 4),
        L('getlocal0'),
        L('pushstring', s_p1), L('getlocal0'), L('getproperty', fmlTBase), L('convert_s'), L('add'),
        L('pushstring', s_p2), L('add'),
        *names('NM2'),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('getproperty', late), L('add'),
        L('pushstring', s_dash), L('add'), L('pushstring', s_dots), L('add'),
        L('getlocal', 5), L('getlocal', 5), L('getproperty', length), L('getlocal', 4), L('subtract'),
        L('callproperty', substrM, 1), L('add'),
        L('pushstring', s_p3), L('add'),
        L('setproperty', titleP),
        L('jump', 'FIT'),
        ('DONE', 'getlocal0'), L('getlocal2'), L('getproperty', textP), L('initproperty', fmlTSet),
        ('END', 'returnvoid'),
    ]

    # fmlHits(s):Boolean - some entry of fmlAll matches the search s (the same test as fmlView)   2 i, 3 item
    hits = [
        L('getlocal0'), L('getproperty', fmlAll), L('iffalse', 'NO'),
        L('pushbyte', 0), L('setlocal2'),
        ('HL', 'label'),
        L('getlocal2'), L('getlocal0'), L('getproperty', fmlAll), L('getproperty', length), L('ifnlt', 'NO'),
        L('getlocal0'), L('getproperty', fmlAll), L('getlocal2'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'HN'),
        L('getlocal3'), L('getproperty', lab), L('convert_s'), L('callproperty', lowerM, 0), L('getlocal1'),
        L('convert_s'), L('callproperty', idxM, 1), L('pushbyte', 0), L('ifge', 'YES'),
        ('HN', 'inclocal_i', 2), L('jump', 'HL'),
        ('YES', 'pushtrue'), L('returnvalue'),
        ('NO', 'pushfalse'), L('returnvalue'),
    ]

    # ---- header rows (Options > Mods: letters in A to Z, category names in By category) ---------------------------
    # A header is a row fmlView adds (never in fmlAll): {id: "", label: NBSP + letter, type: HDR_TYPE,
    # unavailable: true, fmlHdr: letter}. unavailable makes activateMenuListItem return before hook 7 and any
    # script call (E, Enter, A, click); the label is unique so a recycled renderer redraws it, but never shown.
    s_hash, s_nbsp, s_unav = string('#'), string(' '), string('unavailable')
    s_space = string(' ')
    s_idk, s_labk, s_typek = string('id'), string('label'), string('type')

    # fmlIsHdr(i):Boolean - row i of the list is a letter header   2 dp, 3 row data
    ishdr = [
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'NO'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'NO'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'NO'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'NO'),
        # "in" first: a sealed row object would throw on an unknown property
        L('pushstring', s_fmlhdr), L('getlocal3'), L('in'), L('iffalse', 'NO'),
        L('getlocal3'), L('getproperty', fmlHdrP), L('iffalse', 'NO'),
        L('pushtrue'), L('returnvalue'),
        ('NO', 'pushfalse'), L('returnvalue'),
    ]

    # fmlHdrSkip(v, list):int - from W3ScrollingList.selectedIndex set (hook 10), before it does anything: every way
    # of selecting (default / restored index, refresh, column jumps, right stick, mouse, onLastMoveStatusChanged's 0)
    # passes there. Returns how far to move v: a header -> the next row (the group's first entry; up when there is
    # none below), anything else 0. A delta, so the catch-all's undefined (int 0) leaves v alone.
    #   3 n, 4 i
    hskip = [
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'ZERO'),
        L('getlocal2'), L('getlocal0'), L('getproperty', mcList), L('ifstrictne', 'ZERO'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iffalse', 'ZERO'),
        *lst, L('getproperty', dprov), L('getproperty', length), L('convert_i'), L('setlocal3'),
        L('getlocal1'), L('convert_i'), L('increment_i'), L('setlocal', 4),
        ('DN', 'label'),
        L('getlocal', 4), L('getlocal3'), L('ifnlt', 'UP0'),
        L('getlocal0'), L('getlocal', 4), L('callproperty', m_ishdr, 1), L('iffalse', 'GOT'),
        L('inclocal_i', 4), L('jump', 'DN'),
        ('UP0', 'getlocal1'), L('convert_i'), L('decrement_i'), L('setlocal', 4),
        ('UP', 'label'),
        L('getlocal', 4), L('pushbyte', 0), L('iflt', 'NONE'),
        L('getlocal0'), L('getlocal', 4), L('callproperty', m_ishdr, 1), L('iffalse', 'GOT'),
        L('declocal_i', 4), L('jump', 'UP'),
        ('NONE', 'pushbyte', 255), L('setlocal', 4),
        ('GOT', 'getlocal', 4), L('getlocal1'), L('convert_i'), L('subtract'), L('convert_i'), L('returnvalue'),
        ('ZERO', 'pushbyte', 0), L('returnvalue'),
    ]

    # fmlHdrs(out):Array - A to Z or By category with headers on: out with a header before each group of entries
    # whose key differs from the entry before. A to Z key = first character of the label in lower case (what fmlLess
    # sorts by), shown upper case; characters without case (digits, symbols, caseless scripts) share "#". By category
    # key = the category name (fmlCatName); a Menu Organizer category (-1, sorted first) has "" and gets no header.
    # Other sorts / off: out itself.
    #   2 rows, 3 i, 4 entry, 5 last key, 6 key, 7 first character
    hdrs = [
        *hdr_gate('NO', 'HG'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('iftrue', 'NO'),
        L('newarray', 0), L('setlocal2'),
        L('pushstring', s_empty), L('coerce_a'), L('setlocal', 5),
        L('pushbyte', 0), L('setlocal3'),
        ('L0', 'label'),
        L('getlocal3'), L('getlocal1'), L('getproperty', length), L('ifnlt', 'L9'),
        L('getlocal1'), L('getlocal3'), L('getproperty', late), L('coerce_a'), L('setlocal', 4),
        L('getlocal0'), L('getproperty', fmlSort), L('convert_i'), L('pushbyte', CAT_SORT), L('ifne', 'LTR'),
        L('getlocal0'), L('getlocal0'), L('getlocal', 4), L('callproperty', m_kind, 1), L('callproperty', m_cname, 1),
        L('convert_s'), L('coerce_a'), L('setlocal', 6),
        L('jump', 'LT'),
        ('LTR', 'getlocal', 4), L('getproperty', lab), L('convert_s'), L('callproperty', lowerM, 0), L('convert_s'),
        L('pushbyte', 0), L('callproperty', charAtM, 1), L('convert_s'), L('coerce_a'), L('setlocal', 7),
        L('getlocal', 7), L('convert_s'), L('callproperty', upperM, 0), L('convert_s'), L('coerce_a'),
        L('setlocal', 6),
        L('getlocal', 6), L('getlocal', 7), L('ifne', 'LT'),
        L('pushstring', s_hash), L('coerce_a'), L('setlocal', 6),
        ('LT', 'getlocal', 4), L('getproperty', fmlFavP), L('convert_b'), L('iffalse', 'LU'),
        *nlabel(FAVS_IDX, s_favs, 'LV'), L('coerce_a'), L('setlocal', 6),
        ('LU', 'getlocal', 6), L('getlocal', 5), L('ifeq', 'L1'),
        L('getlocal', 6), L('setlocal', 5),
        L('getlocal', 6), L('pushstring', s_empty), L('ifeq', 'L1'),
        L('getlocal2'),
        L('pushstring', s_idk), L('pushstring', s_empty),
        L('pushstring', s_labk), L('pushstring', s_nbsp), L('getlocal', 6), L('add'),
        L('pushstring', s_typek), L('pushbyte', HDR_TYPE),
        L('pushstring', s_unav), L('pushtrue'),
        L('pushstring', s_fmlhdr), L('getlocal', 6),
        L('newobject', 5), L('callpropvoid', pushM, 1),
        ('L1', 'getlocal2'), L('getlocal', 4), L('callpropvoid', pushM, 1),
        L('inclocal_i', 3), L('jump', 'L0'),
        ('L9', 'getlocal2'), L('returnvalue'),
        ('NO', 'getlocal1'), L('returnvalue'),
    ]

    # fmlHdrDraw(row):Boolean - from W3MenuListItemRenderer.updateText (hook 9) for every row of a list module, after
    # the vanilla label: a header row is redrawn (true: the hook then skips the selection frame sizing), any other
    # row gets back what a header changed and fmlApplyTo as before (false).
    #   2 text field, 3 graphics, 4 data, 5 mcFrame, 6 letter, 7 size / text width, 8 line y
    gcbn, dataP, enabledP = pubn('getChildByName'), pubn('data'), pubn('enabled')
    mouseEn, mouseCh, mcMark = pubn('mouseEnabled'), pubn('mouseChildren'), pubn('fmlHdrMC')
    sizeP, twP, htmlP = pubn('size'), pubn('textWidth'), pubn('htmlText')
    s_mcframe, s_mcmark = string('mcFrame'), string('fmlHdrMC')
    s_f1, s_f2, s_f3 = string('<font color="#%06X" size="' % HDR_GOLD), string('">'), string('</font>')
    i_gold, d_hline = c.integer(HDR_GOLD), c.double(HDR_LINE_A)
    hdraw = [
        # first, before any return: a recycled row loses the line it had as a header (fmlHdrMC marks such rows; no
        # other renderer's graphics are touched)
        L('getlocal1'), L('getproperty', gfx), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'G1'),
        L('pushstring', s_mcmark), L('getlocal1'), L('in'), L('iffalse', 'G1'),
        L('getlocal3'), L('callpropvoid', g_clear, 0),
        # mcFrame only exists on the selected_* frames, each time a new one: looked up every time
        ('G1', 'getlocal1'), L('getproperty', tf), L('coerce_a'), L('setlocal2'),
        L('getlocal1'), L('pushstring', s_mcframe), L('callproperty', gcbn, 1), L('coerce_a'), L('setlocal', 5),
        L('pushnull'), L('coerce_a'), L('setlocal', 6),
        L('getlocal1'), L('getproperty', dataP), L('coerce_a'), L('setlocal', 4),
        L('getlocal', 4), L('iffalse', 'NORM'),
        L('pushstring', s_fmlhdr), L('getlocal', 4), L('in'), L('iffalse', 'NORM'),
        L('getlocal', 4), L('getproperty', fmlHdrP), L('coerce_a'), L('setlocal', 6),
        L('getlocal', 6), L('iffalse', 'NORM'),
        L('getlocal2'), L('iftrue', 'HDR'),
        # a normal row (this list or any other): was it a header, the mouse and the selection frame come back
        ('NORM', 'pushstring', s_mcmark), L('getlocal1'), L('in'), L('iffalse', 'N2'),
        L('getlocal1'), L('getlocal1'), L('getproperty', mcMark), L('setproperty', mouseCh),
        L('getlocal1'), L('getlocal1'), L('getproperty', enabledP), L('setproperty', mouseEn),
        L('getlocal1'), L('deleteproperty', mcMark), L('pop'),
        L('getlocal', 5), L('iffalse', 'N2'),
        L('getlocal', 5), L('pushbyte', 1), L('setproperty', alphaP),
        ('N2', 'getlocal2'), L('iffalse', 'N3'),
        L('getlocal', 4), L('iffalse', 'N3'),
        L('pushstring', s_fmlfav), L('getlocal', 4), L('in'), L('iffalse', 'N3'),
        L('getlocal', 4), L('getproperty', fmlFavP), L('convert_b'), L('iffalse', 'N3'),
        L('getlocal2'), L('pushstring', s_fgold),
        L('getlocal2'), L('getproperty', textP), L('convert_s'),
        L('pushstring', s_amp), L('callproperty', splitM, 1), L('pushstring', s_eamp), L('callproperty', joinM, 1),
        L('pushstring', s_lt), L('callproperty', splitM, 1), L('pushstring', s_elt), L('callproperty', joinM, 1),
        L('pushstring', s_gt), L('callproperty', splitM, 1), L('pushstring', s_egt), L('callproperty', joinM, 1),
        L('add'), L('pushstring', s_f3), L('add'), L('setproperty', htmlP),
        ('N3', 'getlocal0'), L('getlocal1'), L('callpropvoid', m_apply, 1),
        L('pushfalse'), L('returnvalue'),
        # header: no mouse (no hover selection, no click; its mouseChildren kept in fmlHdrMC for later)
        ('HDR', 'pushstring', s_mcmark), L('getlocal1'), L('in'), L('iftrue', 'M1'),
        L('getlocal1'), L('getlocal1'), L('getproperty', mouseCh), L('setproperty', mcMark),
        ('M1', 'getlocal1'), L('pushfalse'), L('setproperty', mouseEn),
        L('getlocal1'), L('pushfalse'), L('setproperty', mouseCh),
        # the letter in gold, HDR_GROW larger, as inline markup only: a format set on the field (setTextFormat /
        # defaultTextFormat) would stay there for the mod rows this renderer shows later
        L('getlocal2'), L('getproperty', dtfP), L('getproperty', sizeP), L('convert_d'), L('setlocal', 7),
        L('getlocal', 7), L('pushbyte', 0), L('ifgt', 'S1'),
        L('pushbyte', 24), L('convert_d'), L('setlocal', 7),
        ('S1', 'getlocal2'),
        L('pushstring', s_f1), L('getlocal', 7), L('pushbyte', HDR_GROW), L('add'), L('convert_i'), L('add'),
        L('pushstring', s_f2), L('add'), L('getlocal', 6), L('convert_s'), L('add'), L('pushstring', s_f3),
        L('add'), L('setproperty', htmlP),
        # aligned like the mod names (left, right in Arabic), then measured; no "shrink" (it would scale the larger
        # letter back down to the row's field; a later mod row gets it again from fmlApplyTo)
        L('getlocal0'), L('getlocal1'), L('callpropvoid', m_apply, 1),
        L('getlocal0'), L('getlocal2'), L('pushfalse'), L('callpropvoid', m_shrink, 2),
        # no selection frame (alpha: the hideSelection setter shows it again without a redraw)
        L('getlocal', 5), L('iffalse', 'F1'),
        L('getlocal', 5), L('pushbyte', 0), L('setproperty', alphaP),
        # the line: 1 px, from just after the letter (before it when right-aligned) to near the column's other
        # edge, through the middle of the letter
        ('F1', 'getlocal3'), L('iffalse', 'DONE'),
        L('getlocal3'), L('callpropvoid', g_clear, 0),
        # a spacer row (fmlGaps): blank, no line
        L('getlocal', 6), L('pushstring', s_space), L('ifeq', 'DONE'),
        L('getlocal2'), L('getproperty', twP), L('convert_d'), L('setlocal', 7),
        L('getlocal2'), L('getproperty', Y), L('getlocal2'), L('getproperty', th), L('pushbyte', 2), L('divide'),
        L('add'), L('pushbyte', 2), L('add'), L('convert_i'), L('setlocal', 8),
        L('getlocal3'), L('pushint', i_gold), L('pushdouble', d_hline), L('callpropvoid', g_bf, 2),
        L('getlocal3'),
        L('getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_right), L('ifne', 'LX'),
        L('getlocal2'), L('getproperty', X), L('pushbyte', 4), L('add'),
        L('jump', 'XX'),
        ('LX', 'getlocal2'), L('getproperty', X), L('getlocal', 7), L('add'), L('pushbyte', 14), L('add'),
        ('XX', 'getlocal', 8),
        L('getlocal2'), L('getproperty', Wd), L('getlocal', 7), L('subtract'), L('pushbyte', 18), L('subtract'),
        L('pushbyte', 1),
        L('callpropvoid', g_dr, 4),
        L('getlocal3'), L('callpropvoid', g_ef, 0),
        ('DONE', 'pushtrue'), L('returnvalue'),
    ]

    # fmlHdrToggle(): RT / Space in A to Z or By category - headers on <-> off, told to the script with the sort
    # (sort_code), the list shown again with the selected entry still selected (else its first entry)
    #   1 sel, 2 dp, 3 row
    htog = [
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'T'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iftrue', 'T'),
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'T'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'T'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'T'),
        L('getlocal3'), L('getproperty', idP), L('iffalse', 'T'),
        L('getlocal0'), L('getlocal3'), L('getproperty', idP), L('convert_s'), L('initproperty', fmlKeepId),
        ('T', 'getlocal0'), L('getlocal0'), L('getproperty', fmlHdrOff), L('not'), L('initproperty', fmlHdrOff),
        L('getlocal0'), *sort_code('SC'), L('initproperty', fmlPSort),
        L('getlocal0'), L('callpropvoid', m_refresh, 0),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        L('returnvoid'),
    ]

    # fmlGaps(out, extra) - A to Z / By category with headers on, the Mods list's columns known (fmlLayout ran):
    # no header in a column's last row, and every column after the first starts with a header or a spacer row (a
    # header with fmlHdr " ": never selected, drawn blank), so a group running on into the next column keeps its
    # names level with the names to their left. One pass for rows per column P, output row pos: a mod on a column
    # top gets a spacer before it; a header on a column's last row gets one before it (it then starts the next
    # column). Rows per column as fmlLayout counts them (fmlPer) for out.length + extra rows (extra 1: Back
    # follows); spacers add rows, which can change that count (screen-capped columns; counting with the new one can
    # flip back and forth). So: the smallest P from per(n) up whose spacers plus the end padding (blank rows at the
    # end until per is P, one more when Back would sit on a column top) give per exactly P; then they go in.
    #   1 out, 2 extra, 3 per, 4 i, 5 k (spacers), 6 P, 7 inserting, 8 n, 9 row / temp, 10 cols, 11 tries,
    #   12 pos / padding rows, 13 rows
    # per_of(n): fmlLayout's rows per column for n rows into 3 (fmlGapR = maxRows, fmlGapC = screen columns)
    per_of = lambda n_ops, t: [
        *n_ops, L('getlocal0'), L('getproperty', fmlGapR), L('add'), L('decrement'),
        L('getlocal0'), L('getproperty', fmlGapR), L('divide'), L('convert_i'), L('setlocal', 10),
        L('getlocal', 10), L('getlocal0'), L('getproperty', fmlGapC), L('ifngt', t + 'a'),
        L('getlocal0'), L('getproperty', fmlGapC), L('convert_i'), L('setlocal', 10),
        (t + 'a', 'getlocal', 10), L('pushbyte', 1), L('ifge', t + 'b'),
        L('pushbyte', 1), L('setlocal', 10),
        (t + 'b', 'getlocal0'), L('getproperty', fmlGapR), L('convert_i'), L('setlocal3'),
        L('getlocal3'), *n_ops, L('ifngt', t + 'c'),
        *n_ops, L('convert_i'), L('setlocal3'),
        (t + 'c', 'nop'), *n_ops, L('getlocal', 10), L('add'), L('decrement'), L('getlocal', 10), L('divide'),
        L('convert_i'), L('setlocal', 9),
        L('getlocal', 9), L('getlocal3'), L('ifngt', t + 'd'),
        L('getlocal', 9), L('setlocal3'),
        (t + 'd', 'nop')]
    # a spacer row object (fmlHdr " "), left on the stack
    spacer = [L('pushstring', s_idk), L('pushstring', s_empty),
              L('pushstring', s_labk), L('pushstring', s_nbsp),
              L('pushstring', s_typek), L('pushbyte', HDR_TYPE),
              L('pushstring', s_unav), L('pushtrue'),
              L('pushstring', s_fmlhdr), L('pushstring', s_space),
              L('newobject', 5)]
    gaps = [
        *hdr_gate('END', 'HG'),
        L('getlocal0'), L('getproperty', fmlHdrOff), L('iftrue', 'END'),
        L('getlocal0'), L('getproperty', fmlMaxR), L('pushbyte', 1), L('iflt', 'END'),
        # these are the values the spacers are placed for (a pending fmlRegap is done by this)
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlMaxR), L('initproperty', fmlGapR),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlScrC), L('initproperty', fmlGapC),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlRegap),
        L('getlocal1'), L('getproperty', length), L('getlocal2'), L('add'), L('convert_i'), L('setlocal', 8),
        L('pushbyte', 0), L('setlocal', 11),
        L('pushfalse'), L('setlocal', 7),
        *per_of([L('getlocal', 8)], 'Q0'),
        L('getlocal3'), L('setlocal', 6),
        ('PS', 'label'),
        L('pushbyte', 0), L('setlocal', 5),
        L('pushbyte', 0), L('setlocal', 4),
        ('LP', 'label'),
        L('getlocal', 4), L('getlocal1'), L('getproperty', length), L('ifnlt', 'PD'),
        L('getlocal', 6), L('pushbyte', 2), L('iflt', 'NX'),
        L('getlocal1'), L('getlocal', 4), L('getproperty', late), L('coerce_a'), L('setlocal', 9),
        L('getlocal', 9), L('iffalse', 'NX'),
        # its row once the spacers before it are in: i itself while inserting, i + k while counting
        L('getlocal', 4), L('getlocal', 7), L('iftrue', 'PI'),
        L('getlocal', 5), L('add'),
        ('PI', 'convert_i'), L('setlocal', 12),
        # a column top (not the first): a mod or Back gets a spacer before it; a header or spacer starts it as is
        L('getlocal', 12), L('pushbyte', 0), L('ifngt', 'CB'),
        L('getlocal', 12), L('getlocal', 6), L('modulo'), L('convert_i'), L('pushbyte', 0), L('ifne', 'CB'),
        L('pushstring', s_fmlhdr), L('getlocal', 9), L('in'), L('iffalse', 'ADD'),
        L('getlocal', 9), L('getproperty', fmlHdrP), L('iftrue', 'NX'),
        L('jump', 'ADD'),
        # a column's last row: a header (not a spacer) gets a spacer before it
        ('CB', 'pushstring', s_fmlhdr), L('getlocal', 9), L('in'), L('iffalse', 'NX'),
        L('getlocal', 9), L('getproperty', fmlHdrP), L('iffalse', 'NX'),
        L('getlocal', 9), L('getproperty', fmlHdrP), L('pushstring', s_space), L('ifeq', 'NX'),
        L('getlocal', 12), L('getlocal', 6), L('modulo'), L('convert_i'),
        L('getlocal', 6), L('decrement_i'), L('ifne', 'NX'),
        ('ADD', 'inclocal_i', 5),
        L('getlocal', 7), L('iffalse', 'NX'),
        L('getlocal1'), L('getlocal', 4), L('pushbyte', 0), *spacer,
        L('callpropvoid', spliceM, 3),
        L('inclocal_i', 4),
        ('NX', 'inclocal_i', 4), L('jump', 'LP'),
        # end padding (counted while counting, pushed while inserting): blank rows at the end (before Back) until
        # fmlLayout's rows per column is P (per grows by at most 1 a row, so it gets there exactly), one more when
        # Back would start a column (Back is the last row: rows - 1)
        ('PD', 'pushbyte', 0), L('setlocal', 12),
        ('PL', 'label'),
        L('getlocal', 7), L('iftrue', 'T1'),
        L('getlocal', 8), L('getlocal', 5), L('add'), L('convert_i'), L('setlocal', 13),
        L('jump', 'T2'),
        ('T1', 'getlocal1'), L('getproperty', length), L('getlocal2'), L('add'), L('convert_i'), L('setlocal', 13),
        ('T2', 'nop'),
        *per_of([L('getlocal', 13)], 'Q1'),
        L('getlocal3'), L('getlocal', 6), L('iflt', 'GR'),
        L('getlocal2'), L('iffalse', 'PE'),
        L('getlocal', 6), L('pushbyte', 2), L('iflt', 'PE'),
        L('getlocal', 13), L('decrement_i'), L('setlocal', 9),
        L('getlocal', 9), L('pushbyte', 0), L('ifngt', 'PE'),
        L('getlocal', 9), L('getlocal', 6), L('modulo'), L('convert_i'), L('pushbyte', 0), L('ifne', 'PE'),
        ('GR', 'inclocal_i', 12),
        L('getlocal', 12), L('pushbyte', GAP_TRIES), L('ifgt', 'END'),
        L('getlocal', 7), L('iffalse', 'GK'),
        L('getlocal1'), *spacer, L('callpropvoid', pushM, 1),
        L('jump', 'PL'),
        ('GK', 'inclocal_i', 5),
        L('jump', 'PL'),
        ('PE', 'getlocal', 7), L('iftrue', 'END'),
        # counted: rows per column with the spacers in exactly P -> insert them; else try P + 1 (none found within
        # GAP_TRIES: no spacers, rather than ones placed for another P)
        L('getlocal3'), L('getlocal', 6), L('ifne', 'NP'),
        L('pushtrue'), L('setlocal', 7),
        L('pushbyte', 0), L('setlocal', 11),
        L('jump', 'PS'),
        ('NP', 'inclocal_i', 6),
        L('inclocal_i', 11),
        L('getlocal', 11), L('pushbyte', GAP_TRIES), L('ifgt', 'END'),
        L('jump', 'PS'),
        ('END', 'returnvoid'),
    ]

    # fmlRegapNow(): fmlRegap - the list shown again for the current columns, the selected entry still selected
    #   1 sel, 2 dp, 3 row
    regap = [
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlRegap),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'T'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iftrue', 'T'),
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'T'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'T'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'T'),
        L('getlocal3'), L('getproperty', idP), L('iffalse', 'T'),
        L('getlocal0'), L('getlocal3'), L('getproperty', idP), L('convert_s'), L('initproperty', fmlKeepId),
        ('T', 'getlocal0'), L('callpropvoid', m_refresh, 0),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        L('returnvoid'),
    ]

    # fmlKindOf(row):int - the row's category (fmlKind) 0..NUM_CATS-1, -1 for a Menu Organizer category; Misc when
    # it has none (an older script) or an unknown one   2 kind
    kind = [
        L('getlocal1'), L('iffalse', 'MISC'),
        L('pushstring', s_fmlkind), L('getlocal1'), L('in'), L('iffalse', 'MISC'),
        L('getlocal1'), L('getproperty', fmlKindP), L('convert_i'), L('setlocal2'),
        L('getlocal2'), L('pushbyte', 255), L('iflt', 'MISC'),
        L('getlocal2'), L('pushbyte', NUM_CATS), L('ifge', 'MISC'),
        L('getlocal2'), L('returnvalue'),
        ('MISC', 'pushbyte', NUM_CATS - 1), L('returnvalue'),
    ]

    # fmlCatName(i):String - category i's name: fmlNames from the script, else the English CAT_NAMES; "" for none
    #   2 names
    cname = [
        L('getlocal1'), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'NONE'),
        L('getlocal1'), L('pushbyte', NUM_CATS), L('ifge', 'NONE'),
        L('getlocal0'), L('getproperty', fmlNames), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'EN'),
        L('getlocal2'), L('getproperty', length), L('pushbyte', NUM_SORTS + 3 + NUM_CATS), L('iflt', 'EN'),
        L('getlocal2'), L('getlocal1'), L('pushbyte', NUM_SORTS + 3), L('add_i'), L('getproperty', late),
        L('convert_s'), L('returnvalue'),
        ('EN', 'pushstring', s_catnames), L('pushstring', s_bar), L('callproperty', splitM, 1),
        L('getlocal1'), L('getproperty', late), L('convert_s'), L('returnvalue'),
        ('NONE', 'pushstring', s_empty), L('returnvalue'),
    ]

    # fmlCatNext(): X / Insert in By category - the selected mod to the next category (after Misc: the first), on
    # the row itself (the same object as in fmlAll, so later sorts keep it), the list shown again with it still
    # selected, the script told next frame ("cat", "id:kind"). Not a header, Back or a Menu Organizer category.
    #   1 sel, 2 dp, 3 row, 4 kind
    cnext = [
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'END'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iftrue', 'END'),
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'END'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('getlocal3'), L('getproperty', idP), L('iffalse', 'END'),
        *isBack(3, 'END', 'ifeq'),
        L('getlocal0'), L('getlocal3'), L('callproperty', m_kind, 1), L('convert_i'), L('setlocal', 4),
        L('getlocal', 4), L('pushbyte', 0), L('iflt', 'END'),
        L('getlocal', 4), L('increment_i'), L('pushbyte', NUM_CATS), L('modulo'), L('convert_i'), L('setlocal', 4),
        L('getlocal3'), L('getlocal', 4), L('setproperty', fmlKindP),
        L('getlocal0'), L('getlocal3'), L('getproperty', idP), L('convert_s'), L('initproperty', fmlKeepId),
        L('getlocal0'), L('getlocal3'), L('getproperty', idP), L('convert_s'), L('pushstring', s_colon), L('add'),
        L('getlocal', 4), L('add'), L('initproperty', fmlPCat),
        L('getlocal0'), L('callpropvoid', m_refresh, 0),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        ('END', 'returnvoid'),
    ]

    # fmlFlag(): LB / Page Up: the selected entry a favorite or not (it stays selected); told to the script next
    # frame ("id:1" / "id:0"). Headers, Back and Menu Organizer categories are left alone.   1 sel, 2 dp, 3 row, 4 id
    flag = [
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'END'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iftrue', 'END'),
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'END'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('getlocal3'), L('getproperty', idP), L('iffalse', 'END'),
        *isBack(3, 'END', 'ifeq'),
        L('getlocal3'), L('getproperty', fmlCatP), L('convert_b'), L('iftrue', 'END'),
        L('getlocal3'), L('getproperty', idP), L('convert_s'), L('coerce_a'), L('setlocal', 4),
        L('getlocal3'), L('getlocal3'), L('getproperty', fmlFavP), L('convert_b'), L('not'),
        L('setproperty', fmlFavP),
        L('getlocal0'), L('getlocal', 4), L('pushstring', s_colon), L('add'),
        L('getlocal3'), L('getproperty', fmlFavP), L('convert_b'), L('convert_i'), L('add'),
        L('initproperty', fmlPFav),
        L('getlocal0'), L('getlocal', 4), L('initproperty', fmlKeepId),
        L('getlocal0'), L('callpropvoid', m_refresh, 0),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        ('END', 'returnvoid'),
    ]

    # fmlFlagPrompts(): every frame (from fmlUi) - "LB / Page Up Favorite" while the Mods list has the focus.
    #   1 input feedback
    fpr = [
        L('getlocal0'), L('getproperty', parentP), L('coerce_a'), L('setlocal1'),
        L('getlocal1'), L('iffalse', 'END'),
        L('pushstring', s_ifm), L('getlocal1'), L('in'), L('iffalse', 'END'),
        L('getlocal1'), L('getproperty', ifmP), L('coerce_a'), L('setlocal1'),
        L('getlocal1'), L('iffalse', 'END'),
        L('getlocal0'), L('getproperty', fmlMods), L('iffalse', 'OFF'),
        L('getlocal0'), L('getproperty', locked), L('pushbyte', 0), L('ifge', 'OFF'),
        L('getlocal0'), L('getproperty', fmlFvPr), L('iftrue', 'END'),
        L('getlocal1'), L('pushshort', FAV_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal1'), L('pushshort', FAV_ACTION), L('pushstring', s_l1), L('pushbyte', KEY_PGUP),
        *nlabel(FAV_IDX, s_favp, 'P1'), L('pushtrue'), L('callpropvoid', appendB, 5),
        L('getlocal0'), L('pushtrue'), L('initproperty', fmlFvPr),
        L('jump', 'END'),
        ('OFF', 'getlocal0'), L('getproperty', fmlFvPr), L('iffalse', 'END'),
        L('getlocal1'), L('pushshort', FAV_ACTION), L('pushtrue'), L('callpropvoid', removeB, 2),
        L('getlocal0'), L('pushfalse'), L('initproperty', fmlFvPr),
        ('END', 'returnvoid'),
    ]

    # fmlCatReset(): Y / Home in By category. Not armed (or armed longer than RESET_MS ago): arm (fmlUi shows the
    # prompt as "Press again to reset"). Armed: every Mods row with a category of ours (fmlKind >= 0) and the
    # script's guess (fmlGuess; rows of an older script have none and stay) goes back to the guess, the list shown
    # again with the selected entry still selected, the script told next frame ("catreset" with the ids reset,
    # "id;id;...": forget the categories set with X / Insert for those). A Menu Organizer category row (fmlKind -1)
    # in the list shown has its own list (subElements) reset too, so a reset from the top level covers all of them
    # and one inside a category only that category.   1 sel, 2 dp, 3 row, 4 i, 5 now, 6 ids
    crst = [
        L('findpropstrict', getTimer), L('callproperty', getTimer, 0), L('convert_d'), L('setlocal', 5),
        L('getlocal0'), L('getproperty', fmlRArmT), L('pushbyte', 0), L('ifngt', 'ARM'),
        L('getlocal', 5), L('getlocal0'), L('getproperty', fmlRArmT), L('subtract'), L('pushshort', RESET_MS),
        L('ifgt', 'ARM'),
        L('getlocal0'), L('pushbyte', 0), L('initproperty', fmlRArmT),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        *lst, L('getproperty', selIdx), L('convert_i'), L('setlocal1'),
        L('getlocal1'), L('pushbyte', 0), L('iflt', 'T'),
        L('getlocal0'), L('getlocal1'), L('callproperty', m_ishdr, 1), L('iftrue', 'T'),
        *lst, L('getproperty', dprov), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'T'),
        L('getlocal1'), L('getlocal2'), L('getproperty', length), L('ifnlt', 'T'),
        L('getlocal2'), L('getlocal1'), L('getproperty', late), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'T'),
        L('getlocal3'), L('getproperty', idP), L('iffalse', 'T'),
        L('getlocal0'), L('getlocal3'), L('getproperty', idP), L('convert_s'), L('initproperty', fmlKeepId),
        ('T', 'pushstring', s_empty), L('coerce_a'), L('setlocal', 6),
        L('getlocal0'), L('getproperty', fmlAll), L('iffalse', 'RF'),
        L('pushbyte', 0), L('setlocal', 4),
        ('L0', 'label'),
        L('getlocal', 4), L('getlocal0'), L('getproperty', fmlAll), L('getproperty', length), L('ifnlt', 'RF'),
        L('getlocal0'), L('getproperty', fmlAll), L('getlocal', 4), L('getproperty', late), L('coerce_a'),
        L('setlocal3'),
        L('getlocal0'), L('getlocal', 6), L('getlocal3'), L('callproperty', m_rrow, 2), L('coerce_a'),
        L('setlocal', 6),
        L('inclocal_i', 4), L('jump', 'L0'),
        ('RF', 'getlocal', 6), L('iffalse', 'RR'),
        L('getlocal0'), L('getlocal', 6), L('convert_s'), L('initproperty', fmlPRst),
        ('RR', 'getlocal0'), L('callpropvoid', m_refresh, 0),
        L('getlocal0'), L('pushnull'), L('initproperty', fmlKeepId),
        L('returnvoid'),
        ('ARM', 'getlocal0'), L('getlocal', 5), L('initproperty', fmlRArmT),
        L('returnvoid'),
    ]

    # fmlRstRow(ids, row): fmlCatReset for one row; returns ids with the id of each row reset added (";"-joined).
    # A Mods row with a category of ours (fmlKind >= 0) and the script's guess (fmlGuess) goes back to the guess; a
    # Menu Organizer category (fmlKind < 0 with subElements): each row of its own list, the same way.
    #   1 ids, 2 row, 3 sub, 4 j
    rrow = [
        L('getlocal2'), L('iffalse', 'END'),
        # "in" first: a sealed row object would throw on an unknown property
        L('pushstring', s_fmlkind), L('getlocal2'), L('in'), L('iffalse', 'END'),
        L('getlocal2'), L('getproperty', fmlKindP), L('convert_i'), L('pushbyte', 0), L('ifge', 'MOD'),
        L('pushstring', s_subel), L('getlocal2'), L('in'), L('iffalse', 'END'),
        L('getlocal2'), L('getproperty', subElP), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('pushbyte', 0), L('setlocal', 4),
        ('S0', 'label'),
        L('getlocal', 4), L('getlocal3'), L('getproperty', length), L('ifnlt', 'END'),
        L('getlocal0'), L('getlocal1'), L('getlocal3'), L('getlocal', 4), L('getproperty', late),
        L('callproperty', m_rrow, 2), L('coerce_a'), L('setlocal1'),
        L('inclocal_i', 4), L('jump', 'S0'),
        ('MOD', 'pushstring', s_fmlguess), L('getlocal2'), L('in'), L('iffalse', 'END'),
        L('getlocal2'), L('getlocal2'), L('getproperty', fmlGuessP), L('convert_i'), L('setproperty', fmlKindP),
        L('getlocal2'), L('getproperty', idP), L('iffalse', 'END'),
        L('getlocal1'), L('iffalse', 'ONE'),
        L('getlocal1'), L('convert_s'), L('pushstring', s_semi), L('add'),
        L('getlocal2'), L('getproperty', idP), L('convert_s'), L('add'), L('coerce_a'), L('setlocal1'),
        L('jump', 'END'),
        ('ONE', 'getlocal2'), L('getproperty', idP), L('convert_s'), L('coerce_a'), L('setlocal1'),
        ('END', 'getlocal1'), L('returnvalue'),
    ]

    any_t = 0
    M.add_method(c, ci, m_kind, [any_t], any_t, kind, 4, 3, lbody, 'fko_')
    M.add_method(c, ci, m_crst, [], void, crst, 6, 7, lbody, 'fcr_')
    M.add_method(c, ci, m_flag, [], void, flag, 8, 5, lbody, 'ffl_')
    M.add_method(c, ci, m_fpr, [], void, fpr, 8, 2, lbody, 'ffp_')
    M.add_method(c, ci, m_rrow, [any_t, any_t], any_t, rrow, 6, 5, lbody, 'frr_')
    M.add_method(c, ci, m_cname, [any_t], any_t, cname, 5, 3, lbody, 'fcn_')
    M.add_method(c, ci, m_cnext, [], void, cnext, 6, 5, lbody, 'fcx_')
    M.add_method(c, ci, m_ishdr, [any_t], any_t, ishdr, 4, 4, lbody, 'fhi_')
    M.add_method(c, ci, m_hskip, [any_t, any_t], any_t, hskip, 4, 5, lbody, 'fhs_')
    M.add_method(c, ci, m_hdrs, [any_t], any_t, hdrs, 14, 8, lbody, 'fhr_')
    M.add_method(c, ci, m_hdraw, [any_t], any_t, hdraw, 8, 9, lbody, 'fhd_')
    M.add_method(c, ci, m_htog, [], void, htog, 6, 4, lbody, 'fht_')
    M.add_method(c, ci, m_gaps, [any_t, any_t], void, gaps, 16, 14, lbody, 'fgp_')
    M.add_method(c, ci, m_regap, [], void, regap, 6, 4, lbody, 'frg_')
    M.add_method(c, ci, m_hits, [any_t], any_t, hits, 6, 4, lbody, 'fh2_')
    M.add_method(c, ci, m_view, [any_t], any_t, view, 8, 10, lbody, 'fv_')
    M.add_method(c, ci, m_less, [any_t, any_t], any_t, less, 6, 7, lbody, 'fc_')
    M.add_method(c, ci, m_refresh, [], void, refresh, 5, 1, lbody, 'fx_')
    M.add_method(c, ci, m_tell, [any_t, any_t], void, tell, 8, 4, lbody, 'ft2_')
    M.add_method(c, ci, m_parse, [any_t], void, parse, 8, 9, lbody, 'fq_')
    M.add_method(c, ci, m_key, [any_t], any_t, key, 8, 6, lbody, 'fk_')
    M.add_method(c, ci, m_ui, [], void, ui, 10, 7, lbody, 'fi_')
    M.add_method(c, ci, m_frame, [any_t], void, frame, 6, 6, lbody, 'fz_')

    # fmlGov(e): every frame. At MENU_FPS a plain timeline clip (class MovieClip itself: the unnamed animation
    # sprites, which have no frame scripts) would play MENU_FPS/30 times too fast, so the governor plays them:
    # a clip seen advancing by itself is stopped and from then on stepped by the 30 fps ticks that really passed
    # (looping like the timeline). A clip someone else moves (gotoAndStop / gotoAndPlay) is watched again: if it
    # then advances by itself it is taken over again, if not it is left where it was put. State per clip in its
    # dynamic property fmlGS: frame > 0 = driven, -frame = watched.
    # 1 e, 2 now, 3 ms / ticks, 4 stack, 5 container, 6 i, 7 n, 8 child, 9 state, 10 frame, 11 total
    M.add_slot(c, ci, fmlGovT, t_num, 0, 0)
    M.add_slot(c, ci, fmlGovA, t_num, 0, 0)
    rootP, popM, ctorP = pubn('root'), pubn('pop'), pubn('constructor')
    totP, curP, gasP, stopP, gsP = pubn('totalFrames'), pubn('currentFrame'), pubn('gotoAndStop'), pubn('stop'), \
        pubn('fmlGS')
    mcC = None
    for ops in (('getlex',), ('coerce', 'astypelate', 'istypelate', 'findpropstrict', 'constructprop')):
        try:
            mcC = c.used_mn('MovieClip', ops)
            break
        except PatchError:
            pass
    if mcC is None:
        raise PatchError('no MovieClip reference for fmlGov')
    s_numch, s_gs = string('numChildren'), string('fmlGS')
    d_tick = c.double(1000.0 / TIMELINE_FPS)
    gov = [
        L('findpropstrict', getTimer), L('callproperty', getTimer, 0), L('convert_d'), L('setlocal2'),
        L('getlocal2'), L('getlocal0'), L('getproperty', fmlGovT), L('subtract'), L('convert_d'), L('setlocal3'),
        L('getlocal0'), L('getlocal2'), L('initproperty', fmlGovT),
        # first frame after the menu was closed or a long hitch: no time passed for the animations
        L('getlocal3'), L('pushshort', 250), L('ifgt', 'Z'),
        L('getlocal3'), L('pushbyte', 0), L('ifge', 'A'),
        ('Z', 'pushbyte', 0), L('convert_d'), L('setlocal3'),
        ('A', 'getlocal0'), L('getlocal0'), L('getproperty', fmlGovA), L('getlocal3'), L('add'),
        L('initproperty', fmlGovA),
        L('getlocal0'), L('getproperty', fmlGovA), L('pushdouble', d_tick), L('divide'), L('convert_i'),
        L('setlocal3'),
        L('getlocal0'), L('getlocal0'), L('getproperty', fmlGovA), L('getlocal3'), L('pushdouble', d_tick),
        L('multiply'), L('subtract'), L('initproperty', fmlGovA),
        # walk the visible display list from the root
        L('getlocal0'), L('getproperty', rootP), L('newarray', 1), L('setlocal', 4),
        ('OL', 'label'),
        L('getlocal', 4), L('getproperty', length), L('pushbyte', 0), L('ifngt', 'END'),
        L('getlocal', 4), L('callproperty', popM, 0), L('coerce_a'), L('setlocal', 5),
        L('getlocal', 5), L('iffalse', 'OL'),
        L('getlocal', 5), L('getproperty', numCh), L('convert_i'), L('setlocal', 7),
        L('pushbyte', 0), L('setlocal', 6),
        ('IL', 'label'),
        L('getlocal', 6), L('getlocal', 7), L('ifnlt', 'OL'),
        L('getlocal', 5), L('getlocal', 6), L('callproperty', gca, 1), L('coerce_a'), L('setlocal', 8),
        L('inclocal_i', 6),
        L('getlocal', 8), L('iffalse', 'IL'),
        L('pushstring', s_numch), L('getlocal', 8), L('in'), L('iffalse', 'IL'),
        L('getlocal', 8), L('getproperty', vis), L('iffalse', 'IL'),
        L('getlocal', 4), L('getlocal', 8), L('callpropvoid', pushM, 1),
        L('getlocal', 8), L('getproperty', ctorP), L('getlex', mcC), L('ifstrictne', 'IL'),
        L('getlocal', 8), L('getproperty', totP), L('convert_i'), L('setlocal', 11),
        L('getlocal', 11), L('pushbyte', 1), L('ifngt', 'IL'),
        L('getlocal', 8), L('getproperty', curP), L('convert_i'), L('setlocal', 10),
        L('pushbyte', 0), L('setlocal', 9),
        L('pushstring', s_gs), L('getlocal', 8), L('in'), L('iffalse', 'S0'),
        L('getlocal', 8), L('getproperty', gsP), L('convert_i'), L('setlocal', 9),
        ('S0', 'getlocal', 9), L('pushbyte', 0), L('ifngt', 'OBS'),
        # driven: moved by someone else -> watch it; else step it by the ticks that passed
        L('getlocal', 10), L('getlocal', 9), L('ifeq', 'DR'),
        L('getlocal', 8), L('getlocal', 10), L('negate_i'), L('setproperty', gsP), L('jump', 'IL'),
        ('DR', 'getlocal3'), L('pushbyte', 0), L('ifngt', 'IL'),
        L('getlocal', 10), L('decrement_i'), L('getlocal3'), L('add_i'), L('getlocal', 11), L('modulo'),
        L('increment_i'), L('setlocal', 10),
        L('getlocal', 8), L('getlocal', 10), L('callpropvoid', gasP, 1),
        L('getlocal', 8), L('getlocal', 10), L('setproperty', gsP), L('jump', 'IL'),
        # watched (state -frame) or new (0): one frame on by itself since last time = playing -> take it over
        ('OBS', 'getlocal', 9), L('pushbyte', 0), L('ifnlt', 'NEWO'),
        L('getlocal', 9), L('negate_i'), L('setlocal', 9),
        L('getlocal', 10), L('getlocal', 9), L('increment_i'), L('ifeq', 'TAKE'),
        L('getlocal', 9), L('getlocal', 11), L('ifne', 'NEWO'),
        L('getlocal', 10), L('pushbyte', 1), L('ifne', 'NEWO'),
        ('TAKE', 'getlocal', 8), L('callpropvoid', stopP, 0),
        L('getlocal', 8), L('getlocal', 10), L('setproperty', gsP), L('jump', 'IL'),
        ('NEWO', 'getlocal', 8), L('getlocal', 10), L('negate_i'), L('setproperty', gsP), L('jump', 'IL'),
        ('END', 'returnvoid'),
    ]
    M.add_method(c, ci, m_gov, [any_t], void, gov, 8, 12, lbody, 'fg_')
    M.add_method(c, ci, m_top, [any_t], void, top, 6, 3, lbody, 'ft_')
    M.add_method(c, ci, m_bar, [], void, bar, 10, 6, lbody, 'fb_')
    M.add_method(c, ci, m_bdown, [any_t], void, bdown, 4, 2, lbody, 'fd_')
    M.add_method(c, ci, m_bmove, [any_t], void, bmove, 8, 3, lbody, 'fm_')
    M.add_method(c, ci, m_bup, [any_t], void, bup, 3, 2, lbody, 'fu_')
    M.add_method(c, ci, m_wheel, [any_t], void, wheel, 6, 2, lbody, 'fw_')
    M.add_method(c, ci, m_follow, [], void, follow, 4, 1, lbody, 'ff_')
    M.add_method(c, ci, m_strip, [any_t], void, strip, 10, 5, lbody, 'fs_')
    M.add_method(c, ci, m_prep, [any_t], void, prep, 10, 10, lbody, 'fp_')
    M.add_method(c, ci, m_fmt, [any_t], void, fmt, 6, 8, lbody, 'fo_')
    M.add_method(c, ci, m_shrink, [any_t, any_t], void, shrink, 5, 4, lbody, 'fk2_')
    M.add_method(c, ci, m_apply, [any_t], void, apply_, 6, 4, lbody, 'fa_')
    M.add_method(c, ci, m_layout, [], any_t, layout, 10, 19, lbody, 'fl_')
    M.add_method(c, ci, m_nav, [any_t], any_t, nav, 10, 9, lbody, 'fn_')
    M.add_method(c, ci, m_repos, [any_t], void, rep, 4, 2, lbody, 'fr_')
    M.add_method(c, ci, m_hide, [], void, hide, 6, 4, lbody, 'fh_')

    # hook 1: setListData, before "getlocal0; getproperty mcList; getlocal1; setproperty dataProvider"
    ins = abcrt.decode(lbody['code'])
    k = [i for i, x in enumerate(ins) if op_name(x) == 'setproperty' and abc.mn(x[2][0]) == 'dataProvider']
    if len(k) != 1 or op_name(ins[k[0] - 3]) != 'getlocal0':
        raise PatchError('setListData: dataProvider store not found')
    ins = insert_at(ins, k[0] - 3, [L('getlocal0'), L('getlocal1'), L('callpropvoid', m_prep, 1),
                                     L('getlocal0'), L('getlocal1'), L('callproperty', m_view, 1),
                                     L('dup'), L('istype', arrC), L('iffalse', 'VX'),
                                     L('coerce', arrC), L('setlocal1'), L('jump', 'VY'),
                                     ('VX', 'pop'),
                                     # fmlView's own selection (Back to a re-sorted list) replaces the restored one
                                     ('VY', 'getlocal0'), L('getproperty', fmlSelOut), L('convert_i'), L('dup'),
                                     L('pushbyte', 0), L('iflt', 'VS'),
                                     L('setlocal2'), L('jump', 'VZ'),
                                     ('VS', 'pop'), ('VZ', 'nop')], 'h1_')
    lbody['code'], _ = abcrt.encode(ins)
    lbody['max_stack'] = max(lbody['max_stack'], 3)

    # hook 9: W3MenuListItemRenderer.updateText, after the label is drawn (and capitalized) and mcFrame is looked up
    # (so a header row keeps no stale mcFrame), before the selection frame is sized to the text: a row of our list redraws in fmlAlignNow's format (fmlHdrDraw -> fmlApplyTo); a letter
    # header is drawn by fmlHdrDraw and gets no selection frame.
    #   p = parent; if (p && "fmlHdrDraw" in p && p.fmlHdrDraw(this)) return
    ubody = c.body('W3MenuListItemRenderer::updateText')
    ins = abcrt.decode(ubody['code'])
    k = [i for i in range(1, len(ins) - 1) if op_name(ins[i]) == 'findpropstrict' and abc.mn(ins[i][2][0]) == 'getChildByName'
         and op_name(ins[i - 1]) == 'getlocal0' and op_name(ins[i + 1]) == 'pushstring'
         and abc.strings[ins[i + 1][2][0]] == b'mcFrame']
    if len(k) != 1 or op_name(ins[k[0] + 5]) != 'initproperty' or abc.mn(ins[k[0] + 5][2][0]) != 'mcFrame':
        raise PatchError('updateText: mcFrame lookup not found')
    s_hdraw = string('fmlHdrDraw')
    ins = insert_at(ins, k[0] + 6, [L('getlocal0'), L('getproperty', parentP), L('coerce_a'),
                                     L('dup'), L('iffalse', 'NP'),
                                     L('dup'), L('pushstring', s_hdraw), L('swap'), L('in'), L('iffalse', 'NP'),
                                     L('getlocal0'), L('callproperty', m_hdraw, 1), L('iffalse', 'UD'),
                                     L('returnvoid'),
                                     ('NP', 'pop'), ('UD', 'nop')], 'h9_')
    # fmlFitFrame(row): the selection frame (mcFrame, a new one on each selected_* frame of the renderer) fitted to
    # the row's text as it is aligned now. Lists in the column format (fmlMods, fmlAlignNow "left" / "right"): it
    # hugs the name - FRAME_PAD past each end of the text, FRAME_TRIM shorter than vanilla, on vanilla's middle. Any
    # other list: the vanilla geometry back if this frame was fitted before (a frame never fitted is left alone).
    # From the end of updateText (hook 9b) and from the end of fmlApplyTo, so a row re-aligned without a redraw (the
    # module switching lists) refits too. Header / spacer rows (data.fmlHdr) are skipped: fmlHdrDraw keeps their
    # frame at alpha 0. The vanilla x / y / width / height are kept on the frame (fmlVX, fmlVY, fmlVW, fmlVH) the
    # first time it is fitted; fmlFH = the height written last, so a height vanilla set since (updateText:
    # textHeight + 33; hook 9a clears fmlFH to NaN right before it) becomes the new fmlVH. Every call starts from the vanilla geometry, so nothing drifts.
    #   1 row, 2 f, 3 t, 4 bounds, 5 mid, 6 left, 7 data / fit
    if op_name(ins[-1]) != 'returnvoid':
        raise PatchError('updateText: unexpected end')
    try:
        boundsM = c.used_mn('getBounds', ('callproperty',))
    except PatchError:
        boundsM = c.new_name(X, 'getBounds')
    vxP, vyP, vwP, vhP, fhP = (c.new_name(X, n) for n in ('fmlVX', 'fmlVY', 'fmlVW', 'fmlVH', 'fmlFH'))
    s_vx = string('fmlVX')
    fit = [
        L('getlocal1'), L('pushstring', s_mcframe), L('callproperty', gcbn, 1), L('coerce_a'), L('setlocal2'),
        L('getlocal2'), L('iffalse', 'END'),
        L('getlocal1'), L('getproperty', tf), L('coerce_a'), L('setlocal3'),
        L('getlocal3'), L('iffalse', 'END'),
        L('getlocal1'), L('getproperty', dataP), L('coerce_a'), L('setlocal', 7),
        L('getlocal', 7), L('iffalse', 'D1'),
        L('pushstring', s_fmlhdr), L('getlocal', 7), L('in'), L('iffalse', 'D1'),
        L('getlocal', 7), L('getproperty', fmlHdrP), L('iftrue', 'END'),
        # 7 = fit: fmlMods && fmlAlignNow && fmlAlignNow != "center"
        ('D1', 'getlocal0'), L('getproperty', fmlMods), L('convert_b'), L('dup'), L('iffalse', 'W1'),
        L('pop'), L('getlocal0'), L('getproperty', fmlAlignNow), L('convert_b'), L('dup'), L('iffalse', 'W1'),
        L('pop'), L('getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_center), L('equals'), L('not'),
        ('W1', 'convert_b'), L('setlocal', 7),
        # the vanilla geometry, kept before the first change
        L('pushstring', s_vx), L('getlocal2'), L('in'), L('iftrue', 'HAVE'),
        L('getlocal', 7), L('iffalse', 'END'),
        L('getlocal2'), L('getlocal2'), L('getproperty', X), L('setproperty', vxP),
        L('getlocal2'), L('getlocal2'), L('getproperty', Y), L('setproperty', vyP),
        L('getlocal2'), L('getlocal2'), L('getproperty', Wd), L('setproperty', vwP),
        L('getlocal2'), L('getlocal2'), L('getproperty', Hd), L('setproperty', vhP),
        L('jump', 'RST'),
        ('HAVE', 'getlocal2'), L('getproperty', Hd), L('getlocal2'), L('getproperty', fhP), L('ifeq', 'RST'),
        L('getlocal2'), L('getlocal2'), L('getproperty', Hd), L('setproperty', vhP),
        # back to vanilla
        ('RST', 'getlocal2'), L('getlocal2'), L('getproperty', vwP), L('setproperty', Wd),
        L('getlocal2'), L('getlocal2'), L('getproperty', vhP), L('setproperty', Hd),
        L('getlocal2'), L('getlocal2'), L('getproperty', vxP), L('setproperty', X),
        L('getlocal2'), L('getlocal2'), L('getproperty', vyP), L('setproperty', Y),
        L('getlocal', 7), L('iffalse', 'MARK'),
        # fit: b = f.getBounds(row); mid = b.y + b.height/2; f.width = t.textWidth + 2*FRAME_PAD; f.height -= FRAME_TRIM
        L('getlocal2'), L('getlocal1'), L('callproperty', boundsM, 1), L('coerce_a'), L('setlocal', 4),
        L('getlocal', 4), L('getproperty', Y), L('getlocal', 4), L('getproperty', Hd), L('pushbyte', 2),
        L('divide'), L('add'), L('convert_d'), L('setlocal', 5),
        L('getlocal2'), L('getlocal3'), L('getproperty', twP), L('pushbyte', 2 * FRAME_PAD), L('add'),
        L('setproperty', Wd),
        L('getlocal2'), L('getlocal2'), L('getproperty', Hd), L('pushbyte', FRAME_TRIM), L('subtract'),
        L('setproperty', Hd),
        # left = (right: t.x + t.width - t.textWidth - 2; left: t.x + 2; else centred) - FRAME_PAD
        L('getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_right), L('ifne', 'LL'),
        L('getlocal3'), L('getproperty', X), L('getlocal3'), L('getproperty', Wd), L('add'),
        L('getlocal3'), L('getproperty', twP), L('subtract'), L('pushbyte', 2), L('subtract'),
        L('jump', 'LZ'),
        ('LL', 'getlocal0'), L('getproperty', fmlAlignNow), L('pushstring', s_left), L('ifne', 'LC'),
        L('getlocal3'), L('getproperty', X), L('pushbyte', 2), L('add'),
        L('jump', 'LZ'),
        ('LC', 'getlocal3'), L('getproperty', X),
        L('getlocal3'), L('getproperty', Wd), L('getlocal3'), L('getproperty', twP), L('subtract'),
        L('pushbyte', 2), L('divide'), L('add'),
        ('LZ', 'pushbyte', FRAME_PAD), L('subtract'), L('convert_d'), L('setlocal', 6),
        # b = f.getBounds(row); f.x += left - b.x; f.y += mid - (b.y + b.height/2)
        L('getlocal2'), L('getlocal1'), L('callproperty', boundsM, 1), L('coerce_a'), L('setlocal', 4),
        L('getlocal2'), L('getlocal2'), L('getproperty', X), L('getlocal', 6), L('getlocal', 4),
        L('getproperty', X), L('subtract'), L('add'), L('setproperty', X),
        L('getlocal2'), L('getlocal2'), L('getproperty', Y), L('getlocal', 5),
        L('getlocal', 4), L('getproperty', Y), L('getlocal', 4), L('getproperty', Hd), L('pushbyte', 2),
        L('divide'), L('add'), L('subtract'), L('add'), L('setproperty', Y),
        ('MARK', 'getlocal2'), L('getlocal2'), L('getproperty', Hd), L('setproperty', fhP),
        ('END', 'returnvoid'),
    ]
    M.add_method(c, ci, m_fit, [any_t], void, fit, 8, 8, lbody, 'fff_')
    # hook 9a: just before vanilla sizes the frame (mcFrame.height = textHeight + 33, only on the path that reaches
    # it, so hideSelection / no-frame paths are untouched): mcFrame.fmlFH = NaN. The fit from hook 9 (fmlApplyTo)
    # already ran this pass and wrote fmlFH; vanilla's new height could equal it to the twip, and fmlFitFrame would
    # then keep the old fmlVH. NaN never compares equal, so the height vanilla sets is always taken as the new fmlVH.
    #   mcFrame.fmlFH = NaN
    # vanilla ends with the sizing; Real-Time Graphics and HDR Menus Preview (patcher merge) adds its text shadow
    # after it, so the sizing is looked for anywhere, once
    sz = ['getlocal0', 'getproperty', 'getlex', 'getproperty', 'pushbyte', 'add', 'setproperty']
    k = [i for i in range(len(ins) - 6) if [op_name(x) for x in ins[i:i + 7]] == sz
         and abc.mn(ins[i + 1][2][0]) == 'mcFrame' and abc.mn(ins[i + 6][2][0]) == 'height']
    if len(k) != 1:
        raise PatchError('updateText: frame sizing not found')
    frameM = ins[k[0] + 1][2][0]
    ins = insert_at(ins, k[0], [L('getlocal0'), L('getproperty', frameM), L('pushnan'),
                                L('setproperty', fhP)], 'h9a_')
    # hook 9b: the end of updateText (every path that sized the frame or skipped it):
    #   p = parent; if (p && "fmlFitFrame" in p) p.fmlFitFrame(this)
    s_fit = string('fmlFitFrame')
    ins = insert_at(ins, len(ins) - 1, [L('getlocal0'), L('getproperty', parentP), L('coerce_a'),
                                         L('dup'), L('iffalse', 'NP'),
                                         L('dup'), L('pushstring', s_fit), L('swap'), L('in'), L('iffalse', 'NP'),
                                         L('getlocal0'), L('callpropvoid', m_fit, 1),
                                         L('jump', 'END'),
                                         ('NP', 'pop'), ('END', 'nop')], 'h9b_')
    ubody['code'], _ = abcrt.encode(ins)
    ubody['max_stack'] = max(ubody['max_stack'], 4)

    # hook 10: W3ScrollingList.selectedIndex set starts with the letter-header skip (before its "same index" check,
    # the highlight sound and the commit), for every list whose parent is a list module (fmlHdrSkip leaves the others
    # and every row that is not a header alone):
    #   p = parent; if (p && "fmlHdrSkip" in p) value += int(p.fmlHdrSkip(value, this))
    b = c.body('W3ScrollingList::selectedIndex set')
    ins = abcrt.decode(b['code'])
    if [op_name(x) for x in ins[:2]] != ['getlocal0', 'pushscope']:
        raise PatchError('W3ScrollingList.selectedIndex set: unexpected start')
    s_hskip = string('fmlHdrSkip')
    ins = insert_at(ins, 2, [L('getlocal0'), L('getproperty', parentP), L('coerce_a'),
                             L('dup'), L('iffalse', 'NP'),
                             L('dup'), L('pushstring', s_hskip), L('swap'), L('in'), L('iffalse', 'NP'),
                             L('getlocal1'), L('getlocal0'), L('callproperty', m_hskip, 2), L('convert_i'),
                             L('getlocal1'), L('add_i'), L('convert_i'), L('setlocal1'),
                             L('jump', 'GO'),
                             ('NP', 'pop'), ('GO', 'nop')], 'h10_')
    b['code'], _ = abcrt.encode(ins)
    b['max_stack'] = max(b['max_stack'], 4)

    # hook 2: repositionRenderers starts with "if (fmlLayout()) return;"
    b = c.body('SimpleListModule::repositionRenderers')
    ins = abcrt.decode(b['code'])
    if [op_name(x) for x in ins[:2]] != ['getlocal0', 'pushscope']:
        raise PatchError('repositionRenderers: unexpected start')
    ins = insert_at(ins, 2, [L('getlocal0'), L('callproperty', m_layout, 0), L('iffalse', 'GO'), L('returnvoid'),
                             ('GO', 'nop')], 'h2_')
    b['code'], _ = abcrt.encode(ins)

    # hook 6: handleIndexChanged (the list's INDEX_CHANGE) starts with fmlFollowSel()
    b = c.body('SimpleListModule::handleIndexChanged')
    ins = abcrt.decode(b['code'])
    if [op_name(x) for x in ins[:2]] != ['getlocal0', 'pushscope']:
        raise PatchError('handleIndexChanged: unexpected start')
    ins = insert_at(ins, 2, [L('getlocal0'), L('callpropvoid', m_follow, 0)], 'h6_')
    b['code'], _ = abcrt.encode(ins)
    b['max_stack'] = max(b['max_stack'], 1)

    # hooks 3/4: lockSelection and hideSelection setters, before their last returnvoid
    for owner, call in (('SimpleListModule::lockSelection set', repR), ('SimpleListModule::hideSelection set', m_hide)):
        b = c.body(owner)
        ins = abcrt.decode(b['code'])
        if op_name(ins[-1]) != 'returnvoid':
            raise PatchError('%s: unexpected end' % owner)
        ins = insert_at(ins, len(ins) - 1, [L('getlocal0'), L('callpropvoid', call, 0)], 'h3_' if call is repR else 'h4_')
        b['code'], _ = abcrt.encode(ins)
        b['max_stack'] = max(b['max_stack'], 2)

    # hook 5: IngameMenu.handleInputNavigate, before "menuListModule.mcList.handleInput(e)"
    b = c.body('IngameMenu::handleInputNavigate')
    ins = abcrt.decode(b['code'])
    k = [i for i, x in enumerate(ins) if op_name(x) == 'callpropvoid' and abc.mn(x[2][0]) == 'handleInput'
         and op_name(ins[i - 2]) == 'getproperty' and abc.mn(ins[i - 3][2][0]) == 'menuListModule']
    if len(k) != 1:
        raise PatchError('handleInputNavigate: list input call not found')
    k = k[0] - 4
    if op_name(ins[k]) != 'getlocal0' or op_name(ins[k + 5]) != 'jump':
        raise PatchError('handleInputNavigate: unexpected shape')
    mlm = ins[k + 1][2][0]
    skip = ins[k + 5][2][0]
    new = M.assemble([L('getlocal0'), L('getproperty', mlm), L('getlocal1'), L('callproperty', m_nav, 1)], 'h5_')
    new.append(['h5_br', abcrt.NAME2OP['iftrue'], [skip]])
    new[0][0] = ins[k][0]
    ins[k] = ['h5_orig', ins[k][1], ins[k][2]]
    ins = ins[:k] + new + ins[k:]
    # hook 5b: same method, before "if (keyUp && !handled) { if (code == KeyCode.E) activateMenuListItem() ..." (after
    # the dialogs): menuListModule.fmlKey(e) first
    want = ['getlocal3', 'convert_b', 'dup', 'iffalse', 'pop', 'getlocal1', 'getproperty', 'not', 'iffalse',
            'getlocal2', 'getproperty', 'getlex', 'getproperty', 'ifne']
    k = [i for i in range(len(ins) - len(want)) if [op_name(x) for x in ins[i:i + len(want)]] == want
         and abc.mn(ins[i + 6][2][0]) == 'handled' and abc.mn(ins[i + 12][2][0]) == 'E']
    if len(k) != 1:
        raise PatchError('handleInputNavigate: E check not found')
    k = k[0]
    act = [x[2][0] for x in ins[k:] if op_name(x) == 'callpropvoid' and abc.mn(x[2][0]) == 'activateMenuListItem'][0]
    inPanel = [x[2][0] for x in ins[k:] if op_name(x) == 'getproperty' and abc.mn(x[2][0]) == 'inPanel'][0]
    ins = insert_at(ins, k, [L('getlocal0'), L('getproperty', inPanel), L('iftrue', 'KX'),
                             L('getlocal0'), L('getproperty', mlm), L('getlocal1'), L('callproperty', m_key, 1),
                             L('convert_i'), L('dup'), L('iffalse', 'KP'),
                             L('pushbyte', 2), L('ifne', 'KR'),
                             L('getlocal0'), L('callpropvoid', act, 0),
                             ('KR', 'returnvoid'),
                             ('KP', 'pop'),
                             ('KX', 'nop')], 'h5b_')
    # Real-Time Graphics and HDR Menus Preview (patcher merge only; absent from vanilla): its T toggle runs first in
    # this method and swallows the key, so T is left to our search while the Mods list itself has the focus (a
    # mod's settings page and every other menu keep the toggle). After its "code == KeyCode.T" test:
    #   if (menuListModule.fmlMods && !inPanel) skip the toggle
    tw = ['getlocal0', 'getproperty', 'iftrue', 'getlocal3', 'iffalse', 'getlocal2', 'getproperty', 'getlex',
          'getproperty', 'equals', 'iffalse', 'getlocal0', 'getproperty']
    t = [i + 5 for i in range(len(ins) - len(tw)) if [op_name(x) for x in ins[i:i + len(tw)]] == tw
         and abc.mn(ins[i + 1][2][0]) == '_isMainMenu' and abc.mn(ins[i + 7][2][0]) == 'KeyCode'
         and abc.mn(ins[i + 8][2][0]) == 'T' and abc.mn(ins[i + 12][2][0]) == 'mcBlackBackground']
    if len(t) > 1:
        raise PatchError('handleInputNavigate: more than one T toggle')
    if t:
        k = t[0] + 6
        new = M.assemble([L('getlocal0'), L('getproperty', mlm), L('getproperty', fmlMods), L('iffalse', 'TK'),
                          L('getlocal0'), L('getproperty', inPanel), L('iftrue', 'TK')], 'h5t_')
        new.append(['h5t_skip', abcrt.NAME2OP['jump'], [ins[k - 1][2][0]]])
        new.append(['h5t_TK', abcrt.NAME2OP['nop'], []])
        new[0][0] = ins[k][0]
        ins[k] = ['h5t_orig', ins[k][1], ins[k][2]]
        ins = ins[:k] + new + ins[k:]
    b['code'], _ = abcrt.encode(ins)

    # Real-Time Graphics merge only: its hint text (configUI: x = 1450, y = 1005) goes to the top right
    b = c.body('IngameMenu::configUI')
    ins = abcrt.decode(b['code'])
    hw = ['getlocal1', 'pushshort', 'setproperty', 'getlocal1', 'pushshort', 'setproperty']
    h = [i for i in range(len(ins) - 5) if [op_name(x) for x in ins[i:i + 6]] == hw
         and ins[i + 1][2][0] == 1450 and abc.mn(ins[i + 2][2][0]) == 'x'
         and ins[i + 4][2][0] == 1005 and abc.mn(ins[i + 5][2][0]) == 'y']
    if len(h) > 1:
        raise PatchError('configUI: more than one hint position')
    if h and any(op_name(x) == 'pushstring' and abc.strings[x[2][0]] == b'[ T ]  TOGGLE TRANSPARENCY' for x in ins):
        ins[h[0] + 4][2][0] = RTG_HINT_Y
        b['code'], _ = abcrt.encode(ins)

    # hook 7: IngameMenu.activateMenuListItem, before handleEntrySelected: an entry of the Mods list was opened
    b = c.body('IngameMenu::activateMenuListItem')
    ins = abcrt.decode(b['code'])
    k = [i for i, x in enumerate(ins) if op_name(x) == 'callproperty' and abc.mn(x[2][0]) == 'handleEntrySelected']
    if len(k) != 1 or [op_name(x) for x in ins[k[0] - 2:k[0]]] != ['getlocal0', 'getlocal']:
        raise PatchError('activateMenuListItem: handleEntrySelected call not found')
    item = ins[k[0] - 1][2][0]
    ins = insert_at(ins, k[0] - 2, [L('getlocal0'), L('getproperty', mlm), L('getproperty', fmlMods), L('iffalse', 'SK'),
                                     L('getlocal0'), L('getproperty', mlm),
                                     L('getlocal', item), L('getproperty', idP), L('convert_s'),
                                     L('setproperty', fmlPOpen),
                                     L('getlocal0'), L('getproperty', mlm),
                                     L('getlocal', item), L('getproperty', idP), L('convert_s'),
                                     L('setproperty', fmlBackId),
                                     ('SK', 'nop')], 'h7_')
    # hook 7b: same method, before the "handleNavigateBack()" it does when another entry (not Back) is clicked while
    # a page is open: that Back is no Back of the player's, so it doesn't re-sort (fmlNoRs, cleared every frame)
    k = [i for i, x in enumerate(ins) if op_name(x) == 'callpropvoid' and abc.mn(x[2][0]) == 'handleNavigateBack']
    if len(k) != 1 or op_name(ins[k[0] - 1]) != 'getlocal0' or op_name(ins[k[0] + 1]) != 'getlocal'             or ins[k[0] + 1][2][0] != 6 or abc.mn(ins[k[0] + 2][2][0]) != 'IGMActionType_Back':
        raise PatchError('activateMenuListItem: in-panel handleNavigateBack not found')
    backLex = ins[k[0] + 2][2][0]
    ins = insert_at(ins, k[0] - 1, [L('getlocal', 6), L('getlex', backLex), L('ifeq', 'NB'),
                                     L('getlocal0'), L('getproperty', mlm), L('pushtrue'), L('setproperty', fmlNoRs),
                                     ('NB', 'nop')], 'h7b_')
    b['code'], _ = abcrt.encode(ins)
    b['max_stack'] = max(b['max_stack'], 4)

    # hook 8: ModuleInputFeedback.updateBackgroundVisibility, before "mcInputBackground.visible = true": the frame is
    # sized from _canvas.getBounds(), which counts the hidden parts of each prompt button (pad icons, key label), so
    # it ends ~160 units past the rightmost button. With the Sort (or Headers) prompt shown, the right padding mirrors the left:
    # width = (canvas.x + b0.x + b0.getViewWidth()) + (canvas.x + bLast.x - rect.x) - rect.x   (b0 = rightmost)
    b = c.body('ModuleInputFeedback::updateBackgroundVisibility')
    ins = abcrt.decode(b['code'])
    k = [i for i in range(len(ins) - 3) if op_name(ins[i]) == 'getlocal0' and op_name(ins[i + 1]) == 'getproperty'
         and abc.mn(ins[i + 1][2][0]) == 'mcInputBackground' and op_name(ins[i + 2]) == 'pushtrue'
         and op_name(ins[i + 3]) == 'setproperty' and abc.mn(ins[i + 3][2][0]) == 'visible']
    if len(k) != 1:
        raise PatchError('updateBackgroundVisibility: unexpected shape')
    pick8 = lambda body, op, n: next(x[2][0] for x in body if op_name(x) == op and abc.mn(x[2][0]) == n)
    bgP, canvasP, listP = (pick8(ins, 'getproperty', 'mcInputBackground'), pick8(ins, 'getproperty', '_canvas'),
                           pick8(ins, 'getproperty', '_buttonsList'))
    xP, widthP = pick8(ins, 'getproperty', 'x'), pick8(ins, 'setproperty', 'width')
    rins = abcrt.decode(c.body('ModuleInputFeedback::repositionButtons')['code'])
    lenP, viewW = pick8(rins, 'getproperty', 'length'), pick8(rins, 'callproperty', 'getViewWidth')
    late8 = pick8(rins, 'getproperty', '[late]')
    ins = insert_at(ins, k[0], [
        L('getlocal0'), L('pushshort', SORT_ACTION), L('callproperty', pubn('hasButton'), 1), L('iftrue', 'OURS'),
        L('getlocal0'), L('pushshort', HDR_ACTION), L('callproperty', pubn('hasButton'), 1), L('iffalse', 'orig'),
        ('OURS', 'getlocal0'), L('getproperty', bgP),
        L('getlocal0'), L('getproperty', canvasP), L('getproperty', xP),
        L('getlocal0'), L('getproperty', listP), L('pushbyte', 0), L('getproperty', late8),
        L('dup'), L('getproperty', xP), L('swap'), L('callproperty', viewW, 0), L('add'), L('add'),
        L('getlocal0'), L('getproperty', canvasP), L('getproperty', xP),
        L('getlocal0'), L('getproperty', listP),
        L('getlocal0'), L('getproperty', listP), L('getproperty', lenP), L('decrement_i'),
        L('getproperty', late8), L('getproperty', xP), L('add'),
        L('getlocal1'), L('getproperty', xP), L('subtract'),
        L('add'),
        L('getlocal1'), L('getproperty', xP), L('subtract'),
        L('setproperty', widthP)], 'h8_')
    b['code'], _ = abcrt.encode(ins)
    b['max_stack'] = max(b['max_stack'], 7)

    # IngameMenu.fmlSetData(s): from the script (Full Mods List store) -> menuListModule.fmlParse(s)
    gi = c.cls('IngameMenu')
    M.add_method(c, gi, c.new_name(like, 'fmlSetData'), [0], void,
                 [L('getlocal0'), L('getproperty', mlm), L('getlocal1'), L('callpropvoid', m_parse, 1),
                  L('returnvoid')], 3, 2, c.body('IngameMenu::setListData'), 'gs_')
    return abc


def abc_late(c):
    """the [late] multiname (runtime name, used by vanilla for dp[i])"""
    abc = c.abc
    for b in abc.bodies:
        for pos, op, args in abcrt.decode(b['code']):
            if abcrt.OPS[op][0] == 'getproperty' and args and abc.mns[args[0]][0] == 0x1B:
                return args[0]
    raise PatchError('no late-name getproperty')


def check_back_branches(abc, before=None):
    """every backward branch must land on OP_label: the game's AS3 VM does not take one that doesn't (the loop body
    then runs once), and avm2verify does not check it. before = {method: code} of the source: a method left as it was
    is not ours to check (Real-Time Graphics 6 has such a branch in updateDescriptionText)"""
    own = abc.owners()
    for bd in abc.bodies:
        if before is not None and before.get(bd['method']) == bytes(bd['code']):
            continue
        ins = abcrt.decode(bd['code'])
        at = {pos: op for pos, op, _ in ins}
        for pos, op, args in ins:
            if abcrt.OPS[op][1] == ('br',) and args[0] <= pos and at.get(args[0]) != abcrt.NAME2OP['label']:
                raise PatchError('%s: backward %s @%d -> %d does not land on a label'
                                 % (own.get(bd['method'], '?'), abcrt.OPS[op][0], pos, args[0]))


def patch_redswf(orig):
    w = cr2w.CR2W(orig)
    pe, lo, bo, bl, tail = w.swf_layout()
    fws = M.inflate_swf(w.chunk_data(0)[bo:bo + bl])
    abc = abcrt.ABC(abcrt.swf_abcs(fws)[0][1])
    before = {bd['method']: bytes(bd['code']) for bd in abc.bodies}
    abc = patch_abc(abc)
    check_back_branches(abc, before)
    new_abc = abc.serialize()
    abcrt.ABC(new_abc)
    fws = bytearray(fws)
    p = 8 + (5 + 4 * (fws[8] >> 3) + 7) // 8
    fws[p:p + 2] = bytes((0, MENU_FPS))
    fws = bytes(fws)
    out, _ = cr2w.rewrap(orig, abcrt.replace_abc(fws, new_abc))
    bad = [r for r in cr2w.checks(cr2w.CR2W(out)) if r[1] != r[2]]
    if bad:
        raise PatchError('container check failed: %s' % bad[0][0])
    return out, abcrt.replace_abc(fws, new_abc)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    data, swf = patch_redswf(open(src, 'rb').read())
    open(dst, 'wb').write(data)
    if len(sys.argv) > 3:
        open(sys.argv[3], 'wb').write(swf)
    print('wrote', dst, len(data))
