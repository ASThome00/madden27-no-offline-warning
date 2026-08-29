# Madden 27 – No Offline Warning

A mod for **EA Sports Madden NFL 27 (PC)** that removes the nag popup you get when playing signed out of EA (for example, with mods enabled):

> **ACCOUNT ERROR**
> Mods require being offline. You won't be able to sign in or access modes like Superstar/Online Dynasty while modding. Enjoy!! -MMC/CFMC
> [OK]

This is the game's stock login-failure dialog; MMC fills in the message. It shows at boot and again whenever a mode re-runs the sign-in. With this mod the menus simply continue as if you had pressed OK.

Port of the [CFB 27 No Offline Warning](https://github.com/ASThome00/cfb27-no-offline-warning) mod. Made by **ASThome**.

## Download

Grab the latest `NoOfflineWarning_vX.Y.fbmod` from this repo (or the [Releases](../../releases) page).

## Install

1. Open **MMC Mod Manager** (the Madden NFL 27 fork of Frosty Mod Manager).
2. Import the `.fbmod` (remove or disable any older version).
3. Enable it and launch the game through the mod manager as usual.

Load order does not matter unless another mod also replaces the file below (unusual — it is a front-end UI script file).

## What it changes

Exactly **one legacy asset**, one byte:

| File | Class / function | Byte | Effect |
|---|---|---|---|
| `common/ui/node_com/scriptpod.ast` | `madden.online.module.Login._ShowLoginFailedPopup` | `0x49 → 0x48` @ 1024677 | never opens the login-failed popup |

The file is an EA APT archive (Flash-style ActionScript 2 bytecode). Every login failure in the front end ends up in one function of the shared `Login` module:

```actionscript
_ShowLoginFailedPopup(title, message, reason) {
    if (mShowLoginFailedPopup == true) {                 // <-- patched
        UnlockInput(LOGIN_INPUT_LOCK);
        if (!PopupManager.IsPopupShowing(LOGIN_FAILED_POPUP_NAME)) {
            popup = PopupManager.MakeGenericPopup(LOGIN_FAILED_POPUP_NAME);
            popup.SetTitle(LocalizeText(title));         // "OSDK_ACC_ERR" = "Account Error"
            popup.SetMessage(LocalizeText(message));     // the reason string the login adapter reports
            popup.AddButton(LocalizeText("OSDK_OK"), Delegate(_LoginFailedCallback, reason));
            popup.Open();
        } else { _LoginFailedCallback(reason); }
    } else {
        _LoginFailedCallback(reason);                    // "login failed, carry on"
    }
    mShowLoginFailedPopup = true;
}
```

The `Equals2` opcode in the `if` (`0x49`) becomes `Less2` (`0x48`), turning the gate into `true < mShowLoginFailedPopup`, which is never true. Execution falls into the `else` branch, which calls the same `_LoginFailedCallback` the OK button would have — so the game behaves exactly as if you had pressed OK, just without the dialog. (`_LoginFailedCallback` → `_LoginComplete(false, …)` also releases the input lock itself, so nothing is left locked.) Flipping the `true` literal instead would have inverted the behaviour for callers that deliberately set the flag to `false`, e.g. silent sign-in attempts.

* No text, strings, or other UI elements are modified. The message text is not stored in the game files — it is supplied at runtime by whatever breaks the sign-in.
* The mod does **not** spoof login state. Other online features are unaffected.
* Side effect: while the mod is active, *any* login-failure popup from this module is suppressed (e.g. a genuine "EA servers unavailable" message). Since mods require playing offline anyway, this has no practical impact.

## Scope / known limitations

* Only the Account Error dialog is covered. Any other offline notices are separate mechanisms.
* Title updates that change the file may require the mod to be rebuilt. If the popup returns after a patch, open an issue.

## Building from source

`MNoOfflineWarning.fbproject` is the MMC Editor project. Open it in **MMC Editor** (Madden NFL 27 profile) and use **File → Export to Mod** to produce the `.fbmod`.

To reproduce the patch from a clean game install:

1. In MMC Editor → Legacy Explorer, export `common/ui/node_com/scriptpod.ast`.
2. Run `python tools/build_patch.py <exported.AST> <patched.AST>`. The script finds the patch site by byte pattern (falling back to the known offset), flips the byte, recompresses (zlib level 9, or [zopfli](https://pypi.org/project/zopfli/) when the zlib stream no longer fits the original slot — it does not for this file) and rewrites the archive with the original header/TOC untouched. It refuses to write anything ambiguous.
3. Legacy Explorer → right-click the asset → **Import** the patched file, save the project, and export the mod.

Byte pattern, if the offset moves after a title update: `78 56 34 12 00 00 00 00 73 B9 01 AF 48 [49] B8`

## Disclaimer

Not affiliated with or endorsed by EA. Use mods offline only, per the Madden modding community rules. Use at your own risk.

## License

[MIT](LICENSE)
