# Changelog

## 1.0.2 – 2026-09-26
- Rebuilt against the **September 26, 2026 title update** from a fresh export of `common/ui/node_com/scriptpod.ast`. Same one-byte patch (site now @1026701), no functional changes.
- Fixes 1.0.1, which still shipped the August 29 `scriptpod.ast` and so rolled back EA's later changes to that file (the current file's script is ~3 KB larger).

## 1.0.1 – 2026-09-03
- Rebuilt against the **September 3, 2026 title update**. Same one-byte patch, same behaviour; the previous build was made from the pre-update `scriptpod.ast` and this one replaces it so the mod keeps working after the update.

## 1.0 – 2026-08-29
- Initial release. Removes the **"ACCOUNT ERROR"** login-failure popup (the one MMC fills with *"Mods require being offline… -MMC/CFMC"*) that appears at boot and again whenever a mode re-runs the sign-in while signed out.
  One one-byte patch in `common/ui/node_com/scriptpod.ast` (`madden.online.module.Login._ShowLoginFailedPopup`).
- Note: while the mod is active, *any* login-failure popup from that class is suppressed (the login-failed callback still runs, so menus continue exactly as if you had pressed OK).
