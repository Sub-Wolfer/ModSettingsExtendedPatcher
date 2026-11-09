# Mod Settings Extended Patcher

Source code of **Mod Settings Extended Patcher**, the optional tool for the Witcher 3
mod [Mod Settings Extended](https://www.nexusmods.com/witcher3/mods/15205).

Mod Settings Extended and Real-Time Graphics and HDR Menus Preview both replace the
same menu file, `panel_ingamemenu.redswf`, and the game loads only one of them. The
patcher reads Real-Time Graphics' menu file from the player's own install, adds Mod
Settings Extended's changes to it and saves the result in Mod Settings Extended's own
folder (`Mods\mod00000_ModSettingsExtended\content`), so both mods' features load
together. It works with Real-Time Graphics 2.0 (with the T hotkey) and version 6
("Original", folder `modLiveGraphicsPreviewOriginal`).

What it does, and does not do:

- Reads the game's and your mods' bundle files, and writes only
  `blob0.bundle` and `metadata.store` in Mod Settings Extended's folder.
- Never changes Real-Time Graphics' files and never redistributes them. Nothing
  from that mod is included here or in the exe.
- Checks the new menu file's bytecode before writing; if anything new fails the
  check, it writes nothing.
- "Restore standard MSE" rebuilds Mod Settings Extended's own menu file from the
  game's.
- No network access, no installer, no registry writes. It only *reads* the
  Steam/GOG registry keys to find the game folder.
- Python standard library only; no third-party packages.

## Files

| File | Purpose |
| --- | --- |
| `src/mse_patcher.py` | Window (tkinter): finds the game, shows the state, Combine / Restore buttons |
| `src/mse_core.py` | Finds the game and the mods, builds and writes the menu file |
| `src/fml_patch.py` | Mod Settings Extended's changes to the game menu (Flash bytecode) |
| `src/coll_tables.py` | Sort keys and letter headers for the Mods list in all 18 game languages |
| `src/abcrt.py` | ActionScript 3 (ABC) bytecode reader/writer |
| `src/avm2verify.py` | Structural bytecode verifier (stack, scopes, registers, branches) |
| `src/uw_map_patch.py` | Shared SWF helpers (from Ultrawide Menus) |
| `src/cr2w.py` | CR2W wrapper of `.redswf` files |
| `src/w3bundle.py` | Witcher 3 `.bundle` reader/writer |
| `src/w3meta.py` | `metadata.store` writer |
| `src/lz4block.py` | LZ4 block codec |

## Run from source

```
python src\mse_patcher.py
```

## Build the exe

Windows, Python 3.10 (the release was built with Python 3.10.6 and
PyInstaller 6.22.3):

```
build.bat
```

which runs

```
python -m pip install pyinstaller==6.22.3
python -m PyInstaller --noconfirm --onefile --windowed --name ModSettingsExtendedPatcher --paths src src\mse_patcher.py
```

The exe is written to `dist\ModSettingsExtendedPatcher.exe`. PyInstaller builds are
not byte-for-byte reproducible, so a rebuilt exe will have a different hash.

Released exes (on Nexus Mods and GitHub Releases), SHA-256:

- 1.4.1 (for Mod Settings Extended 1.5.0; finds the game on Linux / Steam Deck): `4e9a04baf51eaae3822b15d1e995fb633e1490cba9b52b0fd90fd768a215daea`
- 1.4.0 (for Mod Settings Extended 1.5.0): `a2d2b8b25697f6f931d5a12615bc9db223a83c3c448a755660f23bba360c403b`
- 1.3.0 (for Mod Settings Extended 1.4.0): `a6459e16f01242a072fad8e1330240f5d73256e14254b29760dbf2774d08cf3a`
- 1.2.0 (for Mod Settings Extended 1.3.0): `e6d95ab38610abc45ff2efdf8a733b3da1c6a37b4d1f8b7f5384a9ed75855b05`
- 1.1.0 (for Mod Settings Extended 1.2.0): `960c94d3cc1c64f34c8f944c14776cbfb275f80ce4e11d12f157f5fea7dd5460`
- 1.0.1: `c8ad87e76ee8fc56083d0b2fe18d52549bf1deebbc278180192b9bf6afe88712` (for Mod Settings Extended 1.1.0)

## License

MIT, see `LICENSE`. Real-Time Graphics and HDR Menus Preview is by its own author
and is not covered by this license.
